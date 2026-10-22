"""Браузерные проверки (Playwright, Chromium и WebKit если установлен): нет JS-ошибок, нет горизонтального скролла,
работают ключевые модули. Запуск: python3 tests/smoke.py  (нужен pip install playwright)"""
import csv, http.server, os, socketserver, sys, threading
from functools import partial
from pathlib import Path
from urllib.parse import unquote


def spaces(value):
    return value.replace(chr(160), ' ').replace(chr(8239), ' ')
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
PAGES = sorted(p.name for p in ROOT.glob('*.html')) + sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'admin-preview').glob('*.html'))
SNAPSHOTS = ROOT / 'artifacts' / 'screenshots'
SNAPSHOTS.mkdir(parents=True, exist_ok=True)
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


srv = socketserver.TCPServer(('127.0.0.1', 0), partial(H, directory=str(ROOT)))
port = srv.server_address[1]; threading.Thread(target=srv.serve_forever, daemon=True).start()
B = f'http://127.0.0.1:{port}/'
err = []
overflow_results = []


def page(br, w, path):
    pg = br.new_page(viewport={'width': w, 'height': 844}); pg.errs = []
    pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    pg.on('console', lambda m: pg.errs.append('console: '+m.text) if m.type == 'error' else None)
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
        for w in (320, 390, 768, 1440):
            for path in PAGES:
                pg = page(br, w, path)
                sw = pg.evaluate('document.documentElement.scrollWidth')
                overflow_results.append((kind, path, w, sw, 'FAIL' if sw > w else 'PASS'))
                if sw > w:
                    offenders = pg.evaluate('''() => [...document.querySelectorAll('body *')].map(e => ({tag:e.tagName.toLowerCase(), cls:typeof e.className==='string'?e.className.slice(0,65):'', right:Math.round(e.getBoundingClientRect().right), width:Math.round(e.getBoundingClientRect().width)})).filter(e => e.right > innerWidth + 2).sort((a,b)=>b.right-a.right).slice(0,8)''')
                    err.append(f'{kind} {w} {path}: горизонтальный скролл {sw}; offenders={offenders}')
                if path != 'muzhskoj-manikyur.html' and pg.locator('#privateVisit').count():
                    err.append(f'{kind} {w} {path}: индивидуальный визит вне мужской страницы')
                if pg.errs: err.append(f'{kind} {w} {path}: {pg.errs}')
                if path == 'index.html':
                    if pg.locator('#works .folio-card').count() != 8:
                        err.append(f'{kind} {w}: на главной не хватает 8 фотографий портфолио')
                    if not pg.locator('a[href="raboty.html"]').count():
                        err.append(f'{kind} {w}: нет перехода в фотогалерею')
                    if pg.locator('.mcta').count() != 0:
                        err.append(f'{kind} {w}: фиксированная плашка записи перекрывает контент')
                    if pg.locator('#foot svg').count() != 0:
                        err.append(f'{kind} {w}: огромная схема стопы всё ещё видна')
                    if pg.locator('.tryon .hand-stage:not([hidden])').count() != 0:
                        err.append(f'{kind} {w}: мультяшная рука всё ещё видна')
                    # Both specialist profiles must be reachable directly.
                    for profile in ('188382', '463374'):
                        url = f'https://bumpix.net/{profile}'
                        if pg.locator(f'#specialists .booking-v3-card a[href="{url}"][target="_blank"]').count() != 1:
                            err.append(f'{kind} {w}: отсутствует основная ссылка Bumpix {profile}')
                    if pg.locator('[data-remind]').count():
                        err.append(f'{kind} {w}: осталось выдуманное календарное напоминание')
                if (path == 'index.html' and w in (390, 1440)) or (path == 'muzhskoj-manikyur.html' and w == 390):
                    pg.screenshot(path=str(SNAPSHOTS / f'{kind}-{path.replace(".html", "")}-{w}.png'), full_page=False)
                if path == 'index.html' and w == 390:
                    for section in ('calc-section', 'podo', 'specialists'):
                        pg.locator(f'#{section}').scroll_into_view_if_needed()
                        pg.screenshot(path=str(SNAPSHOTS / f'{kind}-{section}-390.png'), full_page=False)
                pg.close()
        # Booking now uses direct external links, not an iframe/dialog.
        booking = page(br, 390, 'index.html')
        for profile in ('188382', '463374'):
            link = booking.locator(f'.booking-v3-card a[href="https://bumpix.net/{profile}"]')
            if link.count() != 1 or link.get_attribute('target') != '_blank':
                err.append(f'{kind}: неверная прямая ссылка мастера {profile}')
        if booking.locator('#booking-v3-frame').count():
            err.append(f'{kind}: устаревший iframe записи')
        if booking.errs:
            err.append(f'{kind} booking: {booking.errs}')
        booking.close()
        # Gallery: inspect actual image loading, category filtering and dialog navigation.
        gal = page(br, 390, 'raboty.html')
        cards = gal.locator('.folio-card')
        if cards.count() != 30:
            err.append(f'{kind}: ожидалось 30 фотографий, найдено {cards.count()}')
        if gal.locator('.folio-filter').count() != 5:
            err.append(f'{kind}: неверное число фильтров портфолио')
        gal.locator('.folio-card').first.scroll_into_view_if_needed()
        gal.wait_for_timeout(400)
        first_img_ok = gal.locator('.folio-card img').first.evaluate('(im) => im.complete && im.naturalWidth > 0')
        if not first_img_ok:
            err.append(f'{kind}: локальная миниатюра портфолио не загрузилась')
        gal.locator('[data-work-filter="pedicure"]').click()
        if gal.locator('.folio-card:visible').count() != 4:
            err.append(f'{kind}: фильтр педикюра должен показывать 4 фото')
        gal.locator('.folio-card:visible').first.click()
        if not gal.locator('#portfolioViewer').is_visible():
            err.append(f'{kind}: lightbox не открылся')
        else:
            gal.wait_for_function("""() => {
              const img = document.querySelector('#folioImage');
              return img && img.complete && img.naturalWidth > 0;
            }""", timeout=10000)
            before = gal.locator('#folioCounter').inner_text()
            gal.keyboard.press('ArrowRight')
            after = gal.locator('#folioCounter').inner_text()
            if before == after:
                err.append(f'{kind}: стрелка в галерее не переключает изображения')
            gal.screenshot(path=str(SNAPSHOTS / f'{kind}-gallery-lightbox-390.png'), full_page=False)
            gal.keyboard.press('Escape')
            if gal.locator('#portfolioViewer').is_visible():
                err.append(f'{kind}: Escape не закрывает галерею')
        gal.locator('[data-work-filter="all"]').click()
        if gal.locator('.folio-card:visible').count() != 30:
            err.append(f'{kind}: фильтр «Все» не возвращает 30 фотографий')
        gal.screenshot(path=str(SNAPSHOTS / f'{kind}-gallery-390.png'), full_page=False)
        if gal.errs: err.append(f'{kind} gallery: {gal.errs}')
        gal.close()

        # Visual regression guard for the mobile-first homepage.
        for mobile_width in (360, 390):
            hp = page(br, mobile_width, 'index.html')
            if not hp.locator('.home-hero h1').is_visible():
                err.append(f'{kind} {mobile_width}: главный заголовок не отображается')
            if hp.locator('.home-hero .hero-art').count():
                err.append(f'{kind} {mobile_width}: мультяшная иллюстрация осталась в первом экране')
            if not hp.locator('.home-hero .hero-primary').is_visible():
                err.append(f'{kind} {mobile_width}: нет кнопки выбора услуги')
            if hp.locator('.quick-prices a').count() != 3:
                err.append(f'{kind} {mobile_width}: не отображаются три быстрые цены')
            vh = hp.locator('.home-hero').bounding_box()
            if vh and vh['height'] > 1100:
                err.append(f'{kind} {mobile_width}: первый экран чрезмерно высокий ({vh["height"]:.0f}px)')
            hp.close()
        pg = page(br, 390, 'index.html')
        # Примерка находится на странице идей, а не на главной.
        tryon = page(br, 390, 'idei-manikyura.html')
        if tryon.locator('[data-shape="square"]').count() and tryon.locator('.swatch[aria-label="Нюд"]').count():
            tryon.click('[data-shape="square"]'); tryon.click('.swatch[aria-label="Нюд"]')
            if tryon.locator('#tryonSvg .s1').count() and tryon.get_attribute('#tryonSvg .s1', 'stop-color') != '#F2D7CE':
                err.append(f'{kind}: примерка не меняет цвет')
            if tryon.locator('#choice').count() and 'квадрат, нюд' not in tryon.inner_text('#choice'):
                err.append(f'{kind}: примерка не обновила подпись')
        else:
            err.append(f'{kind}: элементы примерки отсутствуют на idei-manikyura.html')
        tryon.close()
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
        if pg.locator('#copyRequest').count():
            if not pg.is_enabled('#copyRequest'):
                err.append(f'{kind}: копирование заказа недоступно')
        else:
            # Кнопка копирования опциональна; отправка заявки проверяется выше.
            print(f'{kind}: #copyRequest отсутствует, проверка копирования пропущена')
        pg.click('#calc [data-tab=pedi]')
        n = pg.locator('#svcList .nm').count()
        if n < 3:
            state = pg.evaluate("""() => ({
                selected: document.querySelector('#calc [aria-selected="true"]')?.getAttribute('data-tab'),
                services: document.querySelector('#svcList')?.innerText,
                calc: !!document.querySelector('#calc'),
                data: document.querySelector('#site-data')?.textContent?.substring(0,180)
            })""")
            err.append(f'{kind}: после выбора педикюра видно только {n} услуг; {state}; errors={pg.errs}')
        else:
            pg.click('#svcList .nm >> nth=2')
        if '5 800' not in spaces(pg.inner_text('#total')):
            err.append(f'{kind}: неверная сумма двух услуг')
        if '2 ч 30 мин' not in pg.inner_text('#time'):
            err.append(f'{kind}: неверная суммарная длительность')
        draft = spaces(unquote(pg.get_attribute('#sendReq', 'href') or ''))
        if '5 800' not in draft or '2 ч 30 мин' not in draft:
            err.append(f'{kind}: цена и время не попали в Telegram-заявку')
        draft = spaces(unquote(pg.get_attribute('#sendReq', 'href') or ''))
        if 'Педикюр с гель-лаком' not in draft or 'Маникюр с гель-лаком' not in draft:
            err.append(f'{kind}: Telegram потерял выбранную услугу')
        pg.click('.hot[data-podo=callus]')
        if 'мозоли' not in pg.inner_text('#podoTitle'): err.append(f'{kind}: точка стопы не работает')
        pg.click('.route-tab[data-route=metro]')
        if pg.get_attribute('#mapBox', 'data-route') != 'metro': err.append(f'{kind}: маршрут не переключается')
        pg.click('#calc [data-tab=mani]')
        info = pg.locator('[data-info="Маникюр с гель-лаком"]')
        if not info.count():
            err.append(f'{kind}: кнопка информации не найдена; services='
                       f'{pg.locator("#svcList").inner_text()}; errors={pg.errs}')
        else:
            info.click(); pg.wait_for_timeout(200)
            if not pg.is_visible('#sheet'): err.append(f'{kind}: окно «i» не открылось')
            else:
                pg.click('.sheet-close')
                if pg.is_visible('#sheet'): err.append(f'{kind}: окно «i» не закрылось')
        if pg.errs: err.append(f'{kind} interactions: {pg.errs}')
        pg.close()
        # Customer navigation, keyboard access and the editorial homepage.
        nav = page(br, 390, 'index.html')
        nav.locator('.menu-btn').click()
        if nav.locator('#menu').get_attribute('hidden') is not None:
            err.append(f'{kind}: меню не открылось')
        nav.keyboard.press('Escape')
        if nav.locator('.menu-btn').get_attribute('aria-expanded') != 'false':
            err.append(f'{kind}: Escape не закрыл меню')
        nav.locator('#calc [data-tab="mani"]').focus()
        nav.keyboard.press('ArrowRight')
        if nav.locator('#calc [data-tab="pedi"]').get_attribute('aria-selected') != 'true':
            err.append(f'{kind}: клавиатурный переход вкладок не работает')
        if nav.locator('#services h2').count() != 1:
            err.append(f'{kind}: заголовок услуг повреждён')
        if not nav.locator('.hero-photo img').evaluate('(im) => im.complete && im.naturalWidth > 0'):
            err.append(f'{kind}: фото первого экрана не загрузилось')
        if nav.errs: err.append(f'{kind} navigation: {nav.errs}')
        nav.close()
        # The recommendation page must change the actual recommendation.
        studio = page(br, 390, 'nail-studio.html')
        studio.get_by_text('Ярко и смело', exact=True).click()
        if 'Смелый образ' not in studio.locator('#advisorTitle').inner_text():
            err.append(f'{kind}: подбор образа не обновляет результат')
        studio.locator('.palette-tile[data-name="Вишня"]').click()
        if 'Вишня' not in studio.locator('#pickedLabel').inner_text():
            err.append(f'{kind}: подборка оттенков не сохраняет выбор')
        studio.locator('.palette-tile[data-name="Вишня"]').click()
        if 'Вишня' in studio.locator('#pickedLabel').inner_text():
            err.append(f'{kind}: оттенок нельзя удалить из подборки')
        if studio.errs: err.append(f'{kind} studio: {studio.errs}')
        studio.close()
        # Public demo editors are usable but never publish changes.
        settings = page(br, 390, 'admin-preview/marketing.html')
        if not settings.locator('#title').input_value():
            err.append(f'{kind}: настройки продвижения не загрузились')
        settings.locator('#title').fill('Проверка локального черновика')
        settings.locator('#title').press('Tab')
        if 'сохранён' not in settings.locator('#message').inner_text():
            err.append(f'{kind}: черновик продвижения не сохраняется')
        settings.reload()
        if settings.locator('#title').input_value() != 'Проверка локального черновика':
            err.append(f'{kind}: черновик продвижения потерян после обновления')
        if settings.errs: err.append(f'{kind} marketing: {settings.errs}')
        settings.close()
        editor = page(br, 390, 'admin-preview/index.html')
        editor.locator('#search').fill('Маникюр с гель-лаком')
        if editor.locator('#list article').count() != 2:
            err.append(f'{kind}: редактор не разделяет одноимённые услуги мастеров')
        if editor.get_by_text('Мастер: Юлия', exact=True).count() != 1:
            err.append(f'{kind}: редактор не показывает мастера услуги')
        if editor.errs: err.append(f'{kind} catalog editor: {editor.errs}')
        editor.close()
        # Master switch, separate catalogs, exact service info and private quote.
        pg = page(br, 390, 'index.html')
        pg.locator('[data-master="julia"]').click()
        if pg.locator('#calc [data-tab="men"]').is_visible():
            err.append(f'{kind}: Юлии предлагается мужской уход из чужого каталога')
        pg.locator('#svcList .nm').filter(has_text='Маникюр с гель-лаком').click()
        if '1 800' not in spaces(pg.inner_text('#total')):
            err.append(f'{kind}: цена Юлии смешана с ценой Венеры')
        pg.locator('#svcList [data-service-id="julia-gel"]').click()
        if '1 800' not in spaces(pg.inner_text('#sheet .sheet-meta')):
            err.append(f'{kind}: окно информации показывает цену другого мастера')
        if pg.locator('#sheet .actions a.btn').first.get_attribute('href') != 'https://bumpix.net/463374':
            err.append(f'{kind}: окно услуги Юлии отправляет к другому мастеру')
        pg.keyboard.press('Escape')
        if pg.locator('#privateVisit').count():
            err.append(f'{kind}: индивидуальный визит появился в общем калькуляторе')
        pg.locator('[data-master="venera"]').click()
        pg.locator('#svcList .nm').filter(has_text='Маникюр без покрытия').click()
        if pg.locator('#extras').is_visible():
            err.append(f'{kind}: дизайн предлагается без покрытия')
        if pg.errs: err.append(f'{kind} private/master: {pg.errs}')
        pg.close()
        prices = page(br, 390, 'ceny.html')
        if '2 500' not in spaces(prices.locator('[data-service-id="mani-gel"] td').last.inner_text()):
            err.append(f'{kind}: прайс Венеры заменён ценой Юлии')
        if '1 800' not in spaces(prices.locator('[data-service-id="julia-gel"] td').last.inner_text()):
            err.append(f'{kind}: прайс Юлии отсутствует')
        prices.close()
        # Предварительный выбор при переходе из мужского раздела.
        pg = page(br, 390, 'index.html?service=men-mani#calc')
        if 'Мужской маникюр' not in pg.inner_text('#lines'):
            err.append(f'{kind}: мужская услуга не выбрана через ссылку')
        if spaces(pg.inner_text('#total')) != '≈ 1 700 ₽' or '45 мин' not in pg.inner_text('#time'):
            err.append(f'{kind}: предварительные мужские цена и время не восстановлены')
        if pg.locator('#calc .summary > a.btn:not(#sendReq)').is_visible():
            err.append(f'{kind}: мужская запись ведёт в Bumpix')
        if pg.locator('#privateVisit').count():
            err.append(f'{kind}: мужская услуга на главной открыла индивидуальный визит')
        pg.close()
        # Private visit exists only on the separate men's manicure page.
        pg = page(br, 390, 'muzhskoj-manikyur.html#calc')
        if pg.locator('#svcList .nm').count() != 3 or 'Мужской маникюр' not in pg.inner_text('#lines'):
            err.append(f'{kind}: отдельный калькулятор потерял мужские услуги')
        pg.locator('#privateVisit').check()
        if spaces(pg.inner_text('#total')) != '≈ 3 825 ₽' or '2 125 ₽' not in spaces(pg.inner_text('#privateVisitPrice')):
            err.append(f'{kind}: максимальный индивидуальный расчёт неверен для маникюра 1700 ₽ / 45 мин')
        if pg.locator('#calc .summary > a.btn:not(#sendReq)').is_visible():
            err.append(f'{kind}: индивидуальный визит отправляется в обычную онлайн-запись')
        before = unquote(pg.get_attribute('#sendReq', 'href') or '')
        if 't.me/Venera_Ni' not in before or 'без других клиентов' not in before or 'Доплата:' not in before or '2 125 ₽' not in spaces(before) or '≈ 3 825 ₽' not in spaces(before):
            err.append(f'{kind}: мужская индивидуальная заявка потеряла условия')
        pg.locator('.booking-preview summary').click()
        if pg.inner_text('#requestPreview') not in before:
            err.append(f'{kind}: предпросмотр заявки не совпадает с Telegram')
        pg.locator('#privateVisit').scroll_into_view_if_needed()
        pg.screenshot(path=str(SNAPSHOTS / f'{kind}-private-visit-390.png'), full_page=False)
        pg.locator('#privateVisit').uncheck()
        if 'без других клиентов' in unquote(pg.get_attribute('#sendReq', 'href') or ''):
            err.append(f'{kind}: обычный мужской визит сохранил приватные условия')
        pg.locator('#privateVisit').check()
        pg.locator('#svcList .nm').filter(has_text='Мужской педикюр').click()
        if spaces(pg.inner_text('#total')) != '≈ 3 000 ₽' or '1 ч 15 мин' not in pg.inner_text('#time'):
            err.append(f'{kind}: мужской педикюр потерял цену или длительность')
        if pg.locator('#privateVisit').is_visible() or 'без других клиентов' in unquote(pg.get_attribute('#sendReq', 'href') or ''):
            err.append(f'{kind}: индивидуальный визит сохранился у педикюра')
        pg.locator('#svcList .nm').filter(has_text='Мужской маникюр и педикюр').click()
        if spaces(pg.inner_text('#total')) != '≈ 4 700 ₽' or '2 ч' not in pg.inner_text('#time'):
            err.append(f'{kind}: мужской комплекс потерял цену или длительность')
        if pg.locator('#privateVisit').is_visible():
            err.append(f'{kind}: индивидуальный визит появился у комплекса')
        pg.locator('.booking-reset').click()
        if pg.locator('#privateVisit').is_checked() or pg.get_attribute('#sendReq', 'aria-disabled') != 'true':
            err.append(f'{kind}: очистка оставила приватный визит или активную заявку')
        if pg.errs: err.append(f'{kind} mens private: {pg.errs}')
        pg.close()
        # Embedded full catalog must work when the live JSON is unavailable.
        fallback = br.new_page(viewport={'width': 390, 'height': 844})
        fallback.route('**/data/services.json', lambda r: r.abort())
        fallback.goto(B + 'index.html')
        fallback.locator('[data-master="julia"]').click()
        fallback.locator('#svcList .nm').filter(has_text='Маникюр с гель-лаком').click()
        if '1 800' not in spaces(fallback.inner_text('#total')):
            err.append(f'{kind}: резервный каталог потерял услуги Юлии')
        fallback.locator('#bookingComment').fill('<img src=x onerror=alert(1)> & ? #')
        fallback.locator('.booking-preview summary').click()
        if fallback.locator('#requestPreview img').count() or '<img src=x' not in fallback.inner_text('#requestPreview'):
            err.append(f'{kind}: комментарий интерпретируется как HTML')
        fallback.close()
        pg = page(br, 390, 'podarochnyy-sertifikat.html'); pg.fill('#gTo', 'Ане'); pg.click('[data-gift=him]')
        if 'Ане' not in pg.get_attribute('#gOrder', 'href').encode().decode() and '%D0%90%D0%BD%D0%B5' not in pg.get_attribute('#gOrder', 'href'): err.append(f'{kind}: сертификат без имени в заявке')
        if pg.errs: err.append(f'{kind} gift: {pg.errs}')
        pg.close(); br.close()
srv.shutdown()
# Reproducible per-page, per-viewport overflow results (generated by actual browser run).
with (SNAPSHOTS.parent / 'overflow-results.csv').open('w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(('browser', 'page', 'viewport_px', 'scroll_width_px', 'result'))
    writer.writerows(overflow_results)
print('Overflow matrix:', len(overflow_results), 'checks; report: artifacts/overflow-results.csv')

if err: sys.exit('\n'.join(err))
print('OK: smoke', ', '.join(k for k, _ in kinds))
