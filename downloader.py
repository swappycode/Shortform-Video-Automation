import subprocess
import sys
from pathlib import Path
import json
from datetime import datetime

ROOT = Path(".")
DOWNLOADS_DIR = ROOT / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

def get_output_path():
    """Generate output filename with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DOWNLOADS_DIR / f"video_{timestamp}.mp4"

def copy_to_vod(downloaded_file):
    """Copy downloaded file to vod.mp4 for processing"""
    import shutil
    vod_path = ROOT / "vod.mp4"
    shutil.copy2(downloaded_file, vod_path)
    print(f"\n📋 Copied to vod.mp4 for processing")
    return vod_path

def download_full_stream(url):
    """Download entire live stream or VOD"""
    print("=" * 60)
    print("📥 Downloading Full Stream/VOD")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"Output: {VOD_OUTPUT}\n")
    
    cmd = [
        "yt-dlp",
        "-f", "best[ext=mp4]/best",  # Best quality MP4
        "-o", str(VOD_OUTPUT),
        "--no-playlist",
        url
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("✅ Download Complete!")
        print(f"Saved to: {VOD_OUTPUT}")
        print("=" * 60)
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
    
    Args:
        url: YouTube URL
        start_time: Start time (format: HH:MM:SS or seconds)
        end_time: End time (format: HH:MM:SS or seconds) - optional
    """
    print("=" * 60)
    print("📥 Downloading Stream Segment")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"Start: {start_time}")
    if end_time:
        print(f"End: {end_time}")
    print(f"Output: {VOD_OUTPUT}\n")
    
    # Build yt-dlp command
    cmd = [
        "yt-dlp",
        "-f", "best[ext=mp4]/best",
        "-o", str(VOD_OUTPUT),
        "--no-playlist",
    ]
    
    # Add download sections for time range
    if end_time:
        cmd.extend(["--download-sections", f"*{start_time}-{end_time}"])
    else:
        cmd.extend(["--download-sections", f"*{start_time}-inf"])
    
    cmd.append(url)
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("✅ Download Complete!")
        print(f"Saved to: {VOD_OUTPUT}")
        print("=" * 60)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Download failed: {e}")
        return False
    except FileNotFoundError:
        print("\n❌ yt-dlp not found! Install it with: pip install yt-dlp")
        return False

def download_live_stream(url, duration=None):
    """
    Download live stream (will wait for stream to start if not live yet)
    
    Args:
        url: YouTube live stream URL
        duration: Optional max duration in seconds to record
    """
    print("=" * 60)
    print(" Downloading Live Stream")
    print("=" * 60)
    print(f"URL: {url}")
    if duration:
        print(f"Max Duration: {duration} seconds")
    print(f"Output: {VOD_OUTPUT}\n")
    
    cmd = [
        "yt-dlp",
        "-f", "best[ext=mp4]/best",
        "-o", str(VOD_OUTPUT),
        "--no-playlist",
        "--live-from-start",  # Start from beginning of live stream
    ]
    
    if duration:
        # Use ffmpeg to limit duration
        cmd.extend(["--downloader", "ffmpeg"])
        cmd.extend(["--downloader-args", f"ffmpeg:-t {duration}"])
    
    cmd.append(url)
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("✅ Download Complete!")
        print(f"Saved to: {VOD_OUTPUT}")
        print("=" * 60)
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
        print("\nExamples:")
        print("  python downloader.py https://youtube.com/watch?v=...")
        print("  python downloader.py https://youtube.com/watch?v=... 1:30:00 2:00:00")
        print("  python downloader.py https://youtube.com/watch?v=... 00:10:00")
        print("  python downloader.py https://youtube.com/watch?v=... --live 3600")
        return
    
    url = sys.argv[1]
    
    # Check for live stream mode
    if len(sys.argv) > 2 and sys.argv[2] == "--live":
        duration = int(sys.argv[3]) if len(sys.argv) > 3 else None
        download_live_stream(url, duration)
    # Check for segment download
    elif len(sys.argv) > 2:
        start_time = sys.argv[2]
        end_time = sys.argv[3] if len(sys.argv) > 3 else None
        download_stream_segment(url, start_time, end_time)
    # Full download
    else:
        download_full_stream(url)

if __name__ == "__main__":
    main()