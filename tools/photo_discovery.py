#!/usr/bin/env python3
"""Inventory publicly visible photo URLs for manual review. Never publish images automatically.
Read only public URLs. This script neither signs in nor bypasses access restrictions.
"""
import concurrent.futures
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path("artifacts/photo-source-audit")
OUT.mkdir(parents=True, exist_ok=True)
SOURCES = {
    "yandex_maps_ru": "https://yandex.ru/maps/org/veneranailart/213918968490/photos/",
    "yandex_maps_en": "https://yandex.com/maps/org/veneranailart/213918968490/photos/",
    "yandex_navi": "https://yandex.ru/navi/org/veneranailart/213918968490",
    "bumpix_venera": "https://bumpix.net/188382",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
           "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,image/*,*/*;q=0.8"}
PATTERN = re.compile(r"""(?:https?:)?(?://|\\/\\/)(?:avatars\.mds\.yandex\.net|get-[\w.-]+\.yandex\.net|[\w.-]*bumpix\.net)[^\s"'\u003c>\\]{8,350}""", re.I)
IMGTAG = re.compile(r"""<(?:img|meta)\b[^>]*(?:src|content)=["']([^"']+)["']""", re.I)
SAFE_HOSTS = ("avatars.mds.yandex.net", "bumpix.net", "storage.yandexcloud.net")

def fetch(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=15) as res:
            body = res.read(3_000_000)
            return dict(status=res.status, final_url=res.url, size=len(body), text=body.decode("utf8", "replace"), error="")
    except Exception as exc:
        return dict(status=None, final_url="", size=0, text="", error=str(exc)[:300])

def clean_url(s, base):
    s = html.unescape(s).replace("\\/", "/")
    s = s.split(" ")[0].split('"')[0].split("'")[0].strip("),;]}")
    if s.startswith("//"):
        s = "https:" + s
    if s.startswith("/"):
        s = urllib.parse.urljoin(base, s)
    if not s.startswith("https://"):
        return ""
    host = (urllib.parse.urlsplit(s).hostname or "").lower()
    if not any(host == p or host.endswith("." + p) for p in SAFE_HOSTS):
        return ""
    return s

report = {"sources": {}, "candidate_count": 0, "note": "Discovery only. No image has been approved for use."}
candidates = []
for key, url in SOURCES.items():
    resp = fetch(url)
    report["sources"][key] = {k: v for k, v in resp.items() if k != "text"}
    text = resp["text"]
    raw = PATTERN.findall(text) + IMGTAG.findall(text)
    found = []
    for item in raw:
        candidate = clean_url(item, url)
        if candidate and candidate not in found:
            found.append(candidate)
            if candidate not in [c["url"] for c in candidates]:
                candidates.append({"source": key, "url": candidate})
    report["sources"][key]["extracted_image_candidates"] = len(found)

# Consolidate Yandex's repeated thumbnail URLs and its size placeholder to the same public photo.
# This does not enumerate hidden/private photo IDs, and it does not bypass access controls.
gallery = []
seen_photo_ids = set()
for entry in candidates:
    u = entry["url"]
    if "/get-altay/" in u:
        bits = u.split("/")
        if len(bits) < 7:
            continue
        photo_key = "/".join(bits[:6])
        if photo_key in seen_photo_ids:
            continue
        seen_photo_ids.add(photo_key)
        gallery.append({**entry, "url": photo_key + "/XXL_height", "photo_id": photo_key})
# Add any other photo-like sources after core gallery, without icon/avatar/logo services.
report["gallery_candidates"] = gallery
# Download only from the photo collection after deduplication.
chosen = gallery[:72]
def get_image(index_and_info):
    i, item = index_and_info
    url = item["url"]
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=15) as r:
            ct = r.headers.get("Content-Type", "").split(";")[0].strip()
            if ct not in ("image/jpeg", "image/png", "image/webp"):
                return {"n": i, **item, "error": "Unexpected content type: " + ct}
            data = r.read(2_000_001)
            if len(data) > 2_000_000:
                return {"n": i, **item, "error": "Image exceeded size limit"}
            ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[ct]
            filename = f"{i:02d}-{item['source']}{ext}"
            (OUT / filename).write_bytes(data)
            return {"n": i, **item, "file": filename, "bytes": len(data)}
    except Exception as exc:
        return {"n": i, **item, "error": str(exc)[:180]}

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    images = list(pool.map(get_image, enumerate(chosen, 1)))
report["candidate_count"] = len(candidates)
report["images"] = images
(OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
(OUT / "README.txt").write_text(
    "PUBLIC PHOTO CANDIDATES ONLY — NOT CLEARED FOR REDISTRIBUTION.\n"
    "Before adding to the website, verify that this is the correct salon, the work is by that studio,\n"
    "the photographer and any visible client consent, and the right to republish.\n"
    "Not all photos in Yandex Maps may be owned by the business.\n", encoding="utf8")
print(json.dumps({
    "sources": report["sources"],
    "candidates": len(candidates),
    "downloaded": len([x for x in images if "file" in x]),
    "errors": [x for x in images if "error" in x][:5]
}, ensure_ascii=False, indent=2))
