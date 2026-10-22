#!/usr/bin/env python3
"""Проверка и безопасная синхронизация статического сайта с каталогом услуг.
Использование: python3 scripts/sync_catalog.py --check | --write
Только стандартная библиотека Python.
"""
import argparse
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "services.json"
SITE_BLOCK = re.compile(r'(<script type="application/json" id="site-data">)(.*?)(</script>)', re.S)
TABLE = re.compile(r'(<table class="prices">)(.*?)(</table>)', re.S)
ROW = re.compile(r'(<tr(?![^>]*class="cat")[^>]*>)(.*?)(</tr>)', re.S)
TD = re.compile(r'(<td[^>]*>)(.*?)(</td>)', re.S)
BUTTON = re.compile(r'data-info="([^"]+)"')
SMALL = re.compile(r'<small>.*?</small>', re.S)


def validate(d):
    if d.get("schemaVersion") != 1:
        raise ValueError("Неверная версия каталога")
    services, cats, extras = d.get("services"), d.get("categories"), d.get("extras")
    if not all(isinstance(x, list) for x in (services, cats, extras)):
        raise ValueError("Не найдены списки services/categories/extras")
    cat_ids = {x["id"] for x in cats}
    seen = set()
    for item in services:
        sid = item.get("id")
        if not isinstance(sid, str) or not re.fullmatch(r"[a-z0-9-]+", sid) or sid in seen:
            raise ValueError("Повтор или неверный ID: " + str(sid))
        seen.add(sid)
        if not isinstance(item.get("name"), str) or not item["name"].strip():
            raise ValueError("Отсутствует название " + sid)
        if item.get("cat") not in cat_ids:
            raise ValueError("Неизвестная категория " + sid)
        if item.get("status", "published") not in {"published", "draft", "hidden", "archived"}:
            raise ValueError("Неверный статус " + sid)
        for key, lower in (("price", 0), ("min", 1)):
            value = item.get(key)
            if value is not None and (type(value) is not int or value < lower):
                raise ValueError("Неверное поле " + key + " в " + sid)
    extra_ids = set()
    for item in extras:
        sid = item.get("id")
        if not isinstance(sid, str) or sid in extra_ids:
            raise ValueError("Неверный ID дополнения")
        extra_ids.add(sid)
        if not isinstance(item.get("name"), str) or not item["name"].strip():
            raise ValueError("Нет названия дополнения")
        if type(item.get("price")) is not int or item["price"] < 0:
            raise ValueError("Неверная цена дополнения")
    return services, cats, extras


def duration(m):
    if m is None:
        return ""
    h, minutes = divmod(m, 60)
    return (str(h) + " ч" if h else "") + (" " if h and minutes else "") + (str(minutes) + " мин" if minutes else "")


def replace_prices(content, old_services, services):
    by_id = {s["id"]: s for s in services}
    by_old_name = {s["name"]: by_id[s["id"]] for s in old_services if s["id"] in by_id}

    def table_repl(match):
        def row_repl(row):
            cells = list(TD.finditer(row.group(2)))
            if len(cells) != 2:
                return row.group(0)
            label = cells[0].group(2)
            button = BUTTON.search(label)
            if button:
                old_name = html.unescape(button.group(1))
            else:
                old_name = html.unescape(re.sub(r"<[^>]*>", "", SMALL.sub("", label))).strip()
            item = by_old_name.get(old_name)
            if not item:
                return row.group(0)
            if item.get("status", "published") != "published":
                return ""  # скрываем из статического прайса
            title = html.escape(item["name"])
            if button:
                label = label.replace(button.group(1), html.escape(item["name"], quote=True))
                label = re.sub(r"^.*?(?=<button)", title + " ", label, count=1, flags=re.S)
            else:
                label = re.sub(r"^.*?(?=<small>|$)", title, label, count=1, flags=re.S)
            details = " · ".join(x for x in (duration(item.get("min")), item.get("note", "")) if x)
            if SMALL.search(label):
                label = SMALL.sub("<small>" + html.escape(details) + "</small>", label, count=1)
            elif details:
                label += "<small>" + html.escape(details) + "</small>"
            price = "По запросу" if item.get("price") is None else f'{item["price"]:,}'.replace(",", " ") + " ₽"
            a, b = cells
            inner = row.group(2)
            inner = inner[:a.start(2)] + label + inner[a.end(2):b.start(2)] + html.escape(price) + inner[b.end(2):]
            return row.group(1) + inner + row.group(3)
        return match.group(1) + ROW.sub(row_repl, match.group(2)) + match.group(3)
    return TABLE.sub(table_repl, content)


def check_missing_services(path, services):
    """Detect newly published services absent from the static price table.

    Only the main price list is expected to contain every service; category
    tables on other pages are intentionally partial.
    """
    if path.name != "ceny.html":
        return []
    source = path.read_text(encoding="utf-8")
    tables = TABLE.findall(source)
    if not tables:
        return ["ceny.html: отсутствует таблица прайса"]
    text = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", body)) for _, body, _ in tables)
    missing = [s["name"] for s in services
               if s.get("status", "published") == "published"
               and s["name"] not in text]
    return ["ceny.html: в таблице отсутствует услуга: " + name for name in missing]


def stale_price_locations(path, old_services, services):
    """Report old unambiguous ₽ amounts outside embedded catalog JSON with line numbers.

    A shared price is not unambiguously attributable to one service, so it is
    intentionally not flagged without additional service context.
    """
    original = path.read_text(encoding="utf-8")
    visible = SITE_BLOCK.sub(lambda m: m.group(1) + m.group(3), original)
    current = {x["id"]: x for x in services}
    valid_prices = {x.get("price") for x in services if x.get("price") is not None}
    findings = []
    for old in old_services:
        new = current.get(old.get("id"))
        before = old.get("price")
        if not new or before is None or before == new.get("price") or before in valid_prices:
            continue
        # Match either spaces, NBSP or narrow NBSP as thousand separators.
        digits = str(before)
        pattern = r"[\\s\\u00a0\\u202f]*".join(re.escape(digits[max(0, len(digits) % 3):][i:i+3]) for i in range(0, len(digits[max(0, len(digits) % 3):]), 3)) if len(digits) <= 3 else re.escape(digits[:-3]) + r"[\\s\\u00a0\\u202f]*" + re.escape(digits[-3:])
        for match in re.finditer(r"(?<!\\d)" + pattern + r"\\s*₽", visible):
            line = visible.count("\\n", 0, match.start()) + 1
            findings.append(f"{path.name}:{line}: возможно устаревшая цена {match.group(0)!r} (услуга {old['id']}, актуально {new.get('price')} ₽)")
    return sorted(set(findings))


def process(path, services, cats, extras, write):
    original = path.read_text(encoding="utf-8")
    match = SITE_BLOCK.search(original)
    if not match:
        return False
    embedded = json.loads(match.group(2))
    old_services = embedded.get("services", [])
    embedded.update(services=[s for s in services if s.get("status", "published") == "published"],
                    cats=cats,
                    extras=[e for e in extras if e.get("status", "published") == "published"])
    updated = original[:match.start(2)] + json.dumps(embedded, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c") + original[match.end(2):]
    updated = replace_prices(updated, old_services, services)
    if updated != original:
        if write:
            path.write_text(updated, encoding="utf-8")
        return True
    return False


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    services, cats, extras = validate(json.loads(DATA.read_text(encoding="utf-8")))
    pages = sorted(ROOT.glob("*.html"))
    stale = []
    for p in pages:
        match = SITE_BLOCK.search(p.read_text(encoding="utf-8"))
        if match:
            previous = json.loads(match.group(2)).get("services", [])
            stale.extend(stale_price_locations(p, previous, services))
    changed = [str(p.relative_to(ROOT)) for p in pages if process(p, services, cats, extras, args.write)]
    missing = check_missing_services(ROOT / "ceny.html", services)
    if missing:
        print("\n".join(missing), file=sys.stderr)
    if stale:
        print("\n".join(stale), file=sys.stderr)
    if changed:
        print(("Синхронизированы: " if args.write else "Требуется синхронизация: ") + ", ".join(changed))
    else:
        print("Каталог и HTML синхронизированы")
    return 1 if (args.check and changed) or missing or (args.check and stale) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, json.JSONDecodeError) as error:
        print("Ошибка каталога:", error, file=sys.stderr)
        sys.exit(2)
