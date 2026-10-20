"""Статические проверки: ссылки и якоря, noindex, нет внешних картинок/скриптов, нет латинского бренда в видимых заголовках,
нет запрещённых медицинских формулировок, JSON-LD валиден, сборка актуальна."""
import json, re, subprocess, sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
ROOT = Path(__file__).resolve().parents[1]
PAGES = sorted(p.name for p in ROOT.glob('*.html'))
BANNED = re.compile(r'лечим|вылеч|лечение вросш|врач-подолог|медицинск(ий|ого) педикюр|онихомикоз|гарантированн', re.I)


class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.ids = set(); self.res = []; self.ld = []; self._ld = False; self.title = ''; self._t = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'): self.ids.add(a['id'])
        if tag == 'a' and a.get('href'): self.links.append(a['href'])
        if tag in ('img', 'script', 'iframe') and a.get('src'): self.res.append(a['src'])
        if tag == 'link' and a.get('rel') in ('stylesheet', 'preload'): self.res.append(a['href'])
        if tag == 'script' and a.get('type') == 'application/ld+json': self._ld = True
        if tag == 'title': self._t = True
    def handle_endtag(self, tag):
        if tag == 'script': self._ld = False
        if tag == 'title': self._t = False
    def handle_data(self, d):
        if self._ld: self.ld.append(d)
        if self._t: self.title += d


err = []
for name in PAGES:
    path = ROOT / name; src = path.read_text(encoding='utf-8'); p = P(); p.feed(src)
    if 'name="robots" content="noindex,nofollow"' not in src: err.append(f'{name}: нет noindex')
    if 'NAILART' in p.title: err.append(f'{name}: латиница в title')
    if BANNED.search(src): err.append(f'{name}: запрещённая формулировка «{BANNED.search(src).group(0)}»')
    for r in p.res:
        if r.startswith(('http:', 'https:', '//')): err.append(f'{name}: внешний ресурс {r}')
    for u in p.links:
        if u.startswith(('https:', 'http:', 'mailto:', 'tel:', 'data:', '//')): continue
        parsed = urlsplit(u)
        target = ROOT / parsed.path if parsed.path else path
        if parsed.path and not target.is_file():
            err.append(f'{name}: битая ссылка {u}')
            continue
        if parsed.fragment:
            tp = P(); tp.feed(target.read_text(encoding='utf-8'))
            if parsed.fragment not in tp.ids: err.append(f'{name}: битый якорь {u}')
    for j in p.ld:
        try: json.loads(j)
        except Exception as e: err.append(f'{name}: JSON-LD не парсится: {e}')
    if not p.ld and name not in ('politika.html', 'soglasie.html'): err.append(f'{name}: нет JSON-LD')
r = subprocess.run([sys.executable, str(ROOT / 'src' / 'build.py'), '--check'], capture_output=True, text=True)
if r.returncode: err.append(r.stderr.strip() or r.stdout.strip())
if err: sys.exit('\n'.join(err))
print(f'OK: {len(PAGES)} страниц проверено')
