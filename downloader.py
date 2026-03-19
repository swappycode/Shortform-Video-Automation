import subprocess
import sys
from pathlib import Path
import json
from datetime import datetime

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

ROOT = Path(".")
DOWNLOADS_DIR = ROOT / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

def get_output_path():
    """Generate output filename with timestamp (yt-dlp will output MKV)"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DOWNLOADS_DIR / f"video_{timestamp}.mkv"

def convert_to_mp4(input_file):
    """Convert downloaded MKV → MP4 using GPU for maximum speed"""
    output_file = input_file.with_suffix(".mp4")

    cmd = [
        "ffmpeg",
        "-y",
        "-hwaccel", "cuda",
        "-i", str(input_file),
        "-c:v", "h264_nvenc",
        "-preset", "p4",       # Good balance of speed/quality
        "-rc", "vbr",
        "-cq", "19",           # Lower = better; 19 = high quality
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_file)
    ]

    print("\n⚡ GPU Converting MKV → MP4 (NVENC)...")

    try:
        subprocess.run(cmd, check=True)
        print(f"✅ GPU Conversion Complete: {output_file}")

        input_file.unlink(missing_ok=True)
        print("🗑️ Removed MKV after GPU conversion")

        return output_file

    except subprocess.CalledProcessError:
        print("❌ GPU Conversion failed! Keeping MKV.")
        return input_file


    except subprocess.CalledProcessError:
        print("❌ Conversion failed! Keeping MKV.")
        return input_file

def copy_to_vod(downloaded_file):
    """Copy downloaded file to vod.mp4 for processing"""
    import shutil
    vod_path = ROOT / "vod.mp4"
    shutil.copy2(downloaded_file, vod_path)
    print(f"\n📋 Copied to vod.mp4 for processing")
    return vod_path

def download_full_stream(url):
    """Download entire live stream or VOD"""
    output_path = get_output_path()
    
    print("=" * 60)
    print("📥 Downloading Full Stream/VOD")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"Output: {output_path}\n")
    
    cmd = [
        "yt-dlp",
        "-f", "bestvideo+bestaudio/best",
        "--merge-output-format", "mkv",
        "-o", str(output_path),
        "--no-playlist",
        url
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("✅ Download Complete!")
        print("=" * 60)

        # Convert MKV → MP4
        mp4_file = convert_to_mp4(output_path)

        # Copy to vod.mp4
        copy_to_vod(mp4_file)
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Download failed: {e}")
        return False
    except FileNotFoundError:
        print("\n❌ yt-dlp not found! Install it with: pip install yt-dlp")
        return False

def download_stream_segment(url, start_time, end_time=None):
    """
    Download a specific segment of a live stream or VOD
    """
    output_path = get_output_path()
    
    print("=" * 60)
    print("📥 Downloading Stream Segment")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"Start: {start_time}")
    if end_time:
        print(f"End: {end_time}")
    print(f"Output: {output_path}\n")
    
    cmd = [
        "yt-dlp",
        "-f", "bestvideo+bestaudio/best",
        "--merge-output-format", "mkv",
        "-o", str(output_path),
        "--no-playlist",
    ]
    
    if end_time:
        cmd.extend(["--download-sections", f"*{start_time}-{end_time}"])
    else:
        cmd.extend(["--download-sections", f"*{start_time}-inf"])
    
    cmd.append(url)
    
    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("✅ Download Complete!")
        print("=" * 60)

        # Convert MKV → MP4
        mp4_file = convert_to_mp4(output_path)

        # Copy to vod.mp4
        copy_to_vod(mp4_file)
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Download failed: {e}")
        return False
    except FileNotFoundError:
        print("\n❌ yt-dlp not found! Install it with: pip install yt-dlp")
        return False

def download_live_stream(url, duration=None):
    """Download YouTube live stream"""
    output_path = get_output_path()
    
    print("=" * 60)
    print("📡 Downloading Live Stream")
    print("=" * 60)
    print(f"URL: {url}")
    if duration:
        print(f"Max Duration: {duration} seconds")
    print(f"Output: {output_path}\n")
    
    cmd = [
        "yt-dlp",
        "-f", "bestvideo+bestaudio/best",
        "--merge-output-format", "mkv",
        "-o", str(output_path),
        "--no-playlist",
        "--live-from-start",
    ]
    
    if duration:
        cmd.extend(["--downloader", "ffmpeg"])
        cmd.extend(["--downloader-args", f"ffmpeg:-t {duration}"])
    
    cmd.append(url)
    
    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("✅ Download Complete!")
        print("=" * 60)

        # Convert MKV → MP4
        mp4_file = convert_to_mp4(output_path)

        # Copy to vod.mp4
        copy_to_vod(mp4_file)
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Download failed: {e}")
        return False
    except FileNotFoundError:
        print("\n❌ yt-dlp not found! Install it with: pip install yt-dlp")
        return False

def main():
    """CLI interface for downloader"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Full download:     python downloader.py <URL>")
        print("  Segment download:  python downloader.py <URL> <start_time> [end_time]")
        print("  Live stream:       python downloader.py <URL> --live [duration]")
        return
    
    url = sys.argv[1]
    
    if len(sys.argv) > 2 and sys.argv[2] == "--live":
        duration = int(sys.argv[3]) if len(sys.argv) > 3 else None
        download_live_stream(url, duration)
    elif len(sys.argv) > 2:
        start_time = sys.argv[2]
        end_time = sys.argv[3] if len(sys.argv) > 3 else None
        download_stream_segment(url, start_time, end_time)
    else:
        download_full_stream(url)

if __name__ == "__main__":
    main()
