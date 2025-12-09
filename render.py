import re
import subprocess
import time
from pathlib import Path
from tqdm import tqdm
from faster_whisper import WhisperModel
import srt

# ---------- config ----------
CLIP_DIR = Path("clips")
OUT = Path("output/test_vertical.mp4")
SRT_OUT = Path("subs/test_vertical.srt")
FONT_NAME = "Komika Axis"
FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"
# ----------------------------


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


def probe_duration_seconds(path: Path) -> float:
    cmd = [
        FFPROBE, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0 or not p.stdout.strip():
        return 0.0
    return float(p.stdout.strip())


def ffmpeg_time_to_seconds(tstr: str) -> float:
    parts = tstr.strip().split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(h)*3600 + int(m)*60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m)*60 + float(s)
    return float(parts[0])


# ---------- MAIN ----------
if __name__ == "__main__":
    clip = next(Path("clips").glob("*.mp4"))
    print(f"\n🔎 Using clip for caption test: {clip}\n")

    model = WhisperModel(
        "large-v3",
        download_root="D:/hf_cache_models",
        device="cuda",
        compute_type="float16"
    )

    print("🎤 Transcribing...\n")

    segments, info = model.transcribe(
    str(clip),
    language="hi",
    task="translate",   # <-- FIXED
    vad_filter=True,     # <-- forces proper segments
    beam_size=7,
    best_of=7,
    patience=2,
    temperature=0.0
)

    items = []
    idx = 1

    # ---------- FIXED TIMING SYSTEM ----------
    for seg in segments:
        raw = seg.text.strip()
        if not raw:
            continue

        chunks = chunk_text(raw, max_len=36)

        seg_start = seg.start
        seg_end = seg.end
        total = max(0.35, seg_end - seg_start)
        step = total / len(chunks)

        for i, c in enumerate(chunks):
            st = seg_start + (i * step)
            et = seg_start + ((i + 1) * step) - 0.01

            items.append(
                srt.Subtitle(
                    index=idx,
                    start=srt.timedelta(seconds=round(st, 3)),
                    end=srt.timedelta(seconds=round(et, 3)),
                    content=c
                )
            )
            idx += 1

    # ---------- WRITE SRT ----------
    SRT_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(SRT_OUT, "w", encoding="utf-8") as f:
        f.write(srt.compose(items))

    print(f"✅ SRT created at: {SRT_OUT}\n")

    total_dur = probe_duration_seconds(clip)
    print(f"🎞 Duration: {total_dur:.2f}s\n")

    print("🎬 Rendering with FFMPEG...\n")

    # ---------- FIX WINDOWS PATH ----------
    srt_path = str(SRT_OUT).replace("\\", "/")
    safe_srt = srt_path.replace(":", r"\:")
    # ---------------------------------------

    force_style = (
        f"FontName={FONT_NAME},"
        f"FontSize=18,"
        f"PrimaryColour=&H00FFAA00&,"     # neon blue
        f"OutlineColour=&H00FFFFFF&,"     # white outline
        f"Outline=3,"
        f"BorderStyle=1,"
        f"Alignment=2,"
        f"MarginV=30"
    )

    vf = (
        f"scale=1080:-1:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
        f"subtitles={safe_srt}:force_style='{force_style}'"
    )

    cmd = [
        FFMPEG, "-y",
        "-hwaccel", "cuda",
        "-i", str(clip),
        "-vf", vf,
        "-c:v", "h264_nvenc",
        "-preset", "p7",
        "-b:v", "10M",
        "-c:a", "aac",
        str(OUT)
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    pbar = tqdm(total=100, desc="GPU Render", ncols=80)
    last = 0
    pattern = re.compile(r"time=(\d+:\d+:\d+\.\d+|\d+:\d+\.\d+)")

    try:
        while True:
            line = proc.stderr.readline()
            if line == "" and proc.poll() is not None:
                break

            m = pattern.search(line)
            if not m:
                continue

            secs = ffmpeg_time_to_seconds(m.group(1))

            if total_dur > 0:
                pct = min(100, int(secs / total_dur * 100))
                if pct > last:
                    pbar.update(pct - last)
                    last = pct

    finally:
        proc.wait()
        if last < 100:
            pbar.update(100 - last)
        pbar.close()

    if proc.returncode == 0:
        print(f"\n🎉 Render FINISHED → {OUT}\n")
    else:
        print("\n❌ FFMPEG ERROR\n")
