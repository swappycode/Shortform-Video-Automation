# layer2_filter.py
import subprocess, json, shutil
from pathlib import Path
from tqdm import tqdm
import numpy as np
from faster_whisper import WhisperModel

ROOT = Path(".")
CLIPS_DIR = ROOT / "clips"
FILTERED = ROOT / "filtered"
FILTERED.mkdir(exist_ok=True)
MANIFEST = ROOT / "layer2_manifest.json"

# --- Trigger keywords ---
TRIGGERS = [
    "clip","bro","bruh","bru","wtf","holy","oh my god","omg","oh my gosh",
    "what","wait","no","damn","brooo","nah","yo","fuck","freaking",
    "dude","guys","wow","damn","shit","crazy","insane","unbelievable"
]

SAMPLE_FPS = 2
FRAME_DIFF_THRESH = 0.12

print("=" * 60)
print("Loading Whisper 'medium' for filtering...")
print("=" * 60)
fw = WhisperModel("medium", device="cuda", compute_type="float16")
print("✅ Model loaded\n")

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
        print(f"    ⚠️ Can't get resolution")
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
        print(f"    ⚠️ Less than 2 frames extracted")
        return 0.0

    diffs = [np.mean(np.abs(frames[i]-frames[i-1])) for i in range(1,len(frames))]
    med = float(np.median(diffs)) or 1e-9
    norm = np.array(diffs)/med
    score = float(np.sum(norm > FRAME_DIFF_THRESH))
    
    print(f"    📊 vis_debug: frames={len(frames)}, median_diff={med:.4f}, score={score:.1f}")
    return score

def fast_transcribe_text(clip):
    try:
        segs,_ = fw.transcribe(
            str(clip), 
            language="hi",           # ✅ Set Hindi
            task="translate",        # ✅ Translate to English
            vad_filter=False, 
            beam_size=1, 
            word_timestamps=False
        )
        text = " ".join([s.text for s in segs]).lower()
        print(f"    🎤 Transcribed: {text[:80]}...")
        return text
    except Exception as e:
        print(f"[Whisper Error] {clip}: {e}")
        return ""

def passes_filters(clip):
    txt = fast_transcribe_text(clip)
    
    # Count keyword occurrences (with word boundaries)
    kw = 0
    for trigger in TRIGGERS:
        kw += len([w for w in txt.split() if trigger in w.lower()])
    
    vis = visual_change_score(clip)
    
    print(f"    → kw={kw}, vis={vis:.1f}")
    
    keep = (kw >= 4) or (vis >= 70)
    return keep, {"kw": kw, "vis": vis}

def main():
    print("=" * 60)
    print("LAYER 2: Content Filtering")
    print("=" * 60)
    
    clips = sorted(CLIPS_DIR.glob("*.mp4"))
    if not clips:
        print("❌ No clips found in clips/. Run layer1 first.")
        return

    print(f"\n[Step 1/2] Found {len(clips)} clips")
    print("[Step 2/2] Filtering clips with keyword + visual analysis...\n")

    results = []
    kept_count = 0
    kw_kept = 0
    vis_kept = 0

    for clip in tqdm(clips, desc="Filtering clips", unit="clip"):
        ok, meta = passes_filters(clip)
        results.append({"path": str(clip), "keep": ok, "meta": meta})

        if ok:
            shutil.copy2(clip, FILTERED / clip.name)
            kept_count += 1
            
            # Track what passed
            if meta["kw"] >= 2:
                kw_kept += 1
            if meta["vis"] >= 5:
                vis_kept += 1

    try:
        with open(MANIFEST, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
    except Exception as e:
        print(f"[Warning] Could not write manifest: {e}")

    print(f"\n✅ Filtering complete")
    print("=" * 60)
    print(f"LAYER 2 COMPLETE: {kept_count}/{len(clips)} clips kept")
    print(f"  • Keyword-based: {kw_kept}")
    print(f"  • Visual-based: {vis_kept}")
    print(f"Output: filtered/")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
