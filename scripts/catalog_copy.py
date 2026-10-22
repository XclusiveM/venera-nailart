"""Stable catalog references for visible copy, metadata and structured offers."""
import html
import json
import re

TOKEN = re.compile(r'\{(price|duration|min-price):([a-z0-9,-]+)\}')
BOUND = re.compile(r'(<span\b[^>]*data-(price|duration)-id="([a-z0-9-]+)"[^>]*>).*?(</span>)', re.S)
TEMPLATE_TAG = re.compile(r'<(title|meta)\b[^>]*data-catalog-template="([^"]*)"[^>]*>(?:.*?</title>)?', re.S)
LD = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)


def render_copy(source, services, extras, old_services):
    current = {x['id']: x for x in services + extras if x.get('status', 'published') == 'published'}
    old_names = {s['name']: s['id'] for s in old_services if s.get('master', 'venera') == 'venera'}
    names = {s['name']: s['id'] for s in services if s.get('master', 'venera') == 'venera'}
    names = {**old_names, **names}

    def value(kind, sid):
        if kind == 'min-price':
            values = [current.get(key, {}).get('price') for key in sid.split(',')]
            return 'по запросу' if any(n is None for n in values) else f'{min(values):,}'.replace(',', '\u00a0') + '\u00a0₽'
        item = current.get(sid, {})
        n = item.get('price' if kind == 'price' else 'min')
        if n is None:
            return 'по запросу'
        if kind == 'price':
            return f'{n:,}'.replace(',', '\u00a0') + '\u00a0₽'
        h, m = divmod(n, 60)
        return ' '.join(([f'{h} ч'] if h else []) + ([f'{m} мин'] if m else []))

    def expand(text):
        return TOKEN.sub(lambda m: value(m[1], m[2]), text)

    source = BOUND.sub(lambda m: m[1] + html.escape(value(m[2], m[3])) + m[4], source)

    def render_tag(m):
        result = html.escape(expand(html.unescape(m[2])), quote=True)
        if m[1] == 'title':
            opening = m[0].split('>', 1)[0] + '>'
            return opening + result + '</title>'
        return re.sub(r'\bcontent="[^"]*"', lambda _: 'content="' + result + '"', m[0], count=1)

    source = TEMPLATE_TAG.sub(render_tag, source)
    faqs = []
    for question, answer in re.findall(r'<details><summary>(.*?)</summary><p>(.*?)</p></details>', source, re.S):
        clean = lambda text: html.unescape(re.sub(r'<[^>]*>', '', text))
        faqs.append({'@type': 'Question', 'name': clean(question),
                     'acceptedAnswer': {'@type': 'Answer', 'text': clean(answer)}})

    def ld_repl(m):
        def walk(obj):
            if isinstance(obj, list):
                return [v for child in obj if (v := walk(child)) is not None]
            if not isinstance(obj, dict):
                return obj
            if obj.get('@type') == 'FAQPage' and faqs:
                obj['mainEntity'] = faqs
            if obj.get('@type') == 'Offer':
                name = obj.get('itemOffered', {}).get('name') or obj.get('name')
                sid = obj.get('sku') or names.get(name)
                if sid:
                    item = current.get(sid)
                    if not item or item.get('price') is None:
                        return None
                    obj.update(sku=sid, price=str(item['price']))
                    if obj.get('name'):
                        obj['name'] = item['name']
                    if isinstance(obj.get('itemOffered'), dict):
                        obj['itemOffered']['name'] = item['name']
            if obj.get('@type') == 'NailSalon' and 'priceRange' in obj:
                prices = [s['price'] for s in services if s.get('master', 'venera') == 'venera' and s.get('status', 'published') == 'published' and s.get('price') is not None]
                if prices:
                    obj['priceRange'] = str(min(prices)) + '–' + str(max(prices)) + ' ₽'
            return {key: walk(val) for key, val in obj.items()}
        data = walk(json.loads(m[2]))
        return m[1] + json.dumps(data, ensure_ascii=False).replace('<', '\\u003c') + m[3]
    return LD.sub(ld_repl, source)
