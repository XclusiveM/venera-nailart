"""Exercise price publication in an isolated checkout, including colliding amounts."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as directory:
    target = Path(directory)
    (target / 'scripts').mkdir()
    (target / 'data').mkdir()
    for source in list(ROOT.glob('*.html')) + list((ROOT / 'scripts').glob('*.py')):
        shutil.copy2(source, target / source.relative_to(ROOT))
    data = json.loads((ROOT / 'data/services.json').read_text())
    changes = {'mani-gel': 2777, 'corr-gel': 3111, 'corr-poly': 3222}
    for s in data['services']:
        if s['id'] in changes: s['price'] = changes[s['id']]
    next(e for e in data['extras'] if e['id'] == 'french')['price'] = 777
    (target / 'data/services.json').write_text(json.dumps(data, ensure_ascii=False))
    subprocess.run([sys.executable, 'scripts/sync_catalog.py', '--write'], cwd=target, check=True, capture_output=True)
    check = subprocess.run([sys.executable, 'scripts/sync_catalog.py', '--check'], cwd=target, capture_output=True, text=True)
    assert check.returncode == 0, check.stdout + check.stderr
    homepage = (target / 'index.html').read_text()
    assert 'data-price-id="mani-gel">2\u00a0777\u00a0₽' in homepage
    assert 'content="Маникюр с гель-лаком 2\u00a0777\u00a0₽' in homepage
    assert 'data-price-id="mani-gel">2\u00a0500' not in homepage
    manicure = (target / 'manikyur.html').read_text()
    assert 'data-price-id="french">777\u00a0₽' in manicure
    payloads = [json.loads(x) for x in re.findall(r'<script type="application/ld\+json">(.*?)</script>', manicure, re.S)]
    structured = json.dumps(payloads, ensure_ascii=False)
    assert '2777' in structured and '777' in structured
    assert '300 ₽' not in structured
    extensions = (target / 'narashchivanie-nogtey.html').read_text()
    assert '"sku": "corr-gel"' in extensions and '"price": "3111"' in extensions
    assert '"sku": "corr-poly"' in extensions and '"price": "3222"' in extensions
    # The unrelated correction system keeps the same 3000 amount.
    assert '"sku": "system"' in homepage and '"price": "3000"' in homepage
print('OK: publication synchronises visible prices, metadata, FAQ and independent structured offers')
