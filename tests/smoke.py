"""Браузерные проверки (Playwright, Chromium и WebKit если установлен): нет JS-ошибок, нет горизонтального скролла,
работают ключевые модули. Запуск: python3 tests/smoke.py  (нужен pip install playwright)"""
import http.server, os, socketserver, sys, threading
from functools import partial
from pathlib import Path
from urllib.parse import unquote


def spaces(value):
    return value.replace(chr(160), ' ').replace(chr(8239), ' ')
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
PAGES = sorted(p.name for p in ROOT.glob('*.html'))
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


srv = socketserver.TCPServer(('127.0.0.1', 0), partial(H, directory=str(ROOT)))
port = srv.server_address[1]; threading.Thread(target=srv.serve_forever, daemon=True).start()
B = f'http://127.0.0.1:{port}/'
err = []


def page(br, w, path):
    pg = br.new_page(viewport={'width': w, 'height': 844}); pg.errs = []
    pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith(B) or r.request.url.startswith(('data:', 'blob:')) else r.abort())
    pg.goto(B + path); pg.wait_for_timeout(300); return pg


with sync_playwright() as p:
    kinds = [('chromium', p.chromium)]
    try:
        p.webkit.launch().close(); kinds.append(('webkit', p.webkit))
    except Exception:
        pass
    for kind, bt in kinds:
        opts = {'executable_path': os.environ['CHROMIUM']} if kind == 'chromium' and os.environ.get('CHROMIUM') else {}
        br = bt.launch(**opts)
        for w in (360, 390, 768, 1440):
            for path in PAGES:
                pg = page(br, w, path)
                sw = pg.evaluate('document.documentElement.scrollWidth')
                if sw > w: err.append(f'{kind} {w} {path}: горизонтальный скролл {sw}')
                if pg.errs: err.append(f'{kind} {w} {path}: {pg.errs}')
                pg.close()
        pg = page(br, 390, 'index.html')
        pg.click('[data-shape=square]'); pg.click('.sw[data-name="Нюд"]')
        if pg.get_attribute('#tryonSvg .s1', 'stop-color') != '#F2D7CE': err.append(f'{kind}: примерка не меняет цвет')
        if 'квадрат, нюд' not in pg.inner_text('#choice'): err.append(f'{kind}: примерка не обновила подпись')
        for t in ('pedi', 'podo', 'men', 'mani'):
            pg.click(f'#calc [data-tab={t}]')
            if not pg.inner_text('#total').strip() or pg.inner_text('#total') == '—': err.append(f'{kind}: пустой итог во вкладке {t}')
        pg.click('#calc [data-tab=mani]'); pg.click('#whenDay .chip >> nth=1')
        if '%D0%B7%D0%B0%D0%B2%D1%82%D1%80%D0%B0' not in pg.get_attribute('#sendReq', 'href'): err.append(f'{kind}: заявка в Telegram без дня')
        # Проверка комментария клиента, суммы и нескольких услуг в Telegram-заявке.
        pg.fill('#bookingComment', 'Без покрытия, удобно после 18:00')
        draft = spaces(unquote(pg.get_attribute('#sendReq', 'href') or ''))
        if 'Без покрытия, удобно после 18:00' not in draft:
            err.append(f'{kind}: Telegram не содержит комментария')
        if 'Маникюр с гель-лаком' not in draft or '2 500 ₽' not in draft:
            err.append(f'{kind}: Telegram не содержит цену и название услуги')
        if not pg.is_enabled('#copyRequest'):
            err.append(f'{kind}: копирование заказа недоступно')
        pg.click('#calc [data-tab=pedi]')
        pg.click('#svcList .nm >> nth=2')
        if '5 800' not in spaces(pg.inner_text('#total')):
            err.append(f'{kind}: неверная сумма двух услуг')
        draft = spaces(unquote(pg.get_attribute('#sendReq', 'href') or ''))
        if 'Педикюр с гель-лаком' not in draft or 'Маникюр с гель-лаком' not in draft:
            err.append(f'{kind}: Telegram потерял выбранную услугу')
        pg.click('.hot[data-podo=callus]')
        if 'мозоли' not in pg.inner_text('#podoTitle'): err.append(f'{kind}: точка стопы не работает')
        pg.click('.route-tab[data-route=metro]')
        if pg.get_attribute('#mapBox', 'data-route') != 'metro': err.append(f'{kind}: маршрут не переключается')
        pg.click('#calc [data-tab=mani]')
        pg.click('[data-info="Маникюр с гель-лаком"]'); pg.wait_for_timeout(200)
        if not pg.is_visible('#sheet'): err.append(f'{kind}: окно «i» не открылось')
        pg.click('.sheet-close')  # Close the earlier info dialog before testing the calculator.
        # The booking calculator must support two categories, keep their prices,
        # and include the comment and exact selected services in the Telegram draft.
        pg.click('#calc [data-tab=mani]')
        pg.click('#svcList button.nm >> nth=0')
        # The initial manicure can be toggled off. Re-select it if needed.
        if 'Маникюр с гель-лаком' not in pg.inner_text('#lines'):
            pg.click('#svcList button.nm >> nth=0')
        pg.click('#calc [data-tab=pedi]')
        pg.get_by_role('checkbox', name='Добавить Педикюр с гель-лаком').click()
        if '5 800' not in pg.inner_text('#total').replace('\u00a0', ' ').replace('\u202f', ' '):
            err.append(f'{kind}: суммарная цена двух услуг не равна 5 800 ₽')
        if '2 ч 30 мин' not in pg.inner_text('#time'):
            err.append(f'{kind}: неверная суммарная длительность двух услуг')
        pg.fill('#bookingComment', 'Тест: молочный цвет, после 18:00')
        from urllib.parse import urlparse, parse_qs
        u = pg.get_attribute('#sendReq', 'href') or ''
        m = parse_qs(urlparse(u).query).get('text', [''])[0]
        m = m.replace('\u00a0', ' ').replace('\u202f', ' ')
        for part in ('Маникюр с гель-лаком', 'Педикюр с гель-лаком', '5 800', '2 ч 30 мин', 'Тест: молочный цвет'):
            if part not in m: err.append(f'{kind}: Telegram-заявка потеряла {part}')
        if not pg.locator('#copyRequest').is_visible():
            err.append(f'{kind}: отсутствует резервное копирование заказа')
        # Unconfirmed men prices cannot be displayed as an exact payable total.
        pg.click('#calc [data-tab=men]')
        pg.get_by_role('checkbox', name='Добавить Мужской маникюр').click()
        if 'уточняется' not in pg.inner_text('#total').lower():
            err.append(f'{kind}: цена мужской услуги указана как подтверждённая')
        if pg.errs: err.append(f'{kind} interactions: {pg.errs}')
        pg.close()
        # Предварительный выбор при переходе из мужского раздела.
        pg = page(br, 390, 'index.html?service=men-mani#calc')
        if 'Мужской маникюр' not in pg.inner_text('#lines'):
            err.append(f'{kind}: мужская услуга не выбрана через ссылку')
        if 'Стоимость уточняется' not in pg.inner_text('#total'):
            err.append(f'{kind}: неутверждённая мужская цена показана как окончательная')
        if pg.errs: err.append(f'{kind} male deep link: {pg.errs}')
        pg.close()
        pg = page(br, 390, 'podarochnyy-sertifikat.html'); pg.fill('#gTo', 'Ане'); pg.click('[data-gift=him]')
        if 'Ане' not in pg.get_attribute('#gOrder', 'href').encode().decode() and '%D0%90%D0%BD%D0%B5' not in pg.get_attribute('#gOrder', 'href'): err.append(f'{kind}: сертификат без имени в заявке')
        if pg.errs: err.append(f'{kind} gift: {pg.errs}')
        pg.close(); br.close()
srv.shutdown()
if err: sys.exit('\n'.join(err))
print('OK: smoke', ', '.join(k for k, _ in kinds))
