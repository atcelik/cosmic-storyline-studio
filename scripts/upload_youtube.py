#!/usr/bin/env python3
"""Upload a finished episode to YouTube as PRIVATE (owner publishes from YouTube Studio).

Usage: python scripts/upload_youtube.py VIDEO.mp4 DESCRIPTION.txt "Title" [THUMB.png]

Needs env: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (GitHub Actions secrets).
Scope used: youtube.upload only. Captions (.srt) are added by hand in Studio.
Free: YouTube Data API v3 quota, about 1600 units per upload (10000/day).
"""
import os
import sys

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

TAGS = ["space", "universe", "NASA", "documentary", "astronomy", "space mysteries"]


def main(video, desc_path, title, thumb=None):
    for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"):
        if not os.environ.get(k):
            sys.exit(f"Missing secret {k}. See docs/YOUTUBE_UPLOAD_TR.md")
    if len(title) > 100:
        sys.exit("Title is longer than 100 characters")
    description = open(desc_path, encoding="utf-8").read()
    if len(description.encode("utf-8")) > 5000:
        sys.exit("Description is over YouTube's 5000-byte limit")

    creds = Credentials(
        None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": TAGS,
            "categoryId": "27",  # Education
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,  # synthetic voice + our 3D scenes
        },
    }
    media = MediaFileUpload(video, chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    try:
        while resp is None:
            status, resp = req.next_chunk()
            if status:
                print(f"upload {int(status.progress() * 100)}%", flush=True)
    except HttpError as e:
        sys.exit(f"YouTube API error: {e}")
    vid = resp["id"]
    print(f"Uploaded (private): https://studio.youtube.com/video/{vid}/edit")
    if thumb and os.path.exists(thumb):
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumb)).execute()
            print("Thumbnail set")
        except HttpError as e:
            print(f"Thumbnail not set (channel may need phone verification): {e}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    main(*sys.argv[1:5])
