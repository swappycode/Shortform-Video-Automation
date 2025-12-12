#!/usr/bin/env python3
"""
download_models.py

Downloads default models (large-v3 + medium) into HF cache or a custom folder.

Usage:
  python download_models.py                 # downloads default models to HF cache (~/.cache/huggingface)
  python download_models.py --dest "C:\ProgramData\ShortsStudio\models"
  python download_models.py openai/whisper-medium --dest "C:\models"
"""
import os
import sys
import argparse
from huggingface_hub import snapshot_download

DEFAULT_MODELS = [
    "openai/whisper-large-v3",
    "openai/whisper-medium"
]

def main():
    p = argparse.ArgumentParser(description="Download Hugging Face models (default: large-v3 + medium).")
    p.add_argument("models", nargs="*", default=DEFAULT_MODELS, help="Model repo ids (space separated).")
    p.add_argument("--dest", "-d", default=None, help="Destination folder for HF cache (sets HF_HOME).")
    p.add_argument("--no-progress", action="store_true", help="Disable extra prints.")
    args = p.parse_args()

    if args.dest:
        dest = os.path.abspath(args.dest)
        os.makedirs(dest, exist_ok=True)
        os.environ["HF_HOME"] = dest

    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    if hf_token:
        os.environ["HUGGINGFACE_HUB_TOKEN"] = hf_token

    print("HF_HOME:", os.environ.get("HF_HOME", "(default cache)"))
    print("Models to download:", args.models)

    for m in args.models:
        try:
            print(f"\nDownloading model: {m}")
            path = snapshot_download(repo_id=m, repo_type="model")
            print("Downloaded to:", path)
        except Exception as e:
            print("ERROR downloading", m)
            print("Exception:", str(e))
            print("If the model is private, set HF_TOKEN environment variable.")
            sys.exit(1)

    print("\nAll requested models downloaded successfully.")

if __name__ == "__main__":
    main()
