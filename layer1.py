# layer1_audio.py
import os, subprocess, wave, math, tempfile
from pathlib import Path
from tqdm import tqdm
import numpy as np

ROOT = Path(".")
VOD = ROOT / "vod.mp4"
CLIPS = ROOT / "clips"
CLIPS.mkdir(exist_ok=True)

# Params
SR = 16000
WINDOW = 0.25
HOP = 0.125
SENS = 1.6
PRE = 1.5
POST = 8.0
MIN_CLIP = 30.0
MAX_CLIP = 60.0
MERGE_WINDOW = 7.5

def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def extract_audio(vod, out_wav):
    cmd = ["ffmpeg","-y","-v","error","-i", str(vod), "-vn","-ac","1","-ar", str(SR), "-f","wav", str(out_wav)]
    p = run(cmd)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg audio extract failed: "+p.stderr)
    return out_wav

def detect_peaks(wav):
    wf = wave.open(str(wav),"rb")
    sw = wf.getsampwidth(); rate = wf.getframerate(); frames = wf.getnframes()
    raw = wf.readframes(frames); wf.close()
    if sw==2:
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32)/32768.0
    elif sw==4:
        data = np.frombuffer(raw, dtype=np.int32).astype(np.float32)/2147483648.0
    else:
        data = np.frombuffer(raw, dtype=np.float32)
    win = max(1,int(WINDOW*rate)); hop = max(1,int(HOP*rate))
    energies=[]; times=[]
    for i in range(0, max(1, len(data)-win+1), hop):
        f = data[i:i+win]
        energies.append(np.sqrt(np.mean(f*f)))
        times.append(i/rate + (win/2)/rate)
    energies = np.array(energies)
    if len(energies)==0:
        return []
    median = float(np.median(energies)) or 1e-9
    thr = median * SENS
    peaks=[]
    for i in range(1,len(energies)-1):
        if energies[i] > thr and energies[i] > energies[i-1] and energies[i] >= energies[i+1]:
            peaks.append(times[i])
    if not peaks:
        k = max(3, int(len(energies)*0.01))
        idx = np.argsort(-energies)[:k]
        peaks = sorted(times[idx])
    return peaks

def merge_peaks(peaks):
    if not peaks:
        return []

    merged = []
    s = peaks[0]
    e = peaks[0]

    for t in peaks[1:]:
        # If within merge window AND span doesn't exceed 60 sec
        if (t - e) <= MERGE_WINDOW and (t - s) <= MAX_CLIP:
            e = t
        else:
            merged.append((s, e))
            s = t
            e = t

    merged.append((s, e))
    return merged


def make_segments(merged):
    raw = []

    # --- First pass: build expanded segments with PRE/POST and MIN/MAX caps ---
    for s, e in merged:
        start = max(0.0, s - PRE)
        raw_span = (e - s) + POST                  # expanded hype window
        dur = max(MIN_CLIP, min(MAX_CLIP, raw_span))  # enforce duration constraints
        end = start + dur
        raw.append((round(start, 3), round(end, 3)))

    # --- Second pass: fix overlaps + enforce EXACT clip durations ---
    clean = []
    last_end = 0.0

    for idx, (s, e) in enumerate(raw):

        # FIRST SEGMENT MUST ALWAYS START AT 0.0
        if idx == 0:
            s = 0.0

        # Prevent overlap by pushing start forward
        if s < last_end:
            s = last_end

        # Compute new duration WITHOUT double-counting POST
        new_dur = e - s

        # Enforce exactly MIN_CLIP–MAX_CLIP
        if new_dur > MAX_CLIP:
            new_dur = MAX_CLIP
        if new_dur < MIN_CLIP:
            new_dur = MIN_CLIP

        # Compute corrected end
        e = s + new_dur

        clean.append((round(s, 3), round(e, 3)))
        last_end = e

    return clean


def split_segments(vod, segs):
    if not segs:
        return []

    # Ensure output directory exists
    CLIPS.mkdir(exist_ok=True)

    # Build segment_times: only END times go here
    # Build PERFECT segment times for FFmpeg based ONLY on durations
    segment_times = ",".join(str(e) for (_, e) in segs)


    # Final output pattern
    out_pattern = CLIPS / "clip_%04d.mp4"

    print("\n⚡ Single-pass ffmpeg splitting (high-quality)...")

    # Probe total video duration for progress bar
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nokey=1:noprint_wrappers=1", str(vod)],
        capture_output=True, text=True
    )
    try:
        total = float(probe.stdout.strip())
    except:
        total = None

    # ffmpeg command (single read of input = 20x faster)
    cmd = [
        "ffmpeg", "-y",
        "-ss", "0",                     # seek before input = cleaner cuts
        "-i", str(vod),
        "-f", "segment",
        "-segment_times", segment_times,
        "-reset_timestamps", "1",
        "-c", "copy",                   # no re-encode, high-speed copy
        str(out_pattern)
    ]

    print(f"Segments: {len(segs)}")
    print("Running ffmpeg...")

    # Start ffmpeg
    proc = subprocess.Popen(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    # -------- Progress Bar Setup --------
    from tqdm import tqdm
    import re

    pbar = tqdm(total=100, desc="Splitting", ncols=80, unit="%")
    last = 0
    time_re = re.compile(r"time=(\d+:\d+:\d+\.\d+)")

    def t_to_sec(t):
        h, m, s = t.split(":")
        return int(h)*3600 + int(m)*60 + float(s)

    # Listen to ffmpeg progress
    for line in proc.stderr:
        m = time_re.search(line)
        if not m or total is None:
            continue
        secs = t_to_sec(m.group(1))
        pct = min(100, int((secs / total) * 100))
        if pct > last:
            pbar.update(pct - last)
            last = pct

    proc.wait()
    if last < 100:
        pbar.update(100 - last)
    pbar.close()

    print("✅ Split complete!")

    return sorted(CLIPS.glob("clip_*.mp4"))


def main():
    print("=" * 60)
    print("LAYER 1: Audio-based Peak Detection")
    print("=" * 60)
    
    if not VOD.exists():
        print("❌ Error: put vod.mp4 in project root")
        return
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t:
        wav = Path(t.name)
    
    # Step 1: Extract audio
    print("\n[Step 1/4] Extracting audio from video...")
    extract_audio(VOD, wav)
    print("✅ Audio extracted")
    
    # Step 2: Detect peaks
    print("\n[Step 2/4] Detecting peaks in audio...")
    peaks = detect_peaks(wav)
    print(f"✅ Found {len(peaks)} peaks")
    
    # Step 3: Merge peaks
    print("\n[Step 3/4] Merging nearby peaks...")
    merged = merge_peaks(peaks)
    print(f"✅ Merged into {len(merged)} segments")

    
    
    # Step 4: Create segments
    print("\n[Step 4/4] Creating time segments...")
    segs = make_segments(merged)
    

    if not segs:
        print("❌ No peaks found")
    else:
        split_segments(VOD, segs)
        print(f"✅ Created {len(segs)} clips in clips/")
    
    try:
        wav.unlink()
    except: pass
    
    print("\n" + "=" * 60)
    print(f"LAYER 1 COMPLETE: {len(segs)} clips generated")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
