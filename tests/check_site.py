"""Статические проверки: ссылки и якоря, noindex, нет внешних картинок/скриптов, нет латинского бренда в видимых заголовках,
нет запрещённых медицинских формулировок, JSON-LD валиден, сборка актуальна."""
import json, re, subprocess, sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
ROOT = Path(__file__).resolve().parents[1]
PAGES = sorted(p.name for p in ROOT.glob('*.html')) + sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'admin-preview').glob('*.html'))
BANNED = re.compile(r'лечим|вылеч|лечение вросш|врач-подолог|медицинск(ий|ого) педикюр|онихомикоз|гарантированн', re.I)


class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.ids = set(); self.res = []; self.ld = []; self._ld = False; self.title = ''; self._t = False; self.problems = []; self.h1 = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if len(a) != len(attrs): self.problems.append('повторяющиеся атрибуты ' + tag)
        if a.get('id') in self.ids: self.problems.append('повторяющийся ID ' + a['id'])
        if tag == 'h1': self.h1 += 1
        if tag == 'img' and 'alt' not in a: self.problems.append('изображение без alt')
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
    err.extend(name + ': ' + problem for problem in p.problems)
    if p.h1 != 1: err.append(f'{name}: требуется один h1, найдено {p.h1}')
    if '</span<h2>' in src: err.append(f'{name}: повреждён заголовок раздела')
    if 'name="robots" content="noindex,nofollow"' not in src: err.append(f'{name}: нет noindex')
    if 'NAILART' in p.title: err.append(f'{name}: латиница в title')
    if BANNED.search(src): err.append(f'{name}: запрещённая формулировка «{BANNED.search(src).group(0)}»')
    for r in p.res:
        if r.startswith(('http:', 'https:', '//')): err.append(f'{name}: внешний ресурс {r}')
        elif not r.startswith(('data:', 'blob:')) and not (path.parent / urlsplit(r).path).is_file(): err.append(f'{name}: отсутствует ресурс {r}')
    for u in p.links:
        if u.startswith(('https:', 'http:', 'mailto:', 'tel:', 'data:', '//')): continue
        parsed = urlsplit(u)
        target = path.parent / parsed.path if parsed.path else path
        if target.is_dir(): target = target / 'index.html'
        if parsed.path and not target.is_file():
            err.append(f'{name}: битая ссылка {u}')
            continue
        if parsed.fragment:
            tp = P(); tp.feed(target.read_text(encoding='utf-8'))
            if parsed.fragment not in tp.ids: err.append(f'{name}: битый якорь {u}')
    for j in p.ld:
        try: json.loads(j)
        except Exception as e: err.append(f'{name}: JSON-LD не парсится: {e}')
    if not p.ld and name not in ('politika.html', 'soglasie.html') and not name.startswith('admin-preview/'): err.append(f'{name}: нет JSON-LD')
    for attrs, script in re.findall(r'<script\b([^>]*)>(.*?)</script>', src, re.S):
        if 'src=' in attrs or ('type=' in attrs and not any(t in attrs for t in ('javascript', 'module'))): continue
        if not script.strip(): continue
        check = subprocess.run(['node', '--check', '--input-type=module'], input=script, capture_output=True, text=True)
        if check.returncode: err.append(name + ': ошибка встроенного JavaScript: ' + check.stderr.strip())
r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'sync_catalog.py'), '--check'], capture_output=True, text=True)
if r.returncode: err.append(r.stderr.strip() or r.stdout.strip())
if err: sys.exit('\n'.join(err))
print(f'OK: {len(PAGES)} страниц проверено')
