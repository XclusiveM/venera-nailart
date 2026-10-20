#!/usr/bin/env python3
"""Audit visible public reviews for exact listed salon URLs. No login, no CAPTCHA bypass.
Do not publish source review texts verbatim without the relevant permissions.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout

ROOT = Path("artifacts/reviews-audit")
ROOT.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "bumpix_venera": "https://bumpix.net/188382",
    "bumpix_julia": "https://bumpix.net/463374",
    "yandex_organization_213918968490": "https://yandex.ru/maps/org/veneranailart/213918968490/reviews/",
    "yandex_navigator_213918968490": "https://yandex.ru/navi/org/veneranailart/213918968490?si=mmb-87",
}
DATE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
SKIP = re.compile(r"^(?:Отзывы|Показать еще.*|Запись создана|‹|›|###|©20|Комментарии?)$", re.I)

def extract_bumpix(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    try: start = lines.index("Отзывы") + 1
    except ValueError: return []
    found = []
    i = start
    while i < len(lines):
        if lines[i] in ("Запись создана", "Вход", "Регистрация") or lines[i].startswith("©202"):
            break
        if DATE.match(lines[i]) and i + 2 < len(lines):
            d, author = lines[i], lines[i + 1]
            k = i + 2
            chunks = []
            while k < len(lines) and not DATE.match(lines[k]):
                if lines[k].startswith("Показать еще") or lines[k] in ("Запись создана","‹","›","###"):
                    break
                chunks.append(lines[k]); k += 1
            note = " ".join(chunks).strip()
            if note and not author.startswith("Комментарий"):
                found.append({"date": d, "author": author, "review": note})
            i = k
        else: i += 1
    unique = []
    seen = set()
    for p in found:
        key = (p["date"], p["author"], p["review"])
        if key not in seen:
            unique.append(p); seen.add(key)
    return unique

def inspect(browser, label, url):
    ctx = browser.new_context(locale="ru-RU", timezone_id="Europe/Moscow",
                              viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    row = {"label": label, "url": url, "status": "NOT_CHECKED", "clicks": 0,
           "reviews": [], "notes": []}
    try:
        res = pg.goto(url, wait_until="domcontentloaded", timeout=25000)
        pg.wait_for_timeout(1700)
        row["http"] = res.status if res else None
        row["final_url"] = pg.url
        row["title"] = pg.title()
        row["status"] = "LOADED"
        if label.startswith("bumpix"):
            for j in range(4):
                buttons = pg.get_by_text(re.compile(r"Показать\s+еще|Show more", re.I))
                if buttons.count() == 0: break
                try:
                    buttons.first.scroll_into_view_if_needed(timeout=4000)
                    buttons.first.click(timeout=5000)
                    pg.wait_for_timeout(1200)
                    row["clicks"] += 1
                except Exception as exc:
                    row["notes"].append("Expanding additional reviews failed: " + str(exc)[:170])
                    break
            row["reviews"] = extract_bumpix(pg.locator("body").inner_text(timeout=10000))
            row["visible_review_count"] = len(row["reviews"])
        else:
            body = pg.locator("body").inner_text(timeout=10000)
            row["body_excerpt"] = body[:3500]   # diagnostic, not review publication
            row["notes"].append("Yandex reviews must match org ID 213918968490; verify title before extraction.")
            pg.screenshot(path=str(ROOT / f"{label}.png"), full_page=False, timeout=10000)
    except Exception as exc:
        row["status"] = "UNAVAILABLE"
        row["notes"].append(str(exc)[:600])
    finally:
        ctx.close()
    return row

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    items = [inspect(browser, label, url) for label, url in SOURCES.items()]
    browser.close()

(ROOT / "audit.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
for x in items:
    print(json.dumps({k:v for k,v in x.items() if k not in ("reviews","body_excerpt")}, ensure_ascii=False))
print("Internal review audit only. Do not republish verbatim reviews without authorization.")
