#!/usr/bin/env python3
"""Build locally hosted, size-optimised portfolio photos from approved public source URLs.
Public display on live site still requires owner/photographer consent.
Only use fixed source URLs in src/portfolio.json, never search for private images.
"""
import io
import json
import sys
import time
import urllib.request
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT=Path(__file__).resolve().parent.parent
DATA=json.loads((ROOT/"src/portfolio.json").read_text(encoding="utf-8"))
OUT=ROOT/"assets/photos/gallery"
OUT.mkdir(parents=True,exist_ok=True)
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; VeneraPortfolioBuild/1.0)","Accept":"image/webp,image/jpeg,image/*"}
errors=[]
def save_one(rec):
    url=rec["source_image_url"]
    if not url.startswith("https://avatars.mds.yandex.net/get-altay/"):
        raise ValueError("Photo source must be an approved Yandex image host")
    data=None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=24) as resp:
                mime=resp.headers.get("Content-Type","")
                if not mime.startswith("image/"):raise RuntimeError("non-image content: "+mime)
                data=resp.read(4_000_001)
                if len(data)>4_000_000:raise RuntimeError("source image too large")
            break
        except Exception:
            if attempt==2:raise
            time.sleep(1+attempt)
    with Image.open(io.BytesIO(data)) as src:
        src=ImageOps.exif_transpose(src).convert("RGB")
        if src.width<200 or src.height<200:raise RuntimeError("source unexpectedly small")
        for label,maxwidth,q in (("thumb",550,78),("full",1400,86)):
            image=src.copy()
            image.thumbnail((maxwidth,maxwidth),Image.Resampling.LANCZOS)
            dest=ROOT/rec[label]
            dest.parent.mkdir(parents=True,exist_ok=True)
            image.save(dest,"WEBP",quality=q,method=6,exif=b"")
            print(f'{rec["id"]} {label}: {image.width}x{image.height}, {dest.stat().st_size} bytes',flush=True)
for photo in DATA["photos"]:
    try:save_one(photo)
    except Exception as exc:
        errors.append(f'{photo["id"]}: {exc}')
print(f'Built {len(DATA["photos"])-len(errors)} / {len(DATA["photos"])} photos; problems: {errors}',flush=True)
if errors:sys.exit(1)
