import os, time
from pathlib import Path
from datetime import datetime, timedelta, timezone
import random


from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Folder containing final rendered videos
UPLOAD_DIR = Path("output")

# Upload interval (minutes between each scheduled upload)
UPLOAD_INTERVAL_MINUTES = 60   # ← CHANGE THIS ANY TIME

# OAuth scope for uploading videos
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_youtube():
    flow = InstalledAppFlow.from_client_secrets_file(
        "uploader/client_secret.json", SCOPES
    )
    creds = flow.run_local_server(port=0)
    return build("youtube", "v3", credentials=creds)


def upload_video(youtube, file_path, title, description, tags, publish_time):
    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "private",  # REQUIRED for scheduling
            "publishAt": publish_time.isoformat(),  # TIMESTAMP in UTC
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)

    print(f"\n🚀 Scheduling upload for: {publish_time}")
    print(f"📤 File: {file_path}")

    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploading: {int(status.progress() * 100)}%")

    print(f"✅ Scheduled video: {response['id']} at {publish_time}")
    return response['id']


COUNTER_FILE = Path("uploader/title_counter.txt")

def get_next_upload_number():
    """Returns the next ascending number, stored permanently."""
    # If the counter does not exist, create it starting at 0
    if not COUNTER_FILE.exists():
        COUNTER_FILE.write_text("0")

    # Read last number
    last_number = int(COUNTER_FILE.read_text().strip())

    # Increment
    next_number = last_number + 1

    # Save back to file
    COUNTER_FILE.write_text(str(next_number))

    return next_number


def auto_title(_):
    titles = [
        "INSANE CLUTCH 😂🔥",
        "THIS MOMENT HAD ME SCREAMING 🤯🔥",
        "WHAT JUST HAPPENED 😭🔥",
        "TOP TIER GAMING MOMENT 💀🔥",
        "NO WAY THIS ACTUALLY WORKED 🤣🔥",
        "GAMING MOMENT OF THE DAY 🔥🎮",
        "YOU WON'T BELIEVE THIS 😭💀",
        "ABSOLUTE CHAOS 😂🔥",
        "SKILL ISSUE? NOT TODAY 🤣🔥",
        "THIS GOES HARD 🔥🔥🔥",
        "WHY AM I LIKE THIS 💀🤣",
        "GOD TIER MOVE 😭🔥",
        "BRO REALLY DID THAT 🤯🔥",
        "LEGENDARY MOMENT 😎🔥",
    ]
    number = get_next_upload_number()
    chosen = random.choice(titles)

    return f"{chosen} | [SWAPPYHYPE] | {number}"

def auto_description():
    return (
        "LIVE ON SATURDAY AND SUNDAY\n\n"
        "#gaming #indiafamous #india\n"
        "THIS STREAM IS A JOKE — DON'T TAKE IT SERIOUSLY. "
        "ALL THINGS SAID IN THIS STREAM ARE JOKES.\n\n"
        "lol 😭🔥\n\n"
        "#gaming #indiafamous #india #discord #marvelrivals "
        "#horrorstories #live #thrill #jee #darksouls "
        "#eldenring #valorant #indiagaming #fortnite #games "
        "#battlefield\n\n"
        "Enjoy this highlight! ❤️🔥\n"
        "Subscribe for daily shorts ❤️\n"
    )



def auto_tags():
    return ["shorts", "viral", "funny", "gaming", "clip", "meme", "edit","brainrot","swappyhype", "indiafamous","india","valorant","fortnite","twitch","roblox"]


def main():
    youtube = get_youtube()
    files = sorted(UPLOAD_DIR.glob("*.mp4"))

    if not files:
        print("❌ No videos found in output/")
        return

    print(f"📦 Found {len(files)} videos to schedule.\n")

    # First upload starts 5 minutes from now
    scheduled_time = datetime.now(timezone.utc) + timedelta(minutes=5)

    for f in files:
        title = auto_title(f.name)
        description = auto_description()
        tags = auto_tags()

        upload_video(
            youtube,
            str(f),
            title,
            description,
            tags,
            scheduled_time
        )

        # Schedule next upload
        scheduled_time += timedelta(minutes=UPLOAD_INTERVAL_MINUTES)
        time.sleep(2)  # tiny delay for stability

    print("\n🎉 ALL VIDEOS SCHEDULED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
