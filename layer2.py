# layer2_filter.py
# -*- coding: utf-8 -*-
import subprocess, json, shutil
from pathlib import Path
from tqdm import tqdm
import numpy as np
from faster_whisper import WhisperModel
import torch
import sys

# ===== CRITICAL: FORCE UNBUFFERED OUTPUT FOR GUI =====
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Override print to always flush
import functools
_original_print = print
print = functools.partial(_original_print, flush=True)
# =====================================================

ROOT = Path(".")
CLIPS_DIR = ROOT / "clips"
FILTERED = ROOT / "filtered"
FILTERED.mkdir(exist_ok=True)
MANIFEST = ROOT / "layer2_manifest.json"
CONFIG_FILE = ROOT / "config.json"

# Load config or use defaults
def load_config():
    defaults = {
        "keywords": "clip,bro,bruh,bru,wtf,holy,oh my god,omg,oh my gosh,what,wait,no,damn,brooo,nah,yo,fuck,freaking,dude,guys,wow,damn,shit,crazy,insane,unbelievable",
        "sample_fps": 2,
        "frame_diff_thresh": 0.12,
        "kw_threshold": 4,
        "vis_threshold": 70
    }
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get("layer2", defaults)
        except Exception as e:
            print(f"[WARN] Could not load config: {e}")
            print("[WARN] Using default values")
            return defaults
    return defaults

cfg = load_config()

# Parse keywords from config
TRIGGERS = [k.strip() for k in cfg["keywords"].split(",") if k.strip()]
SAMPLE_FPS = int(cfg["sample_fps"])
FRAME_DIFF_THRESH = float(cfg["frame_diff_thresh"])
KW_THRESHOLD = int(cfg["kw_threshold"])
VIS_THRESHOLD = float(cfg["vis_threshold"])

print("=" * 60)
print("LAYER 2 CONFIG:")
print(f"  Keywords: {len(TRIGGERS)} loaded")
print(f"  Keyword Threshold: {KW_THRESHOLD}")
print(f"  Visual Threshold: {VIS_THRESHOLD}")
print(f"  Sample FPS: {SAMPLE_FPS}")
print(f"  Frame Diff Threshold: {FRAME_DIFF_THRESH}")
print("=" * 60)

print("\n" + "=" * 60)
print("Loading Whisper 'medium' for filtering...")
print("=" * 60)
fw = WhisperModel("medium", device="cuda", compute_type="float16")
print("[OK] Model loaded\n")

def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def ffprobe_resolution(fn):
    p = run([
        "ffprobe","-v","error",
        "-select_streams","v:0",
        "-show_entries","stream=width,height",
        "-of","default=nokey=1:noprint_wrappers=1",
        str(fn)
    ])
    lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
    if len(lines) < 2: return None, None
    return int(lines[0]), int(lines[1])

def visual_change_score(clip, fps=SAMPLE_FPS):
    w,h = ffprobe_resolution(clip)
    if not w or not h: 
        print(f"    [WARN] Can't get resolution")
        return 0.0
    frame_size = w*h*3

    cmd = [
        "ffmpeg","-v","error","-i",str(clip),
        "-vf",f"fps={fps},format=rgb24",
        "-f","rawvideo","-"
    ]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    frames = []
    while True:
        raw = p.stdout.read(frame_size)
        if not raw or len(raw) < frame_size:
            break
        arr = np.frombuffer(raw, np.uint8).reshape((h,w,3)).astype(np.float32)/255.0
        gray = arr.mean(axis=2)
        frames.append(gray)

    try: p.kill()
    except: pass

    if len(frames) < 2:
        print(f"    [WARN] Less than 2 frames extracted")
        return 0.0

    diffs = [np.mean(np.abs(frames[i]-frames[i-1])) for i in range(1,len(frames))]
    med = float(np.median(diffs)) or 1e-9
    norm = np.array(diffs)/med
    score = float(np.sum(norm > FRAME_DIFF_THRESH))
    
    print(f"    [DEBUG] vis_debug: frames={len(frames)}, median_diff={med:.4f}, score={score:.1f}")
    del frames
    del diffs

    return score

def fast_transcribe_text(clip):
    try:
        segs,_ = fw.transcribe(
            str(clip), 
            language="hi",           # Set Hindi
            task="translate",        # Translate to English
            vad_filter=False, 
            beam_size=1, 
            word_timestamps=False
        )
        text = " ".join([s.text for s in segs]).lower()
        print(f"    [DEBUG] Transcribed: {text[:80]}...")
        return text
    except Exception as e:
        print(f"[Whisper Error] {clip}: {e}")
        return ""

def passes_filters(clip):
    print("\n" + "-" * 60)
    print(f"Processing: {Path(clip).name}")
    
    # -------- TRANSCRIPTION --------
    txt = fast_transcribe_text(clip)
    print(f"Transcribed (first 120 chars): {txt[:120]}...")
    
    # -------- KEYWORD MATCHING --------
    kw_details = {}
    total_kw = 0
    words = txt.split()

    for trigger in TRIGGERS:
        count = sum(1 for w in words if trigger in w)
        if count > 0:
            kw_details[trigger] = count
            total_kw += count

    print("\nKeyword Matches:")
    if kw_details:
        for k, v in kw_details.items():
            print(f"   {k}: {v}")
    else:
        print("   No keywords matched")

    print(f"Total Keyword Score = {total_kw}   (Threshold = {KW_THRESHOLD})")

    # -------- VISUAL SCORE --------
    print("\nVisual Motion Analysis:")
    vis = visual_change_score(clip)
    print(f"   Visual Score: {vis:.1f}   (Threshold = {VIS_THRESHOLD})")

    # -------- FINAL DECISION --------
    keep = (total_kw >= KW_THRESHOLD) or (vis >= VIS_THRESHOLD)

    if keep:
        reason = "Keyword" if total_kw >= KW_THRESHOLD else "Visual"
        print(f"\nRESULT: KEEP (Passed by {reason})")
    else:
        print("\nRESULT: DROP (Did not meet thresholds)")

    # -------- MAIN GUI LINE --------
    print(f"[L2] {Path(clip).name} | KW={total_kw} | VIS={vis:.1f} | KEEP={keep}")
    print("-" * 60)

    torch.cuda.empty_cache()

    return keep, {"kw": total_kw, "vis": vis}


def main():
    print("=" * 60)
    print("LAYER 2: Content Filtering")
    print("=" * 60)
    
    clips = sorted(CLIPS_DIR.glob("*.mp4"))
    if not clips:
        print("[ERROR] No clips found in clips/. Run layer1 first.")
        return

    print(f"\n[Step 1/2] Found {len(clips)} clips")
    print("[Step 2/2] Filtering clips with keyword + visual analysis...\n")
    sys.stdout.flush()  # Force flush before tqdm

    results = []
    kept_count = 0
    kw_kept = 0
    vis_kept = 0

    # Configure tqdm for GUI compatibility
    for clip in tqdm(clips, 
                     desc="Filtering clips", 
                     unit="clip", 
                     ncols=80, 
                     leave=True, 
                     dynamic_ncols=False,
                     file=sys.stdout,
                     mininterval=0.1):

        ok, meta = passes_filters(clip)
        results.append({"path": str(clip), "keep": ok, "meta": meta})

        if ok:
            shutil.copy2(clip, FILTERED / clip.name)
            kept_count += 1
            
            # Track what passed
            if meta["kw"] >= KW_THRESHOLD:
                kw_kept += 1
            if meta["vis"] >= VIS_THRESHOLD:
                vis_kept += 1

    try:
        with open(MANIFEST, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
    except Exception as e:
        print(f"[Warning] Could not write manifest: {e}")

    print(f"\n[OK] Filtering complete")
    print("=" * 60)
    print(f"LAYER 2 COMPLETE: {kept_count}/{len(clips)} clips kept")
    print(f"  • Keyword-based: {kw_kept}")
    print(f"  • Visual-based: {vis_kept}")
    print(f"Output: filtered/")
    print("=" * 60 + "\n")
    sys.stdout.flush()

if __name__ == "__main__":
    import os
    import atexit
    
    # Disable all exit handlers that might interfere with CUDA
    atexit.unregister = lambda *args, **kwargs: None
    
    try:
        main()
    except:
        pass
    
    # Immediate hard exit - skip ALL Python cleanup
    os._exit(0)