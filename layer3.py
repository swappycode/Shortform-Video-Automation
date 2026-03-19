# layer3_render.py
# -*- coding: utf-8 -*-

import os
os.environ["HF_HOME"] = "D:\\hf_cache_models"

import re, subprocess, time, json
import random
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
CONFIG_FILE = ROOT / "config.json"
SUBS.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)


def esc(p: str):
    p = p.replace("\\", "/")
    p = p.replace(":", "\\:")
    p = p.replace(" ", "\\ ")
    return p



# Load config or use defaults
def load_config():
    defaults = {
        "model_name": "large-v3",
        "font_name": "Komika Axis",
        "font_size": 18,
        "font_bold": True,
        "outline_width": 3,
        "primary_color": "&H00FFAA00",
        "outline_color": "&H00FFFFFF",
        "alignment": 2,
        "margin_v": 50,
        "max_text_length": 36,
        "bgm_volume": 0.3,
        "bgm_path": "assets/bgm.mp3",
        "ducking_threshold": 0.02,
        "ducking_ratio": 4,
        "ducking_attack": 200,
        "ducking_release": 1000,
        "audio_boost": 1.5
    }
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get("layer3", defaults)
        except Exception as e:
            print(f"[WARN] Could not load config: {e}")
            print("[WARN] Using default values")
            return defaults
    return defaults

cfg = load_config()

MODEL_NAME = cfg["model_name"]
FONT_NAME = cfg["font_name"]
FONT_SIZE = int(cfg["font_size"])
FONT_BOLD = cfg["font_bold"]
OUTLINE_WIDTH = int(cfg["outline_width"])
PRIMARY_COLOR = cfg["primary_color"]
OUTLINE_COLOR = cfg["outline_color"]
ALIGNMENT = int(cfg["alignment"])
MARGIN_V = int(cfg["margin_v"])
MAX_TEXT_LENGTH = int(cfg["max_text_length"])
BGM_VOLUME = float(cfg["bgm_volume"])
BGM_DISABLE = cfg.get("disable_bgm", False)
BGM_RANDOM = cfg.get("randomize_bgm", False)
raw_bgm = cfg.get("bgm_path")
BGM_PATH = Path(raw_bgm) if raw_bgm else None


ASSETS_DIR = Path("assets")

DUCKING_THRESHOLD = float(cfg["ducking_threshold"])
DUCKING_RATIO = int(cfg["ducking_ratio"])
DUCKING_ATTACK = int(cfg["ducking_attack"])
DUCKING_RELEASE = int(cfg["ducking_release"])
AUDIO_BOOST = float(cfg["audio_boost"])

FFMPEG = "ffmpeg"


# Check GPU availability
print("=" * 60)
print(f"CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"CUDA Version: {torch.version.cuda}")
print("=" * 60)

print("\n" + "=" * 60)
print("LAYER 3 CONFIG:")
print(f"  Model: {MODEL_NAME}")
print(f"  Font: {FONT_NAME}, Size: {FONT_SIZE}, Bold: {FONT_BOLD}")
print(f"  Colors: Primary={PRIMARY_COLOR}, Outline={OUTLINE_COLOR}")
print(f"  Alignment: {ALIGNMENT}, Margin: {MARGIN_V}")
print(f"  Max Text Length: {MAX_TEXT_LENGTH}")
print(f"  Audio Boost: {AUDIO_BOOST}x")
print(f"  BGM Volume: {BGM_VOLUME}, Path: {BGM_PATH}")
print(f"  Ducking: threshold={DUCKING_THRESHOLD}, ratio={DUCKING_RATIO}, attack={DUCKING_ATTACK}ms, release={DUCKING_RELEASE}ms")
print("\n" + "="*60)
if BGM_PATH is None:
    print("[INFO] No BGM selected — will render WITHOUT background music.")
else:
    if not BGM_PATH.exists():
        print(f"[WARN] BGM not found at {BGM_PATH}")
        print("      Rendering will continue WITHOUT BGM.")
        BGM_PATH = None
    else:
        print(f"[OK] BGM found: {BGM_PATH}")
print("="*60)


model = WhisperModel(
    MODEL_NAME,
    device="cuda",
    compute_type="float16"
)

print("[OK] Model loaded on GPU\n")

def chunk_text(text: str, max_len: int = MAX_TEXT_LENGTH):
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


def get_bgm_for_clip():
    if BGM_DISABLE:
        return None

    # Random mode
    if BGM_RANDOM:
        bgms = list(ASSETS_DIR.glob("*.mp3"))
        if not bgms:
            return None
        return random.choice(bgms)

    # Manual mode (ensure BGM_PATH exists)
    if BGM_PATH and BGM_PATH.exists():
        return BGM_PATH

    return None



def ffprobe_duration(path):
    p = subprocess.run(
        [FFMPEG.replace("ffmpeg","ffprobe"), "-v","error",
        "-show_entries","format=duration",
        "-of","default=nokey=1:noprint_wrappers=1",
        str(path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(p.stdout.strip())
    except:
        return 0.0

def process_clip(clip_path, lang="hi"):
    import os, shutil
    clip = Path(clip_path)
    stem = clip.stem

    srt_out = SUBS / f"{stem}.srt"
    ass_out = SUBS / f"{stem}.ass"
    out_video = OUT / f"{stem}.mp4"

    try:
        print(f"  Transcribing {stem}...", end=" ", flush=True)

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

        # Build subtitles
        items = []
        idx = 1

        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue

            parts = chunk_text(text, MAX_TEXT_LENGTH)
            dur = max(0.35, seg.end - seg.start)
            step = dur / max(1, len(parts))

            for i, p in enumerate(parts):
                st = seg.start + step * i
                et = st + step - 0.01
                items.append(
                    srt.Subtitle(
                        index=idx,
                        start=srt.timedelta(seconds=round(st, 3)),
                        end=srt.timedelta(seconds=round(et, 3)),
                        content=p
                    )
                )
                idx += 1

        if not items:
            print("  [WARN] No speech detected")
            return None

        print(f"  [OK] {len(items)} subtitles generated")

        # Write SRT
        with open(srt_out, "w", encoding="utf-8") as f:
            f.write(srt.compose(items))

        # Convert SRT → ASS (and ensure saved to subs/<safe-name>.ass)
        subs = pysubs2.load(str(srt_out))
        style = pysubs2.SSAStyle()
        style.fontname = FONT_NAME
        style.fontsize = FONT_SIZE
        style.bold = FONT_BOLD
        style.outline = OUTLINE_WIDTH
        style.primarycolor = PRIMARY_COLOR
        style.outlinecolor = OUTLINE_COLOR
        style.borderStyle = 1
        style.alignment = ALIGNMENT
        style.marginv = MARGIN_V

        subs.styles["Default"] = style
        # Save to ass_out (inside project, no drive letter -> safe for filter graph)
        subs.save(str(ass_out))

        # Prefer a relative path to the ASS for use inside filter_complex
        ass_rel = os.path.relpath(ass_out, start=ROOT).replace("\\", "/")

        # Duration for progress bar
        total = ffprobe_duration(clip)

        # Select BGM according to user mode
        bgm_file = get_bgm_for_clip()  # returns Path or None

        # -----------------------------
        # Build filter graph (video)
        # -----------------------------
        vf = (
            "[0:v]"
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "gblur=sigma=30[bg];"

            "[0:v]"
            "scale=1080:-1:force_original_aspect_ratio=decrease[fg];"

            "[bg][fg]overlay=(W-w)/2:(H-h)/2[pre];"

            "[pre]subtitles='" + ass_rel + "'[v]"
        )




        # -----------------------------
        # Build ffmpeg command args
        # -----------------------------
        if bgm_file is None:
            # No BGM: single input (clip)
            cmd = [
                FFMPEG, "-y", "-hwaccel", "cuda",
                "-i", str(clip),

                "-filter_complex",
                vf + ";" + f"[0:a]volume={AUDIO_BOOST}[a]",

                "-map", "[v]",
                "-map", "[a]",

                "-c:v", "h264_nvenc", "-preset", "p7", "-b:v", "10M",
                "-c:a", "aac", "-b:a", "192k",

                str(out_video)
            ]
        else:
            # BGM present: clip + bgm inputs. pass inputs as separate args (absolute paths are fine here)
            cmd = [
                FFMPEG, "-y", "-hwaccel", "cuda",
                "-i", str(clip),
                "-stream_loop", "-1", "-i", str(bgm_file),

                "-filter_complex",
                vf + ";" +
                f"[0:a]volume={AUDIO_BOOST}[orig];"
                f"[1:a]volume={BGM_VOLUME}[bgm];"
                f"[bgm][orig]sidechaincompress="
                f"threshold={DUCKING_THRESHOLD}:ratio={DUCKING_RATIO}:"
                f"attack={DUCKING_ATTACK}:release={DUCKING_RELEASE}:makeup=1[duck];"
                f"[orig][duck]amix=inputs=2:duration=shortest:dropout_transition=2[a_final]",

                "-map", "[v]",
                "-map", "[a_final]",

                "-c:v", "h264_nvenc", "-preset", "p7", "-b:v", "10M",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",

                str(out_video)
            ]

        # Execute ffmpeg and show progress
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

       
       
        


        # regex handles hh:mm:ss.sss or mm:ss.sss
        patt = re.compile(r"time=(\d+:\d+:\d+\.\d+|\d+:\d+\.\d+)")
        pbar = tqdm(total=100, desc=f"Rendering {stem}", ncols=80, unit="%", leave=False)
        last = 0

        try:
            # read stderr line-by-line
            for line in proc.stderr:
                # forward ffmpeg lines to console (optional)
                # print(line.rstrip())
                m = patt.search(line)
                if not m:
                    continue
                t = m.group(1)
                parts = t.split(":")
                if len(parts) == 3:
                    secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                else:
                    secs = int(parts[0]) * 60 + float(parts[1])

                if total > 0:
                    pct = int((secs / total) * 100)
                    pct = min(100, pct)
                    if pct > last:
                        pbar.update(pct - last)
                        last = pct

        finally:
            proc.wait()
            if last < 100:
                pbar.update(100 - last)
            pbar.close()

        if out_video.exists():
            print("  [OK] Rendering completed")
            return out_video

        print("  [ERROR] Render failed")
        return None

    except Exception as e:
        print(f"  [ERROR] {e}")
        return None


def main():
    print("=" * 60)
    print("LAYER 3: Transcription & Rendering")
    print("=" * 60)

    clips = sorted(FILTERED.glob("*.mp4"))
    if not clips:
        print("[ERROR] No clips in filtered/. Run layer2 first.")
        return

    print(f"\n[Step 1/3] Found {len(clips)} filtered clips")
    print("[Step 2/3] Transcribing with model (translate to English)...")
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
    print("[OK] Rendering complete")
    print("=" * 60)
    print(f"LAYER 3 COMPLETE: {len(outs)} videos rendered (Failed: {failed})")
    print("Output: output/")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
