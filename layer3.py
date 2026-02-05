# layer3_render.py
import os
os.environ["HF_HOME"] = "D:\\hf_cache_models"

import re, subprocess, time
from pathlib import Path
from faster_whisper import WhisperModel
import srt, pysubs2
from tqdm import tqdm
import torch

ROOT = Path(".")
FILTERED = ROOT / "filtered"
SUBS = ROOT / "subs"
OUT = ROOT / "output"
ASSETS = ROOT / "assets"
SUBS.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

MODEL_NAME = "large-v3"
FONT_NAME = "Komika Axis"
FFMPEG = "ffmpeg"
BGM_PATH = ASSETS / "bgm.mp3"

# Check GPU availability
print("=" * 60)
print(f"CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"CUDA Version: {torch.version.cuda}")
print("=" * 60)

# Check BGM
if not BGM_PATH.exists():
    print(f"\n⚠️  WARNING: BGM not found at {BGM_PATH}")
    print("    Background music will be skipped.\n")
else:
    print(f"\n✅ BGM found: {BGM_PATH}\n")

print("\n" + "=" * 60)
print("Loading final model (large-v3) on GPU...")
print("=" * 60)
model = WhisperModel(
    MODEL_NAME, 
    device="cuda",
    compute_type="float16"
)
print("✅ Model loaded on GPU\n")

def chunk_text(text: str, max_len: int = 36):
    words = text.split()
    if not words:
        return []
    chunks = []
    cur = []
    for w in words:
        if len(" ".join(cur + [w])) > max_len:
            chunks.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        chunks.append(" ".join(cur))
    return chunks

def ffprobe_duration(path):
    p = subprocess.run([FFMPEG.replace("ffmpeg","ffprobe"), "-v","error","-show_entries","format=duration","-of","default=nokey=1:noprint_wrappers=1", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try: 
        return float(p.stdout.strip())
    except: 
        return 0.0

def process_clip(clip_path, lang="hi"):
    clip = Path(clip_path)
    stem = clip.stem
    srt_out = SUBS / f"{stem}.srt"
    ass_out = SUBS / f"{stem}.ass"
    out_video = OUT / f"{stem}.mp4"

    try:
        # Step 1: Transcribe with translation to English
        print(f"  🔍 Transcribing {stem}...", end=" ", flush=True)
        segments, info = model.transcribe(
            str(clip), 
            language=lang, 
            task="translate", 
            vad_filter=True, 
            beam_size=5,
            best_of=7,
            patience=2,
            temperature=0.0
        )
        
        items = []
        idx = 1
        
        for seg in segments:
            txt = seg.text.strip()
            if not txt:
                continue
            
            chunks = chunk_text(txt, max_len=36)
            seg_start = seg.start
            seg_end = seg.end
            total = max(0.35, seg_end - seg_start)
            step = total / max(1, len(chunks))
            
            for i, c in enumerate(chunks):
                st = seg_start + (i * step)
                et = seg_start + ((i + 1) * step) - 0.01
                items.append(srt.Subtitle(index=idx, start=srt.timedelta(seconds=round(st, 3)), end=srt.timedelta(seconds=round(et, 3)), content=c))
                idx += 1

        if not items:
            print(f"❌ No speech detected")
            return None

        print(f"✅ ({len(items)} subs)")

        # Write SRT file
        with open(srt_out, "w", encoding="utf-8") as f:
            f.write(srt.compose(items))

        # Step 2: Convert to ASS with styling
        subs2 = pysubs2.load(str(srt_out))
        style = pysubs2.SSAStyle()
        style.fontname = FONT_NAME
        style.fontsize = 18
        style.bold = True
        style.outline = 3
        style.primarycolor = "&H00FFAA00"
        style.outlinecolor = "&H00FFFFFF"
        style.borderStyle = 1
        style.alignment = 2
        style.marginv = 50
        subs2.styles["Default"] = style
        subs2.save(str(ass_out))

        # Get video duration for BGM looping
        total = ffprobe_duration(clip)

        # Step 3: Render with ffmpeg (with BGM if available)
        ass_path = str(ass_out).replace("\\", "/")
        
        vf = (
            f"scale=1080:-1:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
            f"subtitles={ass_path}"
        )

        # Build ffmpeg command with BGM mixing
        if BGM_PATH.exists():
            # Mix original audio with looped BGM with DUCKING
            # BGM ducks down to 10% when speech is detected, stays at 30% otherwise
                cmd = [
                    FFMPEG, "-y", "-hwaccel", "cuda",
                    "-i", str(clip),
                    "-stream_loop", "-1", "-i", str(BGM_PATH),

                    "-filter_complex",
                    f"[0:v]{vf}[v];"
                    
                    # BOOST ONLY THE ORIGINAL AUDIO 🔥 (1.5x louder)
                    f"[0:a]volume=1.5[orig_boosted];"
                    
                    # BGM base volume
                    f"[1:a]volume=0.30[bgm];"
                    
                    # Duck BGM when original audio is loud
                    f"[bgm][orig_boosted]sidechaincompress="
                    f"threshold=0.02:ratio=4:attack=200:release=1000:makeup=1[bgm_ducked];"
                    
                    # Mix original boosted audio + ducked bgm
                    f"[orig_boosted][bgm_ducked]amix=inputs=2:duration=shortest:dropout_transition=2[a_final]",
                    
                    "-map", "[v]",
                    "-map", "[a_final]",
                    "-c:v", "h264_nvenc", "-preset", "p7", "-b:v", "10M",
                    "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    str(out_video)
                ]
        else:
           
                 # No BGM - but boost original audio only
            cmd = [
                FFMPEG, "-y", "-hwaccel", "cuda",
                "-i", str(clip),

                "-filter_complex",
                f"[0:v]{vf}[v];"
                f"[0:a]volume=1.5[a]",   # 🔥 boost original audio ONLY

                "-map", "[v]",
                "-map", "[a]",

                "-c:v", "h264_nvenc", "-preset", "p7", "-b:v", "10M",
                "-c:a", "aac", "-b:a", "192k",

                str(out_video)
            ]


        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        pattern = re.compile(r"time=(\d+:\d+:\d+\.\d+|\d+:\d+\.\d+)")
        pbar = tqdm(total=100, desc=f"  🎬 {stem}", ncols=80, unit="%", leave=False)
        last = 0
        try:
            for line in proc.stderr:
                m = pattern.search(line)
                if not m:
                    continue
                parts = m.group(1).split(":")
                if len(parts) == 3:
                    secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                else:
                    secs = int(parts[0]) * 60 + float(parts[1])
                if total > 0:
                    pct = min(100, int(secs / total * 100))
                    if pct > last:
                        pbar.update(pct - last)
                        last = pct
        finally:
            proc.wait()
            if last < 100:
                pbar.update(100 - last)
            pbar.close()

        if out_video.exists():
            print(f"  ✅ Rendered")
            return out_video
        else:
            print(f"  ❌ Render failed")
            return None
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None

def main():
    print("=" * 60)
    print("LAYER 3: Transcription & Rendering")
    print("=" * 60)
    
    clips = sorted(FILTERED.glob("*.mp4"))
    if not clips:
        print("❌ No clips in filtered/. Run layer2 first.")
        return
    
    print(f"\n[Step 1/3] Found {len(clips)} filtered clips")
    print("[Step 2/3] Transcribing with large-v3 (translate to English)...")
    print("[Step 3/3] Rendering with subtitles + BGM...\n")
    
    outs = []
    failed = 0
    
    for c in clips:
        o = process_clip(c, lang="hi")
        if o:
            outs.append(str(o))
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print("✅ Rendering complete")
    print("=" * 60)
    print(f"LAYER 3 COMPLETE: {len(outs)} videos rendered (Failed: {failed})")
    print(f"Output: output/")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()