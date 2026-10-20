#!/usr/bin/env python3
"""Сборка сайта «Венера, ногтевая студия».

Единственный источник цен и контактов: src/data.json. Описания услуг: src/info.json.
Запуск из корня репозитория:  python3 src/build.py          — собрать страницы в корень
                              python3 src/build.py --check  — проверить, что собранные файлы актуальны
"""
import html, json, sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
D = json.loads((SRC / 'data.json').read_text(encoding='utf-8'))
INFO = json.loads((SRC / 'info.json').read_text(encoding='utf-8'))
B = D['business']
SVC = D['services']
PROFILES = D.get('booking_profiles', [])
BOOK_ROUTE = 'index.html#specialists'
E = html.escape


def rub(n):
    return 'по запросу' if n is None else f"{n:,}".replace(',', ' ') + ' ₽'


def dur(m):
    if not m:
        return ''
    h, mm = divmod(m, 60)
    if h and mm:
        return f'{h} ч {mm} мин'
    return f'{h} ч' if h else f'{mm} мин'


def tg(text):
    return f"https://t.me/{B['telegram']}?text={quote(text)}"


def svc(i):
    return next(s for s in SVC if s['id'] == i)


ADDR = f"{B['district']}, {B['street']}"
URL = B['site_url'].rstrip('/')

ICON = {
    'tg': '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.4 4.2 2.9 11.3c-1.3.5-1.3 1.2-.2 1.6l4.7 1.5 1.8 5.6c.2.6.4.8.9.8.4 0 .6-.2.9-.5l2.3-2.2 4.8 3.5c.9.5 1.5.2 1.7-.8l3.1-14.7c.3-1.3-.5-1.9-1.5-1.4ZM9.3 14.2l8.9-5.6c.4-.3.8-.1.5.2l-7.5 6.8-.3 3.2-1.6-4.6Z"/></svg>',
    'phone': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" aria-hidden="true"><path d="M5 3h4l2 5-2.5 1.5a11 11 0 0 0 6 6L16 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 5a2 2 0 0 1 2-2Z"/></svg>',
    'menu': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    'hand': '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M11 28c-3-2-5-6-5-10v-5a2 2 0 0 1 4 0v3V7a2 2 0 0 1 4 0v8V5a2 2 0 0 1 4 0v10V7a2 2 0 0 1 4 0v12c0 5-3 9-7 9h-4Z"/><path d="M12.5 5.2h3"/></svg>',
    'ext': '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M12 30V13c0-5 1.6-9 4-11 2.4 2 4 6 4 11v17"/><path d="M12 19h8"/></svg>',
    'foot': '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M10 13c-1 5 1 9 2 13 1 3 3 4 5 4s3.5-2 3.6-4.5c.2-3 2-6 2.6-10 .5-3-1-5-4-5.4-3-.3-8.4-.4-9.2 2.9Z"/><circle cx="11" cy="6" r="2"/><circle cx="15.5" cy="4.5" r="1.6"/><circle cx="19.5" cy="5.2" r="1.4"/><circle cx="23" cy="7" r="1.2"/></svg>',
    'podo': '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M16 4 6 8v8c0 6 4.3 10 10 12 5.7-2 10-6 10-12V8L16 4Z"/><path d="M12 16h8M16 12v8"/></svg>',
    'men': '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="13" cy="19" r="8"/><path d="M19 13 27 5M21 5h6v6"/></svg>',
    'gift': '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="5" y="12" width="22" height="16" rx="2"/><path d="M4 8h24v4H4zM16 8v20M16 8c-2-4-7-5-7-2s5 2 7 2Zm0 0c2-4 7-5 7-2s-5 2-7 2Z"/></svg>',
}

# ---------------------------------------------------------------- hand SVG
SHAPES = {'oval': 9, 'almond': 17, 'square': 6}
FINGERS = [  # x, y, angle, length, width   (thumb first)
    (74, 246, -54, 104, 34), (112, 108, -9, 150, 31), (160, 88, -2, 166, 32),
    (208, 104, 5, 154, 31), (250, 146, 13, 118, 28)]


def nail_d(shape, w):
    e = SHAPES[shape]
    nw = w - 8
    L = 34 if w > 30 else 31
    x0, y0 = 4, 6 - e
    if shape == 'square':
        top = f'L{x0} {y0+4} Q{x0} {y0} {x0+4} {y0} L{x0+nw-4} {y0} Q{x0+nw} {y0} {x0+nw} {y0+4}'
    elif shape == 'oval':
        top = f'L{x0} {y0+nw/2:.1f} A{nw/2:.1f} {nw/2:.1f} 0 0 1 {x0+nw} {y0+nw/2:.1f}'
    else:
        top = (f'L{x0} {y0+nw*.95:.1f} C{x0} {y0+nw*.3:.1f} {x0+nw*.32:.1f} {y0+1} {x0+nw/2:.1f} {y0-3} '
               f'C{x0+nw*.68:.1f} {y0+1} {x0+nw} {y0+nw*.3:.1f} {x0+nw} {y0+nw*.95:.1f}')
    return f'M{x0} {L} {top} L{x0+nw} {L} Q{x0+nw/2:.1f} {L+7} {x0} {L} Z'


def hand_svg(shape='almond', interactive=False, uid='h'):
    g = []
    for i, (x, y, a, ln, w) in enumerate(FINGERS):
        d = nail_d(shape, w)
        g.append(
            f'<g transform="translate({x} {y}) rotate({a})">'
            f'<rect width="{w}" height="{ln}" rx="{w/2}" fill="url(#{uid}skin)"/>'
            f'<path d="M6 {ln*.42:.0f}q{w/2-6} 5 {w-12} 0M7 {ln*.62:.0f}q{w/2-7} 4 {w-14} 0" stroke="#C99482" stroke-opacity=".35" stroke-width="1.6" fill="none" stroke-linecap="round"/>'
            f'<clipPath id="{uid}c{i}"><path class="nail-clip" d="{d}"/></clipPath>'
            f'<path class="nail" d="{d}" fill="url(#{uid}lac)"/>'
            f'<g clip-path="url(#{uid}c{i})"><rect class="tip" x="0" y="-30" width="{w}" height="{30+SHAPES[shape]-2}" fill="#FFFDFB" opacity="0"/>'
            f'<rect class="glit" x="0" y="-30" width="{w}" height="80" fill="url(#{uid}gl)" opacity="0"/>'
            f'<path d="M{w*.32:.1f} {2-SHAPES[shape]+8} q-2 10 0 18" stroke="#fff" stroke-opacity=".7" stroke-width="3.2" stroke-linecap="round" fill="none"/></g>'
            f'</g>')
    return (
        f'<svg viewBox="0 0 340 400" role="img" aria-label="Схема руки с покрытием" {"id=tryonSvg" if interactive else ""}>'
        f'<defs><linearGradient id="{uid}skin" x1="0" x2="1"><stop offset="0" stop-color="#EBC1AD"/><stop offset=".5" stop-color="#F6D9CA"/><stop offset="1" stop-color="#E4B39E"/></linearGradient>'
        f'<linearGradient id="{uid}lac" x1="0" y1="0" x2=".4" y2="1"><stop class="s1" offset="0" stop-color="#D21E50"/><stop class="s2" offset="1" stop-color="#A3123A"/></linearGradient>'
        f'<pattern id="{uid}gl" width="7" height="7" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#fff"/><circle cx="5.5" cy="5" r=".7" fill="#FFE3EC"/></pattern>'
        f'<linearGradient id="{uid}fade" x1="0" y1="0" x2="0" y2="1"><stop offset=".72" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<mask id="{uid}m"><rect width="340" height="400" fill="url(#{uid}fade)"/></mask></defs>'
        f'<g mask="url(#{uid}m)">{"".join(g[1:])}'
        f'<path d="M84 400C76 350 66 304 80 268 90 244 104 232 118 228 156 220 228 220 270 232 286 262 292 322 280 400Z" fill="url(#{uid}skin)"/>'
        f'<path d="M126 238q14-8 30 0M174 232q16-8 32 0M220 238q14-6 28 2" stroke="#C99482" stroke-opacity=".3" stroke-width="1.8" fill="none" stroke-linecap="round"/>'
        f'{g[0]}</g></svg>')


# ---------------------------------------------------------------- layout
NAV = [('index.html#services', 'Услуги'), ('ceny.html', 'Цены'), ('podolog-novye-vatutinki.html', 'Подология'),
       ('muzhskoj-manikyur.html', 'Мужской'), ('podarochnyy-sertifikat.html', 'Сертификаты'), ('kontakty.html', 'Контакты')]


def head(title, desc, path, ld=None):
    canon = f'<link rel="canonical" href="{URL}/{"" if path == "index.html" else path}">' if URL else \
        '<!-- canonical: появится автоматически, когда в src/data.json будет заполнен business.site_url -->'
    ldj = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>' if ld else ''
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
{canon}
<meta name="geo.region" content="RU-MOW"><meta name="geo.placename" content="Новые Ватутинки, Москва">
<meta property="og:type" content="website"><meta property="og:locale" content="ru_RU">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}">
<meta name="theme-color" content="#26112B">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%2326112B'/%3E%3Cpath d='M11 26V12c0-4 2-7 5-8 3 1 5 4 5 8v14z' fill='%23D21E50'/%3E%3C/svg%3E">
<link rel="preload" href="assets/fonts/tenor-sans-cyrillic-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="assets/fonts/golos-text-cyrillic-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="assets/site.css">
<script src="assets/site.js" defer></script>
{ldj}
</head>
<body>
<a class="skip" href="#main">К содержанию</a>
<header class="top"><div class="wrap">
<a class="brand" href="index.html" aria-label="Венера, ногтевая студия — на главную"><b>Венера</b><small>ногтевая студия</small></a>
<nav class="nav" aria-label="Разделы">{"".join(f'<a href="{h}">{t}</a>' for h, t in NAV)}</nav>
<a class="icon-btn call" href="tel:{B['phone_href']}" aria-label="Позвонить {B['phone']}">{ICON['phone']}</a>
<a class="btn" href="{BOOK_ROUTE}">Записаться</a>
<button class="icon-btn menu-btn" type="button" aria-expanded="false" aria-controls="menu" aria-label="Меню">{ICON['menu']}</button>
</div></header>
<div class="menu-sheet" id="menu" hidden>
{"".join(f'<a href="{h}">{t}</a>' for h, t in NAV)}<a href="tel:{B['phone_href']}">{B['phone']}</a>
<div class="actions"><a class="btn" href="{BOOK_ROUTE}">Записаться онлайн</a><a class="btn btn-ghost" href="{tg('Здравствуйте! Хочу записаться.')}" target="_blank" rel="noopener">{ICON['tg']}Написать в Telegram</a></div>
</div>
<main id="main">
'''


def foot():
    lg = B['legal']
    legal = ''
    if lg['ip_name'] and lg['ogrnip']:
        legal = f"<p>ИП {E(lg['ip_name'])}, ОГРНИП {E(lg['ogrnip'])}{', ИНН ' + E(lg['inn']) if lg['inn'] else ''}</p>"
    cfg = {'book': B['book_url'], 'tg': B['telegram'], 'metrika': B.get('metrika_id', ''), 'addr': ADDR,
           'services': SVC, 'extras': D['extras'], 'cats': D['categories']}
    return f'''</main>
<footer class="foot-site"><div class="wrap">
<div class="foot-grid">
<div><a class="brand" href="index.html"><b>Венера</b><small>ногтевая студия</small></a>
<p>Москва, {E(ADDR)}, {B['postal']}<br>5 минут пешком от ТЦ «Лайнер»</p>
<p><a href="tel:{B['phone_href']}">{B['phone']}</a><br>{E(B['hours'] or B['hours_note'])}</p></div>
<ul class="foot-links"><li><a href="manikyur.html">Маникюр</a></li><li><a href="pedikyur.html">Педикюр</a></li><li><a href="narashchivanie-nogtey.html">Наращивание</a></li><li><a href="podolog-novye-vatutinki.html">Подолог</a></li><li><a href="vrosshij-nogot.html">Вросший ноготь</a></li><li><a href="muzhskoj-manikyur.html">Мужской маникюр</a></li></ul>
<ul class="foot-links"><li><a href="{BOOK_ROUTE}">Онлайн-запись</a></li><li><a href="https://t.me/{B['telegram']}" target="_blank" rel="noopener">Telegram</a></li><li><a href="{B['yandex_org']}" target="_blank" rel="noopener">Яндекс Карты</a></li><li><a href="ceny.html">Все цены</a></li><li><a href="podarochnyy-sertifikat.html">Сертификаты</a></li><li><a href="kontakty.html">Контакты</a></li></ul>
</div>
<div class="foot-legal">{legal}<p><a href="politika.html">Политика обработки персональных данных</a> · <a href="soglasie.html">Согласие на обработку данных</a></p></div>
</div></footer>

<dialog class="sheet" id="sheet" aria-labelledby="sheetTitle"><div class="sheet-in"><button class="sheet-close" type="button" aria-label="Закрыть">✕</button><div id="sheetBody"></div></div></dialog>
<div class="consent" id="consent" hidden></div>
<div class="toast" id="toast" role="status" aria-live="polite"></div>
<script type="application/json" id="site-data">{json.dumps(cfg, ensure_ascii=False)}</script>
<script type="application/json" id="info-data">{json.dumps(INFO, ensure_ascii=False)}</script>
</body>
</html>
'''


def page_hero(crumb, h1, lead, tgtext, extra=''):
    return f'''<section class="page-hero"><div class="wrap">
<nav class="crumbs" aria-label="Навигация"><a href="index.html">Главная</a> / {E(crumb)}</nav>
<h1>{E(h1)}</h1><p class="lead">{lead}</p>{extra}
<div class="actions" data-hero-end><a class="btn" href="{BOOK_ROUTE}">Записаться онлайн</a><a class="btn btn-ghost" href="{tg(tgtext)}" target="_blank" rel="noopener">{ICON['tg']}Написать в Telegram</a></div>
</div></section>'''


def price_table(ids, title=None):
    rows = []
    if title:
        rows.append(f'<tr class="cat"><td colspan="2">{E(title)}</td></tr>')
    for i in ids:
        s = svc(i)
        sub = ' · '.join(x for x in [dur(s['min']), s['note']] if x)
        info = f' <button class="link-btn" type="button" data-info="{E(s["name"])}">что это?</button>' if s['name'] in INFO else ''
        rows.append(f'<tr><td>{E(s["name"])}{info}{f"<small>{E(sub)}</small>" if sub else ""}</td><td>{rub(s["price"])}</td></tr>')
    return '<table class="prices">' + ''.join(rows) + '</table>'


def faq_html(items):
    return '<div class="faq">' + ''.join(f'<details><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q, a in items) + '</div>'


def faq_ld(items):
    return {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}


def salon_ld():
    ld = {"@type": "NailSalon", "@id": (URL + '/#salon') if URL else '#salon', "name": B['name_full'], "alternateName": B['alternate_name'],
          "telephone": B['phone'], "priceRange": "300–4000 ₽", "currenciesAccepted": "RUB",
          "address": {"@type": "PostalAddress", "streetAddress": B['street'], "addressLocality": "Москва",
                      "addressRegion": "Новые Ватутинки, ТиНАО", "postalCode": B['postal'], "addressCountry": "RU"},
          "areaServed": ["Новые Ватутинки", "Десёновское", "Ватутинки", "ТиНАО"],
          "sameAs": [B['yandex_org'], f"https://t.me/{B['telegram']}", B['book_url']],
          "potentialAction": {"@type": "ReserveAction", "target": B['book_url']},
          "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Услуги и цены", "itemListElement": [
              {"@type": "Offer", "itemOffered": {"@type": "Service", "name": s['name']}, "price": str(s['price']), "priceCurrency": "RUB"}
              for s in SVC if s['price'] is not None]}}
    if URL:
        ld['url'] = URL + '/'
    return ld


def service_ld(name, ids, crumb, path, faq):
    offers = [{"@type": "Offer", "name": svc(i)['name'], "price": str(svc(i)['price']), "priceCurrency": "RUB"} for i in ids if svc(i)['price'] is not None]
    s = {"@type": "Service", "name": name, "areaServed": "Новые Ватутинки, ТиНАО",
         "provider": {"@type": "NailSalon", "name": B['name_full'], "telephone": B['phone'],
                      "address": {"@type": "PostalAddress", "streetAddress": B['street'], "addressLocality": "Москва", "postalCode": B['postal'], "addressCountry": "RU"}}}
    if offers:
        s['offers'] = offers
    bc = {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Главная", **({"item": URL + '/'} if URL else {})},
        {"@type": "ListItem", "position": 2, "name": crumb, **({"item": f"{URL}/{path}"} if URL else {})}]}
    g = [s, bc]
    if faq:
        g.append(faq_ld(faq))
    return {"@context": "https://schema.org", "@graph": g}


def booking_profiles_block():
    cards = []
    for n, profile in enumerate(PROFILES, 1):
        if not profile.get('active', True):
            continue
        url = str(profile.get('url', ''))
        if not url.startswith('https://bumpix.net/'):
            continue
        label = E(profile.get('label', 'Профиль записи ' + str(n)))
        extra = 'Имя и специализация уточняются' if not profile.get('confirmed') else 'Услуги и свободное время — в Bumpix'
        cards.append(f'<div class="specialist-card"><span class="specialist-index">0{n} / ОНЛАЙН-ЗАПИСЬ</span>'
                     f'<h3>{label}</h3><p>{extra}</p>'
                     f'<a class="btn btn-sm" href="{E(url)}" target="_blank" rel="noopener noreferrer">Посмотреть время ↗</a></div>')
    return ('<div class="section-head"><span class="eyebrow">Мастера и запись</span>'
            '<h2>Выберите удобное время</h2>'
            '<p class="muted">Каждый мастер ведёт своё расписание. Актуальные услуги, цены и свободные окна проверяйте в Bumpix.</p></div>'
            '<div class="specialist-grid">' + ''.join(cards) + '</div>'
            '<p class="note specialist-note">Состав команды может изменяться. Мы обновляем ссылки на действующие профили.</p>')


def section(inner, cls='', id_=''):
    return f'<section class="section {cls}"{f" id={chr(34)}{id_}{chr(34)}" if id_ else ""}><div class="wrap">{inner}</div></section>'


ROUTE_MAP = (SRC / 'partials' / 'route-map.svg').read_text(encoding='utf-8')
FOOT_SVG = (SRC / 'partials' / 'foot.svg').read_text(encoding='utf-8')
LINER_URL = 'https://yandex.ru/maps/?rtext=' + quote('Москва, Нововатутинский проспект, 6') + '~' + quote('Москва, ' + B['street']) + '&rtt=pd'
ME_URL = 'https://yandex.ru/maps/?rtext=~' + quote('Москва, ' + B['street']) + '&rtt=auto'


def visit_block(h='h2'):
    return f'''<div class="section-head"><span class="eyebrow">Как добраться</span><{h}>6-я Нововатутинская, 5</{h}><p class="muted">Выберите, откуда идёте.</p></div>
<div class="route-tabs" role="tablist" aria-label="Откуда идёте"><button class="route-tab" role="tab" aria-selected="true" data-route="liner"><i></i>От ТЦ «Лайнер»</button><button class="route-tab metro" role="tab" aria-selected="false" data-route="metro"><i></i>От метро «Ватутинки»</button></div>
<div class="visit">
<div class="map-box" id="mapBox" data-route="liner">{ROUTE_MAP.replace('<svg ', '<svg role="img" aria-label="Схема: от ТЦ «Лайнер» 5 минут пешком мимо «Дикси»; станция «Ватутинки» строится у Калужского шоссе" ', 1)}
<small class="map-note">Схема без масштаба</small>
<div class="map-live" id="mapLive" hidden><iframe title="Студия на Яндекс Картах" loading="lazy" data-src="https://yandex.ru/map-widget/v1/?oid={B['yandex_oid']}&amp;ol=biz&amp;z=16"></iframe><button class="map-close" type="button" id="mapClose">Вернуть схему</button></div></div>
<div>
<div class="route-info" data-route-info="liner"><div class="big">5 минут пешком</div><p>От ТЦ «Лайнер» (Нововатутинский проспект, 6) идите вдоль дороги в сторону Калужского шоссе, мимо «Дикси». Около 400 метров.</p><a class="btn" href="{LINER_URL}" target="_blank" rel="noopener">Маршрут от «Лайнера»</a></div>
<div class="route-info" data-route-info="metro" hidden><div class="big">Станция строится</div><p>Станция «Ватутинки» Троицкой линии появится у Калужского шоссе и проспекта Славского. Когда её откроют, здесь будет пеший маршрут.</p><a class="btn btn-line" href="{ME_URL}" target="_blank" rel="noopener">Маршрут от меня</a></div>
<dl class="facts"><dt>Адрес</dt><dd>{E(ADDR)}</dd><dt>Телефон</dt><dd><a href="tel:{B['phone_href']}">{B['phone']}</a></dd><dt>Время</dt><dd>{E(B['hours'] or B['hours_note'])}</dd></dl>
<p style="margin-top:14px"><button class="link-btn" type="button" id="mapBtn">Показать карту здесь</button> · <a href="{B['yandex_org']}" target="_blank" rel="noopener">Открыть в Яндекс Картах</a></p>
</div></div>'''


def related(cur):
    links = [('manikyur.html', 'Маникюр'), ('pedikyur.html', 'Педикюр'), ('narashchivanie-nogtey.html', 'Наращивание'),
             ('podolog-novye-vatutinki.html', 'Подолог'), ('vrosshij-nogot.html', 'Вросший ноготь'), ('muzhskoj-manikyur.html', 'Мужской маникюр'),
             ('podarochnyy-sertifikat.html', 'Сертификат'), ('ceny.html', 'Все цены')]
    return '<div class="section-head"><h2>Ещё услуги</h2></div><div class="chips">' + ''.join(
        f'<a class="chip" href="{h}" style="text-decoration:none;color:inherit">{t}</a>' for h, t in links if h != cur) + '</div>'


def tips_block(title, tips, days, what):
    return (f'<div class="grid-2"><div><span class="eyebrow">После процедуры</span><h2>{E(title)}</h2><ul class="tips">' +
            ''.join(f'<li>{E(t)}</li>' for t in tips) +
            '</ul></div><div class="route-info"><div class="big">Когда прийти снова?</div>'
            '<p class="muted">Срок следующего посещения подскажет мастер. Не создаём выдуманную запись в календаре — выберите доступное время в системе онлайн-записи.</p>'
            f'<a class="btn" href="{BOOK_ROUTE}">Выбрать мастера и время</a></div></div>')


# ---------------------------------------------------------------- pages
PAGES = {}

# ====== index
HOME_FAQ = [
    ('Где сделать маникюр в Новых Ватутинках?', 'На 6-й Нововатутинской улице, дом 5, в 5 минутах пешком от ТЦ «Лайнер». Запись онлайн или в Telegram.'),
    ('Сколько стоит маникюр с покрытием?', 'Маникюр с гель-лаком стоит 2 500 ₽ и занимает около 1,5 часа: снятие старого покрытия, маникюр, укрепление и покрытие.'),
    ('Что делать, если ноготь врастает в кожу?', 'При боли, воспалении или подозрении на вросший ноготь сначала обратитесь к врачу. Возможность косметического ухода уточняйте отдельно.'),
    ('Делаете ли мужской маникюр?', 'Да, мужской маникюр и педикюр без лака и блеска. Стоимость и свободное время уточняйте в Telegram.'),
    ('Как записаться?', 'Нажмите «Записаться онлайн» и выберите время или напишите в Telegram: сообщение с выбранной услугой подставится само.'),
]
cards = [
    ('manikyur.html', 'hand', 'Маникюр', 'С гель-лаком, без покрытия, френч и дизайн', 'от ' + rub(1200)),
    ('narashchivanie-nogtey.html', 'ext', 'Наращивание', 'Наращивание и коррекция гелем или полигелем', 'от ' + rub(3000)),
    ('pedikyur.html', 'foot', 'Педикюр', 'Смарт-педикюр и педикюр с покрытием', 'от ' + rub(2800)),
    ('podolog-novye-vatutinki.html', 'podo', 'Подология', 'Вросший ноготь, мозоли, огрубевшая кожа', 'консультация ' + rub(700)),
    ('muzhskoj-manikyur.html', 'men', 'Мужской маникюр', 'Без лака и блеска, руки просто ухоженные', 'цена по запросу'),
    ('podarochnyy-sertifikat.html', 'gift', 'Сертификат', 'Подарок на услугу или сумму', 'открытка онлайн'),
]
cards_html = '<div class="cards">' + ''.join(
    f'<a class="card" href="{h}"><span class="card-ico">{ICON[ic]}</span><span><h3>{t}{"<span class=new>NEW</span>" if ic == "men" else ""}</h3><p>{d}</p><b>{p}</b></span></a>'
    for h, ic, t, d, p in cards) + '</div>'

SHADES = [('Вишня', '#D21E50', '#A3123A', ''), ('Нюд', '#F2D7CE', '#DDB3A6', ''), ('Слива', '#8A4380', '#5B2A55', ''),
          ('Молочный', '#FFFFFF', '#EDE3EA', ''), ('Какао', '#A0786B', '#7C5649', ''), ('Чёрный', '#3B2A3F', '#120A14', ''),
          ('Френч', '#F6E1E3', '#EFCFD4', 'french'), ('Блёстки', '#D9A9B8', '#B47A8F', 'glitter')]
def _swbg(a, b, f):
    if f == 'french':
        return 'linear-gradient(180deg,#fff 0 34%,#F6E1E3 35%)'
    if f == 'glitter':
        return f'radial-gradient(circle at 30% 30%,#fff 0 1.3px,transparent 2px) 0 0/7px 7px,linear-gradient(160deg,{a},{b})'
    return f'linear-gradient(160deg,{a},{b})'


sw = ''.join(f'<button class="sw" type="button" style="--c:{_swbg(a, b, f)}" data-name="{n}" data-c1="{a}" data-c2="{b}" data-finish="{f}" aria-pressed="{"true" if n == "Вишня" else "false"}" aria-label="{n}"></button>'
             for n, a, b, f in SHADES)

PODO_POINTS = [('ingrown', 36.5, 15.5, 'Вросший ноготь'), ('toes', 64, 16, 'Пальчики'), ('callus', 80, 44, 'Мозоль'), ('feet', 57, 84, 'Стопы')]

index = head('Маникюр и педикюр в Новых Ватутинках, подолог в ТиНАО | Венера, ногтевая студия',
             'Маникюр с гель-лаком 2 500 ₽, педикюр, наращивание и подолог в Новых Ватутинках (ТиНАО). 5 минут от ТЦ «Лайнер». Цены, подбор оттенка и онлайн-запись.',
             'index.html', {"@context": "https://schema.org", "@graph": [salon_ld(), faq_ld(HOME_FAQ)]})
index += f'''<section class="hero home-hero"><div class="wrap hero-grid">
<div class="hero-copy">
<span class="eyebrow hero-location"><span class="location-dot" aria-hidden="true"></span> НОВЫЕ ВАТУТИНКИ · МОСКВА</span>
<h1>Маникюр в Новых Ватутинках.<br><em>Стиль — в деталях.</em></h1>
<p class="lead">Маникюр, педикюр и уход за ногтями на 6-й Нововатутинской, 5. Понятные цены, спокойная атмосфера и удобная запись.</p>
<ul class="hero-facts"><li>Маникюр с гель-лаком — {rub(svc('mani-gel')['price'])}</li><li>5 минут от ТЦ «Лайнер»</li></ul>
<div class="hero-actions" data-hero-end>
<a class="btn hero-primary" href="#calc">Выбрать услугу <span aria-hidden="true">↗</span></a>
<a class="hero-textlink" href="{BOOK_ROUTE}">Сразу к свободному времени <span aria-hidden="true">→</span></a>
</div>
</div>
<div class="hero-editorial" aria-label="Фирменная графическая композиция студии">
<div class="hero-editorial-inner">
<div class="hero-editorial-top"><span>V / N</span><span>VENЕRA<br>NAIL STUDIO</span></div>
<div class="hero-editorial-main"><span>ЦВЕТ. ФОРМА. УХОД.</span><p>Ваши<br><i>оттенки.</i></p></div>
<div class="hero-editorial-bottom"><div class="hero-swatch-row" aria-hidden="true"><i style="--sw:#A01B46"></i><i style="--sw:#D9B5A4"></i><i style="--sw:#EAE0D8"></i><i style="--sw:#6C415C"></i></div><span>01 / ЭСТЕТИКА</span></div>
</div>
</div>
</div></section>
<div class="quick-prices" aria-label="Популярные услуги"><div class="wrap quick-prices-inner">
<a href="manikyur.html"><span>Маникюр без покрытия</span><strong>{rub(svc('mani-plain')['price'])}</strong></a>
<a href="manikyur.html"><span>С гель-лаком</span><strong>{rub(svc('mani-gel')['price'])}</strong></a>
<a href="pedikyur.html"><span>Педикюр</span><strong>от {rub(svc('smart')['price'])}</strong></a>
</div></div>
'''
index += section(f'<div class="section-head"><span class="eyebrow">Услуги</span><h2>Что можно сделать</h2></div>{cards_html}', 'alt', 'services')
index += section(booking_profiles_block(), '', 'specialists')
index += section(f'''<div class="section-head"><span class="eyebrow">Цены</span><h2>Сколько стоит и сколько займёт</h2><p class="muted">Выберите услугу: сумма и время посчитаются сразу. Значок «i» расскажет, что это за процедура.</p></div>
<div class="calc" id="calc">
<div><div class="tabs" role="tablist" aria-label="Категория">{"".join(f'<button class="tab" role="tab" type="button" data-tab="{c["id"]}" aria-selected="{"true" if c["id"] == "mani" else "false"}">{c["title"]}</button>' for c in D["categories"])}</div>
<div class="svc-list" id="svcList" role="group" aria-label="Выбор услуг"></div>
<div class="extras" id="extras" role="group" aria-label="Дополнительно">{"".join(f'<button class="extra" type="button" data-extra="{x["id"]}" aria-pressed="false">+ {x["name"]} <small>{"от " if x["from"] else ""}{rub(x["price"])}</small></button>' for x in D["extras"])}</div>
<noscript>{price_table([s["id"] for s in SVC])}</noscript></div>
<aside class="summary" aria-live="polite"><div class="note" style="color:var(--night-muted)">Ориентировочно</div><div class="total" id="total">—</div><div class="time" id="time"></div><ul id="lines"></ul>
<a class="btn" href="{BOOK_ROUTE}">Выбрать время онлайн</a>
<div class="label">или заявка в Telegram: когда удобно?</div>
<div class="chips" id="whenDay">{"".join(f'<button class="chip" type="button" aria-pressed="false">{d}</button>' for d in ["Сегодня", "Завтра", "В будни", "В выходные"])}</div>
<div class="chips" id="whenTime" style="margin-top:8px">{"".join(f'<button class="chip" type="button" aria-pressed="false">{d}</button>' for d in ["Утром", "Днём", "Вечером"])}</div>
<a class="btn btn-ghost" id="sendReq" href="https://t.me/{B['telegram']}" target="_blank" rel="noopener">{ICON['tg']}Отправить заявку</a>
<p class="note" style="margin-top:10px">Сообщение с услугой и временем подставится само.</p></aside>
</div>''', '', 'calc-section')
index += section(f'''<div class="tryon">
<div class="hand-stage" hidden aria-hidden="true">{hand_svg('almond', True, 'th')}</div>
<div><span class="eyebrow">Подбор оттенка</span><h2>Выберите форму и цвет</h2><p class="muted">Отметьте форму и оттенок — пожелания будут добавлены к сообщению мастеру. Это не примерка по фотографии.</p>
<div class="ctl"><div class="ctl-label">Форма</div><div class="chips" role="group" aria-label="Форма">{"".join(f'<button class="chip" type="button" data-shape="{k}" aria-pressed="{"true" if k == "almond" else "false"}">{v}</button>' for k, v in [("oval", "Овал"), ("almond", "Миндаль"), ("square", "Квадрат")])}</div></div>
<div class="ctl"><div class="ctl-label">Оттенок</div><div class="swatches" role="group" aria-label="Оттенок">{sw}</div></div>
<div class="choice"><span>Ваш выбор: <b id="choice">миндаль, вишня</b></span><button class="link-btn" type="button" id="quizBtn">Подобрать за 3 вопроса</button></div>
<div class="actions" style="margin-top:14px"><a class="btn" id="sendChoice" href="https://t.me/{B['telegram']}" target="_blank" rel="noopener">{ICON['tg']}Отправить выбор мастеру</a></div>
</div></div>''', 'alt', 'tryon')
index += section(f'''<div class="podo">
<div class="foot-choices" id="foot"><span class="eyebrow">Выберите вопрос</span><p class="muted">Косметический уход за стопами и ногтями. При боли или воспалении обратитесь к врачу.</p>{"".join(f'<button class="hot" type="button" data-podo="{k}" aria-pressed="{"true" if k == "ingrown" else "false"}">{lbl}<span aria-hidden="true">→</span></button>' for k, x, y, lbl in PODO_POINTS)}</div>
<div><span class="eyebrow">Уход за стопами</span><h2>Вопросы по ногтям и коже стоп</h2><p class="muted">Выберите интересующую тему. Информация не заменяет врачебный осмотр.</p>
<div class="podo-card"><h3 id="podoTitle">Обработка вросшего ногтя</h3><p id="podoText" class="muted"></p><div class="meta"><div><b id="podoPrice"></b><span>стоимость</span></div><div><b id="podoTime"></b><span>длительность</span></div></div>
<div class="actions"><a class="btn btn-sm" href="{BOOK_ROUTE}">Записаться</a><button class="btn btn-sm btn-soft" type="button" id="podoMore">Подробнее</button></div></div>
<div class="ctl-label" style="margin-top:20px">Что беспокоит?</div>
<div class="chips" id="footQuiz">{"".join(f'<button class="chip{" red" if k == "doctor" else ""}" type="button" data-f="{k}" aria-pressed="false">{t}</button>' for k, t in [("ingrown", "Ноготь врезается в кожу"), ("system", "Врастает снова и снова"), ("callus", "Мозоль, больно в обуви"), ("feet", "Сухие пятки, трещины"), ("toes", "Утолщённые ногти"), ("consult", "Не знаю, что это"), ("doctor", "Сильная боль, гной, отёк")])}</div>
<p class="ans" id="footAns" aria-live="polite"></p>
<p class="disclaimer">При боли, воспалении, выделениях и заболеваниях стоп необходима консультация врача. Перечень допустимых процедур и квалификацию мастера требуется подтвердить.</p>
<p><a href="podolog-novye-vatutinki.html">Всё о подологии и ценах</a></p></div>
</div>''', '', 'podo')
index += section(f'''<div class="men-grid">
<div><span class="eyebrow" style="color:var(--rose)">Для мужчин · NEW</span><h2>Ухоженные руки без лака и блеска</h2>
<p class="lead" style="color:var(--night-text)">Руки видят первыми: рукопожатие, переговоры, телефон в руке. Мужской маникюр не про красоту ногтей, а про аккуратность. Никто не заметит, что вы были у мастера, заметят только, что руки выглядят ухоженно.</p>
<div class="actions"><a class="btn" href="{tg('Здравствуйте! Хочу записаться на мужской маникюр. Есть время, когда в студии нет других гостей?')}" target="_blank" rel="noopener">{ICON['tg']}Спросить время</a><a class="btn btn-ghost" href="muzhskoj-manikyur.html">Подробнее</a></div></div>
<div class="fears">
<div class="fear"><b>«Можно без покрытия?»</b><p>Да. Цветное покрытие не является обязательной частью процедуры.</p></div>
<div class="fear"><b>«Будет блестеть»</b><p>Без цветного лака. Видно только ровные ногти и кожу без заусенцев.</p></div>
<div class="fear"><b>«Не знаю, что просить»</b><p>Ничего не нужно знать: мастер посмотрит руки и предложит сама.</p></div>
<div class="fear"><b>«Это не по-мужски»</b><p>Это гигиена, как стрижка у барбера. И женщины замечают ухоженные руки.</p></div>
</div></div>''', 'dark', 'men')
index += section(f'''<div class="section-head"><span class="eyebrow">Отзывы</span><h2>Отзывы о студии</h2><p class="muted">Посмотрите опубликованные отзывы и фотографии в карточке студии на Яндекс Картах.</p></div>
<div class="actions"><a class="btn btn-line" href="{B['yandex_reviews']}" target="_blank" rel="noopener">Открыть Яндекс Карты ↗</a><a class="btn btn-soft" href="{B['yandex_reviews']}" target="_blank" rel="noopener" data-goal="review">Оставить отзыв</a></div>''', 'alt', 'reviews')
index += section(visit_block(), '', 'visit')
index += section(f'''<div class="grid-2"><div><span class="eyebrow">Вопросы</span><h2>Маникюр и подолог рядом с домом в Новых Ватутинках</h2>
<p class="muted">Студия на 6-й Нововатутинской улице, в 5 минутах пешком от ТЦ «Лайнер». Удобно прийти из любой части Новых Ватутинок и Десёновского, приехать из Ватутинок и соседних районов ТиНАО.</p>
<p class="muted">Маникюр с гель-лаком, френч и дизайн, наращивание и коррекция, смарт-педикюр и педикюр с покрытием. Отдельное направление — подология: вросший ноготь, мозоли, огрубевшая кожа стоп. А ещё мужской маникюр и педикюр.</p></div>
{faq_html(HOME_FAQ)}</div>''', 'alt', 'faq')
index += foot()
PAGES['index.html'] = index


# ====== service pages
def service_page(path, crumb, title, desc, h1, lead, tgtext, ids, body, faq, tips=None, ldname=None):
    s = head(title, desc, path, service_ld(ldname or crumb, ids, crumb, path, faq))
    if path == 'muzhskoj-manikyur.html':
        s = s.replace('<body>', '<body class="men-page">', 1)
    s += page_hero(crumb, h1, lead, tgtext)
    s += section(f'<div class="grid-2"><div><span class="eyebrow">Цены</span><h2>Стоимость</h2>{price_table(ids)}<p class="note" style="margin-top:10px">Цены из онлайн-записи.{" Стоимость дизайна мастер подскажет на месте." if path in ("manikyur.html", "narashchivanie-nogtey.html") else ""}</p></div><div>{body[0]}</div></div>')
    for b in body[1:]:
        s += section(b, 'alt' if body.index(b) % 2 else '')
    if tips:
        s += section(tips_block(*tips), 'alt')
    if faq:
        s += section(f'<div class="section-head"><span class="eyebrow">Вопросы</span><h2>Частые вопросы</h2></div>{faq_html(faq)}')
    s += section(visit_block('h2'), 'alt')
    s += section(related(path))
    s += foot()
    PAGES[path] = s


MANI_TIPS = ('Чтобы покрытие держалось дольше', ['В первые сутки берегите покрытие от сауны и долгой горячей воды.', 'Уборку и мытьё посуды делайте в перчатках.', 'Каждый вечер капля масла для кутикулы.', 'Не используйте ногти как инструмент: не открывайте ими банки.', 'Если появился скол, не срывайте покрытие, напишите мастеру.'], 21, 'маникюр')

service_page('manikyur.html', 'Маникюр', 'Маникюр в Новых Ватутинках: гель-лак 2 500 ₽, френч | Венера, ногтевая студия',
             'Маникюр с гель-лаком 2 500 ₽, без покрытия 1 200 ₽, френч и дизайн в Новых Ватутинках. 5 минут от ТЦ «Лайнер», онлайн-запись.',
             'Маникюр в Новых Ватутинках', 'С покрытием гель-лаком, без покрытия, френч и дизайн. Около 1,5 часа на маникюр с покрытием.',
             'Здравствуйте! Хочу записаться на маникюр с покрытием.', ['mani-gel', 'mani-plain'],
             ['<span class="eyebrow">Как проходит</span><h2>Маникюр с покрытием</h2><ol class="steps"><li>Снятие старого покрытия.</li><li>Форма и длина ногтей.</li><li>Обработка кутикулы.</li><li>Подготовка и укрепление ногтя.</li><li>Покрытие гель-лаком под лампой.</li><li>Масло для кутикулы.</li></ol><p class="muted" style="margin-top:14px">Френч добавляется за 300 ₽, дизайн от 100 ₽. <button class="link-btn" type="button" data-info="Френч">Откуда взялся френч?</button></p><p><a href="index.html#tryon">Подобрать форму и оттенок</a></p>'],
             [('Сколько держится гель-лак?', 'Обычно 3–4 недели. Потом ноготь отрастает, и покрытие лучше обновить.'),
              ('Сколько длится маникюр с покрытием?', 'Около полутора часов вместе со снятием старого покрытия.'),
              ('Можно ли сделать френч?', 'Да, френч добавляется к маникюру с покрытием за 300 ₽.')], MANI_TIPS, 'Маникюр')

service_page('narashchivanie-nogtey.html', 'Наращивание', 'Наращивание ногтей в Новых Ватутинках 4 000 ₽, коррекция 3 000 ₽ | Венера, ногтевая студия',
             'Наращивание ногтей 4 000 ₽, коррекция гелем или полигелем 3 000 ₽ в Новых Ватутинках (ТиНАО). Онлайн-запись.',
             'Наращивание ногтей в Новых Ватутинках', 'Нужная длина и форма, даже если свои ногти короткие или ломкие. Коррекция раз в 3–4 недели.',
             'Здравствуйте! Хочу записаться на наращивание ногтей.', ['ext', 'corr-gel', 'corr-poly'],
             ['<span class="eyebrow">Что выбрать</span><h2>Наращивание или коррекция</h2><p class="muted">Наращивание — когда ногти делают впервые или после перерыва. Коррекция — плановое обновление: мастер убирает отросшую часть, восстанавливает форму и обновляет покрытие.</p><p><button class="link-btn" type="button" data-info="Коррекция полигелем">Чем полигель отличается от геля?</button></p>'],
             [('Как часто нужна коррекция?', 'Обычно раз в 3–4 недели, когда ноготь отрастает.'),
              ('Сколько длится наращивание?', 'Около полутора часов.')], None, 'Наращивание ногтей')

service_page('pedikyur.html', 'Педикюр', 'Педикюр в Новых Ватутинках: смарт-педикюр 2 800 ₽ | Венера, ногтевая студия',
             'Смарт-педикюр 2 800 ₽, педикюр с гель-лаком 3 300 ₽ в Новых Ватутинках (ТиНАО). 5 минут от ТЦ «Лайнер».',
             'Педикюр в Новых Ватутинках', 'Смарт-педикюр одноразовыми насадками, педикюр пальчиков и полный педикюр с покрытием.',
             'Здравствуйте! Хочу записаться на педикюр.', ['smart', 'pedi-toes', 'pedi-gel'],
             ['<span class="eyebrow">Что выбрать</span><h2>Три варианта</h2><p class="muted"><b>Смарт-педикюр</b> — обработка стоп одноразовыми абразивными насадками, без лезвий. <b>Педикюр пальчиков</b> — только пальцы и покрытие, когда со стопами всё в порядке. <b>Педикюр с гель-лаком</b> — комплекс: стопы, пальцы и покрытие.</p><p class="muted">Если беспокоят вросший ноготь или мозоли, посмотрите <a href="podolog-novye-vatutinki.html">подологию</a>.</p>'],
             [('Сколько держится покрытие на ногах?', 'Обычно дольше, чем на руках: 4–6 недель.'),
              ('Чем смарт-педикюр отличается от обычного?', 'Кожу обрабатывают одноразовыми абразивными насадками на аппарате, без лезвий и долгого распаривания.')],
             ('Уход после педикюра', ['Пару дней носите удобную, не тесную обувь.', 'Мажьте стопы кремом вечером, особенно пятки.', 'Подстригайте ногти на ногах прямо, не закругляя углы.'], 35, 'педикюр'), 'Педикюр')

service_page('podolog-novye-vatutinki.html', 'Подолог', 'Подолог в Новых Ватутинках: вросший ноготь, мозоли, стопы | Венера, ногтевая студия',
             'Подологический педикюр 3 300 ₽, вросший ноготь от 1 000 ₽, консультация 700 ₽ в Новых Ватутинках (ТиНАО). Характер процедур и необходимые разрешения нужно уточнять у специалиста.',
             'Подолог в Новых Ватутинках', 'Вросший ноготь, мозоли, трещины на пятках, утолщённые ногти. Не нужно ехать в центр: всё рядом, на 6-й Нововатутинской.',
             'Здравствуйте! Хочу на консультацию подолога. Беспокоит: ', ['consult', 'podo-pedi', 'ingrown', 'system', 'feet', 'toes', 'callus'],
             ['<span class="eyebrow">С чем приходят</span><h2>Что делает подолог</h2><ul class="tips"><li>Вросший ноготь: мастер аккуратно освобождает край. <a href="vrosshij-nogot.html">Подробнее</a></li><li>Ноготь врастает снова: коррекционная система помогает ему расти ровно.</li><li>Мозоли и натоптыши: убираем огрубевшую кожу и снимаем давление.</li><li>Сухие пятки и трещины: обработка стоп.</li></ul><p class="disclaimer">Характер процедур и необходимые разрешения нужно уточнять у специалиста. Сильная боль, гной, отёк, растущее покраснение или сахарный диабет — повод сначала обратиться к врачу.</p>',
              '<div class="grid-2"><div><span class="eyebrow">Отличие</span><h2>Подологический педикюр и обычный</h2><p class="muted">Обычный педикюр — про аккуратный вид и покрытие. Подологический — про проблемные зоны стоп и ногтей: мастер смотрит, почему появилась мозоль или врастает ноготь, и работает с этим. Покрытие по желанию.</p></div><div><span class="eyebrow">Не знаете, что нужно</span><h2>Начните с консультации</h2><p class="muted">За 700 ₽ мастер осмотрит стопы, подскажет процедуру и её стоимость.</p></div></div>'],
             [('Есть ли подолог в Новых Ватутинках?', 'Да, на 6-й Нововатутинской улице, 5: подологический педикюр, обработка вросшего ногтя, мозолей и стоп.'),
              ('Сколько стоит консультация подолога?', '700 ₽, около 30 минут.'),
              ('Можно ли с диабетом?', 'При диабете сначала посоветуйтесь с врачом и обязательно скажите о нём мастеру при записи.'),
              ('Когда нужно обратиться к врачу?', 'При боли, воспалении, выделениях или подозрении на заболевание ногтей или кожи необходим врач. Характер допустимого косметического ухода уточняется отдельно.')],
             ('Уход после подологии', ['Выполняйте рекомендации мастера по уходу дома.', 'Не срезайте уголки ногтя, если он врастал.', 'При покраснении, отёке или сильной боли обратитесь к врачу.', 'На повторный визит приходите в срок, который назвал мастер.'], 28, 'подологию'), 'Подологический педикюр')

service_page('vrosshij-nogot.html', 'Вросший ноготь', 'Вросший ноготь в Новых Ватутинках: обработка от 1 000 ₽ | Венера, ногтевая студия',
             'Эстетическая обработка вросшего ногтя от 1 000 ₽, коррекционная система 3 000 ₽ в Новых Ватутинках. Когда к подологу, а когда к врачу.',
             'Вросший ноготь: что делать', 'Край ногтя врезался в кожу и болит в обуви? Разберёмся, когда поможет подолог, а когда нужно к врачу.',
             'Здравствуйте! Кажется, врастает ноготь на ноге. Можно записаться на обработку?', ['ingrown', 'system', 'consult'],
             ['<span class="eyebrow">Признаки</span><h2>Как понять, что ноготь врастает</h2><ul class="tips"><li>Край ногтя, чаще на большом пальце, уходит в кожу.</li><li>Кожа рядом краснеет и болит при нажатии или в тесной обуви.</li><li>Боль усиливается, если срезать уголок ещё глубже.</li></ul><p class="disclaimer">Сразу к врачу, если есть гной, сильный отёк, температура, покраснение расползается или у вас диабет. Это воспаление, им занимается хирург.</p>',
              '<div class="grid-2"><div><span class="eyebrow">Процедура</span><h2>Что делает мастер</h2><ol class="steps"><li>Осматривает палец и спрашивает, давно ли беспокоит.</li><li>Аккуратно освобождает край ногтя.</li><li>Обрабатывает кожу вокруг.</li><li>Если ноготь врастает снова и снова, предлагает коррекционную систему.</li><li>Объясняет, как стричь ногти дома.</li></ol></div><div><span class="eyebrow">Почему</span><h2>Отчего ноготь врастает</h2><ul class="tips"><li>Уголки срезают слишком коротко или закругляют.</li><li>Тесная или узкая обувь.</li><li>Травма пальца.</li><li>Особенность формы ногтя.</li></ul></div></div>'],
             [('Сколько стоит обработка вросшего ногтя?', '1 000 ₽ за обработку одного ногтя без установки системы. Коррекционная система 3 000 ₽. Точный состав мастер подскажет после осмотра.'),
              ('Можно ли самому вырезать вросший уголок?', 'Лучше не надо: ноготь часто врастает ещё глубже.'),
              ('Когда нужен врач, а не подолог?', 'Если есть гной, сильный отёк, температура или диабет.')], None, 'Эстетическая обработка вросшего ногтя')

service_page('muzhskoj-manikyur.html', 'Мужской маникюр', 'Мужской маникюр и педикюр в Новых Ватутинках | Венера, ногтевая студия',
             'Мужской маникюр в Новых Ватутинках без обязательного покрытия. Уход за ногтями и кутикулой, онлайн-запись. 6-я Нововатутинская, 5.',
             'Мужской маникюр в Новых Ватутинках', 'Аккуратные ногти и уход за кутикулой без обязательного покрытия. Выберите удобный формат и укажите пожелания к записи.',
             'Здравствуйте! Хочу записаться на мужской маникюр. Подскажите стоимость и время, когда в студии нет других гостей?', ['men-mani', 'men-pedi', 'men-both'],
             ['<span class="eyebrow">Зачем</span><h2>Это просто гигиена</h2><ul class="tips"><li>Руки работают каждый день: инструменты, клавиатура, документы, телефон.</li><li>Как стрижка у барбера: ногти ровные, нет заусенцев и сухой кожи.</li><li>Главное — аккуратные ногти и комфорт в повседневных делах.</li><li>При болезненных трещинах, воспалении или подозрении на вросший ноготь обратитесь к врачу.</li></ul><p class="note">Стоимость и длительность новых мужских услуг пока не подтверждены мастером.</p><p><a class="btn btn-line" href="index.html?service=men-mani#calc">Выбрать услугу и написать пожелания →</a></p>',
              '<div class="section-head"><span class="eyebrow">Если неловко</span><h2>Частые сомнения</h2></div><div class="fears"><div class="fear"><b>«Можно без покрытия?»</b><p>Да. Цветное покрытие не является обязательной частью процедуры.</p></div><div class="fear"><b>«Будет блестеть»</b><p>Без цветного лака и блеска.</p></div><div class="fear"><b>«Не знаю, что просить»</b><p>Мастер уточнит пожелания и объяснит этапы ухода.</p></div><div class="fear"><b>«Это долго»</b><p>Время уточните при записи. Можно в обед или после работы.</p></div></div>',
              '<div class="grid-2"><div><span class="eyebrow">Как проходит</span><h2>Мужской маникюр</h2><ol class="steps"><li>Мастер смотрит руки и спрашивает, что беспокоит.</li><li>Ногти приводят к одной длине и форме.</li><li>Убирают кутикулу и заусенцы.</li><li>Шлифуют поверхность ногтя.</li><li>Масло и крем для рук.</li></ol></div><div><span class="eyebrow">В подарок</span><h2>Подарить мужской маникюр</h2><p class="muted">Лучший способ уговорить мужчину попробовать — подарить сертификат.</p><a class="btn btn-line" href="podarochnyy-sertifikat.html">Сертификат для него</a></div></div>'],
             [('Будет ли заметно, что я сделал маникюр?', 'Нет. Мужской маникюр делают без цветного покрытия: видно только ровные ногти и кожу без заусенцев.'),
              ('Можно прийти, когда в студии никого нет?', 'Спросите об этом в Telegram при записи, мастер подскажет, когда это возможно.'),
              ('Сколько стоит мужской маникюр?', 'Стоимость уточняйте у мастера в Telegram.'),
              ('Как часто делать?', 'Обычно раз в 3–4 недели.')],
             ('Уход между визитами', ['Масло для кутикулы раз в день, лучше перед сном.', 'Крем для рук зимой и после спортзала.', 'Не обкусывайте заусенцы, дождитесь визита или аккуратно срежьте.'], 24, 'мужской маникюр'), 'Мужской маникюр')

# ====== certificate
GIFT_RULES = ['Сертификат действует после оплаты и подтверждения мастером в Telegram.', 'Номер и срок действия мастер укажет при оформлении.',
              'Если услуга дороже номинала, про доплату разницы спросите мастера.', 'Неиспользованную сумму можно вернуть по запросу.']
s = head('Подарочный сертификат на маникюр в Новых Ватутинках | Венера, ногтевая студия',
         'Подарочный сертификат на маникюр, педикюр или сумму в Новых Ватутинках. Соберите открытку онлайн и закажите у мастера в Telegram.',
         'podarochnyy-sertifikat.html', service_ld('Подарочный сертификат', [], 'Подарочный сертификат', 'podarochnyy-sertifikat.html', None))
s += page_hero('Подарочный сертификат', 'Подарочный сертификат', 'Выберите услугу или сумму, впишите имена, и сайт нарисует открытку. Закажите сертификат у мастера в Telegram.', 'Здравствуйте! Хочу подарочный сертификат.')
s += section(f'''<div class="gift" id="gift">
<div><canvas id="giftCanvas" width="1200" height="760" role="img" aria-label="Превью подарочного сертификата"></canvas><p class="note" style="text-align:center;margin-top:10px">Это превью. Сертификат оформляет мастер.</p></div>
<div><div class="tabs" role="tablist" aria-label="Кому подарок"><button class="tab" role="tab" type="button" data-gift="her" aria-selected="true">Для неё</button><button class="tab" role="tab" type="button" data-gift="him" aria-selected="false">Для него</button></div>
<div class="field-label">Что дарим</div><div class="opts" id="giftOpts" role="radiogroup" aria-label="Что дарим"></div>
<label class="field-label" for="gTo">Для кого</label><input class="field" id="gTo" maxlength="24" placeholder="Например, Ане">
<label class="field-label" for="gFrom">От кого</label><input class="field" id="gFrom" maxlength="24" placeholder="Например, от Максима">
<label class="field-label" for="gWish">Пожелание</label><input class="field" id="gWish" maxlength="60" placeholder="С днём рождения!">
<div class="actions" style="margin-top:16px"><a class="btn" id="gOrder" href="https://t.me/{B['telegram']}" target="_blank" rel="noopener">{ICON['tg']}Заказать в Telegram</a><button class="btn btn-line" type="button" id="gDownload">Скачать открытку</button></div>
<ul class="tips" style="margin-top:18px">{"".join(f"<li>{E(r)}</li>" for r in GIFT_RULES)}</ul>
</div></div>''')
s += section(related('podarochnyy-sertifikat.html'), 'alt')
s += foot()
PAGES['podarochnyy-sertifikat.html'] = s

# ====== prices
s = head('Цены на маникюр, педикюр и подологию в Новых Ватутинках | Венера, ногтевая студия',
         'Все цены: маникюр с гель-лаком 2 500 ₽, наращивание 4 000 ₽, смарт-педикюр 2 800 ₽, подолог от 300 ₽. Новые Ватутинки, ТиНАО.',
         'ceny.html', service_ld('Маникюр и педикюр', [x['id'] for x in SVC], 'Цены', 'ceny.html', None))
s += page_hero('Цены', 'Цены', 'Все услуги и стоимость. Цены из онлайн-записи, дизайн мастер подскажет на месте.', 'Здравствуйте! Хочу записаться. Подскажите свободное время?')
tables = ''.join(f'<div style="margin-bottom:22px">{price_table([x["id"] for x in SVC if x["cat"] == c["id"]], c["title"])}</div>' for c in D['categories'])
ext_t = '<table class="prices"><tr class="cat"><td colspan="2">Дополнительно</td></tr>' + ''.join(f'<tr><td>{x["name"]}</td><td>{"от " if x["from"] else ""}{rub(x["price"])}</td></tr>' for x in D['extras']) + '</table>'
s += section(f'{tables}{ext_t}<p class="disclaimer">Услуги подологии не являются медицинскими.</p>')
s += foot()
PAGES['ceny.html'] = s

# ====== contacts
s = head('Контакты: Новые Ватутинки, 6-я Нововатутинская, 5 | Венера, ногтевая студия',
         'Адрес, телефон, Telegram и онлайн-запись. 5 минут пешком от ТЦ «Лайнер». Новые Ватутинки, ТиНАО.', 'kontakty.html',
         {"@context": "https://schema.org", "@graph": [salon_ld()]})
s += page_hero('Контакты', 'Контакты', f'Москва, {E(ADDR)}, {B["postal"]}. Телефон <a href="tel:{B["phone_href"]}" style="color:#fff">{B["phone"]}</a>.', 'Здравствуйте! Хочу записаться.')
s += section(visit_block())
s += foot()
PAGES['kontakty.html'] = s

# ====== legal templates
def legal_page(path, title, sections_):
    s = head(f'{title} | Венера, ногтевая студия', title, path)
    s += page_hero(title, title, 'Шаблон документа. Перед публикацией сайта владелец заполняет данные в квадратных скобках, текст проверяет юрист.', 'Здравствуйте! Вопрос по обработке персональных данных.')
    body = ''.join(f'<h2 style="font-size:24px;margin-top:28px">{E(h)}</h2>' + ''.join(f'<p>{E(p)}</p>' for p in ps) for h, ps in sections_)
    s += section(f'<div style="max-width:760px">{body}</div>')
    s += foot()
    PAGES[path] = s


legal_page('politika.html', 'Политика обработки персональных данных', [
    ('1. Оператор', ['Оператор персональных данных: [ИП ФИО], ОГРНИП [номер], ИНН [номер], адрес: [адрес]. Контакт по вопросам данных: ' + B['phone'] + '.']),
    ('2. Какие данные обрабатываются', ['Сайт не содержит форм и не собирает имя или телефон. Запись ведётся во внешнем сервисе онлайн-записи, переписка — в Telegram, по правилам этих сервисов.',
                                       'Если подключена Яндекс Метрика и посетитель дал согласие: технические данные о посещении (cookie, IP-адрес, сведения о браузере и действиях на сайте).']),
    ('3. Цели', ['Анализ посещаемости и улучшение сайта.']),
    ('4. Основание', ['Согласие посетителя, которое он даёт в плашке о cookie. Без согласия счётчик не загружается.']),
    ('5. Сроки и хранение', ['[Срок хранения]. Данные обрабатываются с использованием сервисов, размещённых в Российской Федерации.']),
    ('6. Права посетителя', ['Отозвать согласие, запросить сведения об обработке, потребовать удаления — по контактам оператора.']),
    ('7. Изменения', ['Актуальная версия всегда на этой странице. Дата редакции: [дата].'])])
legal_page('soglasie.html', 'Согласие на обработку персональных данных', [
    ('Текст согласия', ['Я, посетитель сайта, даю согласие [ИП ФИО], ОГРНИП [номер], на обработку данных о моём посещении сайта (cookie, IP-адрес, сведения о браузере и действиях на сайте) с помощью сервиса Яндекс Метрика в целях анализа посещаемости.',
                        'Согласие действует до его отзыва. Отозвать согласие можно, написав по телефону ' + B['phone'] + ' или в Telegram, а также очистив cookie в браузере.']),
    ('Важно', ['Документ оформлен отдельно от политики, как требует закон. Перед публикацией проверить у юриста.'])])

# ---------------------------------------------------------------- write
robots = (f'User-agent: *\nAllow: /\nSitemap: {URL}/sitemap.xml\n' if URL else 'User-agent: *\nDisallow: /\n')
import re as _re
OUT = {k: _re.sub(r'(\d) (\d{3})( ?)₽', '\\1\u00a0\\2\u00a0₽', v) for k, v in PAGES.items()}
OUT['robots.txt'] = robots
if URL:
    OUT['sitemap.xml'] = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(
        f'<url><loc>{URL}/{"" if p == "index.html" else p}</loc></url>\n' for p in PAGES if p not in ('politika.html', 'soglasie.html')) + '</urlset>\n'

if __name__ == '__main__':
    check = '--check' in sys.argv
    bad = []
    for name, content in OUT.items():
        f = ROOT / name
        if check:
            if not f.exists() or f.read_text(encoding='utf-8') != content:
                bad.append(name)
        else:
            f.write_text(content, encoding='utf-8')
    if check:
        if bad:
            sys.exit('Собранные файлы устарели, запустите python3 src/build.py: ' + ', '.join(bad))
        print('OK: файлы актуальны')
    else:
        print('built', len(OUT), 'files')
