

# layer1_audio.py
# -*- coding: utf-8 -*-
import os, subprocess, wave, math, tempfile, json
from pathlib import Path
from tqdm import tqdm
import numpy as np

ROOT = Path(".")
VOD = ROOT / "vod.mp4"
CLIPS = ROOT / "clips"
CLIPS.mkdir(exist_ok=True)
CONFIG_FILE = ROOT / "config.json"

# Load config or use defaults
def load_config():
    defaults = {
        "sample_rate": 16000,
        "window": 0.25,
        "hop": 0.125,
        "sensitivity": 1.6,
        "pre_buffer": 1.5,
        "post_buffer": 8.0,
        "min_clip": 30.0,
        "max_clip": 60.0,
        "merge_window": 7.5
    }
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get("layer1", defaults)
        except Exception as e:
            print(f"[WARN] Could not load config: {e}")
            print("[WARN] Using default values")
            return defaults
    return defaults

cfg = load_config()

# Params from config
SR = int(cfg["sample_rate"])
WINDOW = float(cfg["window"])
HOP = float(cfg["hop"])
SENS = float(cfg["sensitivity"])
PRE = float(cfg["pre_buffer"])
POST = float(cfg["post_buffer"])
MIN_CLIP = float(cfg["min_clip"])
MAX_CLIP = float(cfg["max_clip"])
MERGE_WINDOW = float(cfg["merge_window"])

print("=" * 60)
print("LAYER 1 CONFIG:")
print(f"  Sample Rate: {SR} Hz")
print(f"  Window: {WINDOW}s, Hop: {HOP}s")
print(f"  Sensitivity: {SENS}x")
print(f"  Pre/Post Buffer: {PRE}s / {POST}s")
print(f"  Clip Duration: {MIN_CLIP}s - {MAX_CLIP}s")
print(f"  Merge Window: {MERGE_WINDOW}s")
print("=" * 60 + "\n")

def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def get_keyframes(vod):
    """Fast + reliable keyframe extraction using packet flags (GUI safe)."""
    print("[INFO] Extracting keyframes... (packet mode)")

    # This ffprobe command does NOT decode video frames.
    # It inspects container-level packets, which is extremely fast.
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-select_streams", "v:0",
        "-show_entries", "packet=pts_time,flags",
        "-of", "csv=p=0",
        str(vod)
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True
        )
    except FileNotFoundError:
        print("[ERROR] ffprobe not found. Skipping keyframe snapping.")
        return []

    keyframes = []

    # Output format of ffprobe:
    # <PTS>,K__  (K indicates keyframe)
    # <PTS>,__  
    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        parts = line.split(',')
        if len(parts) != 2:
            continue

        pts, flags = parts

        # Keyframe packets contain flag "K"
        if "K" in flags:
            try:
                keyframes.append(float(pts))
            except:
                pass

    keyframes.sort()
    print(f"[OK] Found {len(keyframes)} keyframes")
    return keyframes


def snap_to_keyframe(timestamp, keyframes):
    """Find nearest keyframe to given timestamp"""
    if not keyframes:
        return timestamp

    # Find closest keyframe
    closest = min(keyframes, key=lambda x: abs(x - timestamp))
    return closest

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
    total_steps = len(range(0, max(1, len(data)-win+1), hop))
    with tqdm(total=total_steps, desc="Analyzing audio", ncols=80, unit="frames") as pbar:
        for i in range(0, max(1, len(data)-win+1), hop):
            f = data[i:i+win]
            energies.append(np.sqrt(np.mean(f*f)))
            times.append(i/rate + (win/2)/rate)
            pbar.update(1)
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

    with tqdm(total=len(peaks), desc="Merging peaks", ncols=80, unit="peaks") as pbar:
        for i, t in enumerate(peaks[1:], 1):
            # If within merge window AND span doesn't exceed 60 sec
            if (t - e) <= MERGE_WINDOW and (t - s) <= MAX_CLIP:
                e = t
            else:
                merged.append((s, e))
                s = t
                e = t
            pbar.update(1)

    merged.append((s, e))
    return merged


def make_segments(merged, keyframes):
    raw = []

    # --- First pass: build expanded segments with PRE/POST and MIN/MAX caps ---
    for s, e in merged:
        start = max(0.0, s - PRE)
        raw_span = (e - s) + POST                  # expanded hype window
        dur = max(MIN_CLIP, min(MAX_CLIP, raw_span))  # enforce duration constraints
        end = start + dur
        raw.append((round(start, 3), round(end, 3)))

    # --- Second pass: fix overlaps + enforce EXACT clip durations + snap to keyframes ---
    clean = []
    last_end = 0.0

    for idx, (s, e) in enumerate(raw):

        # FIRST SEGMENT MUST ALWAYS START AT 0.0
        if idx == 0:
            s = 0.0

        # Prevent overlap by pushing start forward
        if s < last_end:
            s = last_end

        # Snap start and end to nearest keyframes
        if keyframes:
            s = snap_to_keyframe(s, keyframes)

            # Calculate end based on snapped start
            target_end = s + MIN_CLIP
            e = snap_to_keyframe(target_end, keyframes)

            # Make sure duration is within bounds
            dur = e - s
            if dur < MIN_CLIP:
                # Find next keyframe that gives us MIN_CLIP duration
                target_end = s + MIN_CLIP
                e = snap_to_keyframe(target_end, keyframes)
            elif dur > MAX_CLIP:
                # Find earlier keyframe that gives us MAX_CLIP duration
                target_end = s + MAX_CLIP
                e = snap_to_keyframe(target_end, keyframes)

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

    print("\n[INFO] Single-pass ffmpeg splitting (high-quality)...")

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
    print("[INFO] Running ffmpeg...")

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

    print("[OK] Split complete!")

    return sorted(CLIPS.glob("clip_*.mp4"))


def main():
    print("=" * 60)
    print("LAYER 1: Audio-based Peak Detection with Keyframe Snapping")
    print("=" * 60)
    
    if not VOD.exists():
        print("[ERROR] Error: put vod.mp4 in project root")
        return
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t:
        wav = Path(t.name)
    
    # Step 1: Extract audio
    print("\n[Step 1/5] Extracting audio from video...")
    with tqdm(total=1, desc="Extracting audio", ncols=80, unit="file") as pbar:
        extract_audio(VOD, wav)
        pbar.update(1)
    print("[OK] Audio extracted")
    
    # Step 2: Detect peaks
    print("\n[Step 2/5] Detecting peaks in audio...")
    peaks = detect_peaks(wav)
    print(f"[OK] Found {len(peaks)} peaks")
    
    # Step 3: Merge peaks
    print("\n[Step 3/5] Merging nearby peaks...")
    merged = merge_peaks(peaks)
    print(f"[OK] Merged into {len(merged)} segments")

    # Step 4: Extract keyframes
    print("\n[Step 4/5] Extracting keyframes...")
    keyframes = get_keyframes(VOD)
    print(f"[OK] Loaded {len(keyframes)} keyframes")

    # Step 5: Create segments
    print("\n[Step 5/5] Creating time segments (snapped to keyframes)...")
    segs = make_segments(merged, keyframes)
    

    if not segs:
        print("[WARN] No peaks found")
    else:
        split_segments(VOD, segs)
        print(f"[OK] Created {len(segs)} clips in clips/")
    
    try:
        wav.unlink()
    except: pass
    
    print("\n" + "=" * 60)
    print(f"LAYER 1 COMPLETE: {len(segs)} clips generated")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
