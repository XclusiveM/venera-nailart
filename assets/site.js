/* Венера, ногтевая студия — все интерактивные модули.
   Каждый модуль сам проверяет, есть ли его разметка на странице, и молча выходит, если нет. */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  function json(id) { try { return JSON.parse($('#' + id).textContent); } catch (e) { return {}; } }
  var CFG = json('site-data'), INFO = json('info-data');
  var SVC = CFG.services || [];
  function fmt(n) { return n == null ? 'по запросу' : new Intl.NumberFormat('ru-RU').format(n) + ' ₽'; }
  function dur(m) { if (!m) return ''; var h = Math.floor(m / 60), mm = m % 60; return h && mm ? h + ' ч ' + mm + ' мин' : h ? h + ' ч' : mm + ' мин'; }
  function tgUrl(text) { return 'https://t.me/' + CFG.tg + '?text=' + encodeURIComponent(text); }
  function find(name) { for (var i = 0; i < SVC.length; i++) if (SVC[i].name === name) return SVC[i]; return null; }
  function safe(name, fn) { try { fn(); } catch (e) { if (window.console) console.error('[' + name + ']', e); } }

  var toastT;
  function say(t) { var el = $('#toast'); if (!el) return; el.textContent = t; el.classList.add('on'); clearTimeout(toastT); toastT = setTimeout(function () { el.classList.remove('on'); }, 3200); }

  /* ---------- Метрика: цели (работают, только если счётчик подключён и есть согласие) ---------- */
  function goal(n) { try { if (window.ym && CFG.metrika) window.ym(CFG.metrika, 'reachGoal', n); } catch (e) {} }
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a,button'); if (!a) return;
    var h = a.getAttribute('href') || '';
    if (h.indexOf('bumpix.net') > -1) goal('book_click');
    else if (h.indexOf('t.me/') > -1) goal('telegram_click');
    else if (h.indexOf('tel:') === 0) goal('phone_click');
    if (a.dataset.goal) goal(a.dataset.goal);
  }, true);

  /* ---------- Меню ---------- */
  safe('menu', function () {
    var btn = $('.menu-btn'), sheet = $('#menu'); if (!btn || !sheet) return;
    function set(open) { sheet.hidden = !open; btn.setAttribute('aria-expanded', String(open)); }
    btn.addEventListener('click', function () { set(sheet.hidden); });
    $$('a', sheet).forEach(function (a) { a.addEventListener('click', function () { set(false); }); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') set(false); });
  });

  /* ---------- Мобильная кнопка записи ---------- */
  safe('mcta', function () {
    var c = $('#mcta'); if (!c) return;
    var start = $('[data-hero-end]'), end = $('.foot-site');
    var past = !start, atEnd = false;
    function upd() { c.classList.toggle('show', past && !atEnd); }
    if (!('IntersectionObserver' in window)) { c.classList.add('show'); return; }
    if (start) new IntersectionObserver(function (e) { past = !e[0].isIntersecting && e[0].boundingClientRect.top < 0; upd(); }).observe(start);
    if (end) new IntersectionObserver(function (e) { atEnd = e[0].isIntersecting; upd(); }).observe(end);
    document.addEventListener('focusin', function (e) { if (e.target.matches('input,textarea,select')) c.classList.remove('show'); });
    document.addEventListener('focusout', upd);
    upd();
  });

  /* ---------- Окно-шторка ---------- */
  var sheet = $('#sheet'), sheetBody = $('#sheetBody'), lastFocus = null;
  function openSheet(html) {
    if (!sheet) return; sheetBody.innerHTML = html; lastFocus = document.activeElement;
    if (sheet.showModal) sheet.showModal(); else sheet.setAttribute('open', '');
    var f = $('h3', sheetBody); if (f) { f.setAttribute('tabindex', '-1'); f.focus(); }
  }
  function closeSheet() { if (!sheet) return; if (sheet.close) sheet.close(); else sheet.removeAttribute('open'); }
  if (sheet) {
    $('.sheet-close', sheet).addEventListener('click', closeSheet);
    sheet.addEventListener('click', function (e) { if (e.target === sheet) closeSheet(); });
    sheet.addEventListener('close', function () { if (lastFocus && lastFocus.focus) lastFocus.focus(); });
  }
  function esc(t) { var d = document.createElement('div'); d.textContent = t; return d.innerHTML; }

  /* ---------- «Что это?» ---------- */
  function openInfo(name) {
    var d = INFO[name]; if (!d) return; var s = find(name);
    var meta = s ? '<div class="sheet-meta"><span>' + fmt(s.price) + '</span>' + (s.min ? '<span>' + dur(s.min) + '</span>' : '') + '</div>' : '';
    openSheet('<h3 id="sheetTitle">' + esc(name) + '</h3>' + meta + '<h4>Что это</h4><p>' + esc(d.what) + '</p><h4>Откуда пошло</h4><p>' + esc(d.origin) + '</p><h4>Кому подходит</h4><p>' + esc(d.why) + '</p>' +
      '<div class="actions" style="margin-top:16px"><a class="btn" href="' + CFG.book + '" target="_blank" rel="noopener">Записаться</a><a class="btn btn-line" href="' + tgUrl('Здравствуйте! Хочу записаться: ' + name.toLowerCase() + '.') + '" target="_blank" rel="noopener">Спросить в Telegram</a></div>');
    goal('info_open');
  }
  document.addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('[data-info]'); if (b) { e.preventDefault(); openInfo(b.dataset.info); } });

  /* ---------- Калькулятор: несколько услуг, комментарий и честный итог ---------- */
  var tryonState = { shape: 'миндаль', shade: 'вишня', touched: false };
  safe('calc', function () {
    var root = $('#calc'); if (!root) return;
    var list = $('#svcList'), tab = 'mani', picks = {}, extras = {};
    var tArea = null, copyBtn = null, message = '';
    list.setAttribute('role', 'group');
    list.setAttribute('aria-label', 'Выбор услуг. Можно выбрать несколько услуг из разных категорий');

    // Используем ID услуги, а не название или номер позиции: безопасно для ссылок.
    var requested = new URLSearchParams(location.search).get('service');
    var initial = SVC.find(function (s) { return s.id === requested; });
    if (initial && ['mani', 'pedi', 'men'].indexOf(initial.cat) !== -1) {
      tab = initial.cat; picks[tab] = initial.id;
    } else {
      picks.mani = 'mani-gel';
    }

    var send = $('#sendReq');
    var wrap = document.createElement('div'); wrap.className = 'booking-entry';
    var lab = document.createElement('label'); lab.htmlFor = 'bookingComment'; lab.textContent = 'Пожелания и комментарий';
    tArea = document.createElement('textarea'); tArea.id = 'bookingComment'; tArea.rows = 3; tArea.maxLength = 500;
    tArea.placeholder = 'Например: без покрытия, удобно после 18:00';
    var small = document.createElement('p'); small.className = 'booking-hint';
    small.textContent = 'Время и запись подтверждает мастер. Не пишите здесь диагнозы и медицинские данные.';
    copyBtn = document.createElement('button'); copyBtn.id = 'copyRequest'; copyBtn.type = 'button';
    copyBtn.className = 'btn btn-line'; copyBtn.textContent = 'Скопировать заказ';
    var status = document.createElement('span'); status.id = 'copyStatus'; status.setAttribute('role', 'status');
    status.className = 'booking-hint';
    wrap.append(lab, tArea, small, copyBtn, status);
    send.parentNode.insertBefore(wrap, send);

    function selectedServices() {
      return ['mani', 'pedi', 'men', 'podo'].map(function (cat) {
        return SVC.find(function (s) { return s.id === picks[cat]; });
      }).filter(Boolean);
    }
    function selectedExtras() {
      return picks.mani === 'mani-gel'
        ? (CFG.extras || []).filter(function (x) { return !!extras[x.id]; }) : [];
    }
    function active(s) { return picks[s.cat] === s.id; }
    function toggle(s) {
      if (active(s)) { delete picks[s.cat]; }
      else {
        // Один базовый вариант в каждой категории; отдельные мужские комплексы не дублируются.
        picks[s.cat] = s.id;
        if (s.cat === 'podo') {
          delete picks.mani; delete picks.pedi; delete picks.men; extras = {};
        } else {
          delete picks.podo;
          if (s.cat === 'mani') delete picks.men;
          if (s.cat === 'pedi' && (picks.men === 'men-pedi' || picks.men === 'men-both')) delete picks.men;
          if (s.cat === 'men') {
            if (s.id === 'men-both') { delete picks.mani; delete picks.pedi; extras = {}; }
            if (s.id === 'men-mani') { delete picks.mani; extras = {}; }
            if (s.id === 'men-pedi') delete picks.pedi;
          }
        }
      }
      if (picks.mani !== 'mani-gel') extras = {};
      render();
    }
    function render() {
      list.textContent = '';
      SVC.filter(function (s) { return s.cat === tab; }).forEach(function (s) {
        var row = document.createElement('div'); row.className = 'svc';
        row.setAttribute('aria-checked', String(active(s)));
        var b = document.createElement('button'); b.type = 'button'; b.className = 'nm';
        b.setAttribute('role', 'checkbox'); b.setAttribute('aria-checked', String(active(s)));
        b.setAttribute('aria-label', (active(s) ? 'Убрать ' : 'Добавить ') + s.name);
        b.innerHTML = '<span class="dot" aria-hidden="true"></span>';
        var t = document.createElement('span'); t.textContent = s.name;
        if (s.note) { var sm = document.createElement('small'); sm.textContent = s.note; t.appendChild(sm); }
        b.appendChild(t); b.addEventListener('click', function () { toggle(s); });
        row.appendChild(b);
        if (INFO[s.name]) {
          var ib = document.createElement('button'); ib.type = 'button'; ib.className = 'info-btn';
          ib.textContent = 'i'; ib.setAttribute('aria-label', 'Что такое ' + s.name);
          ib.dataset.info = s.name; row.appendChild(ib);
        }
        var p = document.createElement('div'); p.className = 'pr'; p.textContent = fmt(s.price);
        if (s.min) { var d = document.createElement('small'); d.textContent = dur(s.min); p.appendChild(d); }
        row.appendChild(p); list.appendChild(row);
      });
      var showExtras = tab === 'mani' && picks.mani === 'mani-gel';
      $('#extras').hidden = !showExtras;
      $$('.extra', root).forEach(function (b) {
        b.setAttribute('aria-pressed', String(showExtras && !!extras[b.dataset.extra]));
      });
      $$('.tab', root).forEach(function (b) { b.setAttribute('aria-selected', String(b.dataset.tab === tab)); });
      recalc();
    }
    function picked(id) {
      var b = $('#' + id + ' [aria-pressed="true"]');
      return b ? b.textContent.trim().toLowerCase() : '';
    }
    function totals() {
      var services = selectedServices(), adds = selectedExtras();
      var unknown = services.some(function (s) { return s.price == null; });
      var amount = services.reduce(function (n, s) { return n + (s.price || 0); }, 0);
      adds.forEach(function (x) { amount += x.price; });
      var approximate = adds.some(function (x) { return x.from; });
      var knownTime = services.length > 0 && services.every(function (s) { return Number.isFinite(s.min) && s.min > 0; });
      var minutes = knownTime ? services.reduce(function (n, s) { return n + s.min; }, 0) : null;
      return {services:services,adds:adds,unknown:unknown,amount:amount,approximate:approximate,minutes:minutes};
    }
    function buildMessage(t) {
      var parts = ['Здравствуйте! Хочу уточнить запись.', '', 'Услуги:'];
      t.services.forEach(function (s) { parts.push('• ' + s.name + ' — ' + fmt(s.price)); });
      t.adds.forEach(function (x) { parts.push('• Дополнительно: ' + x.name + ' — ' + (x.from ? 'от ' : '') + fmt(x.price)); });
      parts.push('', 'Стоимость: ' + (t.unknown ? 'нужно уточнить у мастера' : (t.approximate ? 'от ' : '') + fmt(t.amount)));
      parts.push('Продолжительность: ' + (t.minutes == null ? 'уточняется' : 'ориентировочно ' + dur(t.minutes)));
      if (t.adds.length) parts.push('Время дополнительных процедур необходимо уточнить.');
      if (picks.mani && tryonState.touched) parts.push('Форма: ' + tryonState.shape + '; оттенок: ' + tryonState.shade + '.');
      var d = picked('whenDay'), tm = picked('whenTime');
      if (d || tm) parts.push('Удобное время: ' + [d, tm].filter(Boolean).join(', ') + ' (если свободно).');
      var comment = tArea.value.trim();
      if (comment) parts.push('Пожелания: ' + comment);
      parts.push('', 'Подскажите, пожалуйста, свободное время и итоговую стоимость.');
      return parts.join('\n');
    }
    function recalc() {
      var t = totals(), lines = $('#lines'), total = $('#total'), time = $('#time');
      lines.textContent = '';
      function line(a, b) {
        var li = document.createElement('li'), x = document.createElement('span'), y = document.createElement('span');
        x.textContent = a; y.textContent = b; li.append(x, y); lines.appendChild(li);
      }
      t.services.forEach(function (s) { line(s.name, fmt(s.price)); });
      t.adds.forEach(function (x) { line(x.name, (x.from ? 'от ' : '+') + fmt(x.price)); });
      if (!t.services.length) {
        total.textContent = 'Выберите услугу'; total.classList.add('ask'); time.textContent = '';
        message = ''; send.removeAttribute('href'); send.setAttribute('aria-disabled', 'true');
        copyBtn.disabled = true; return;
      }
      total.textContent = t.unknown ? 'Стоимость уточняется' : (t.approximate ? 'от ' : '') + fmt(t.amount);
      total.classList.toggle('ask', t.unknown);
      time.textContent = t.minutes == null ? 'Время уточняется' : '≈ ' + dur(t.minutes) + (t.adds.length ? ' + время допов' : '');
      message = buildMessage(t);
      send.href = tgUrl(message); send.removeAttribute('aria-disabled'); copyBtn.disabled = false;
    }
    $$('.tab', root).forEach(function (b) {
      b.addEventListener('click', function () { tab = b.dataset.tab; render(); });
    });
    $$('.extra', root).forEach(function (b) {
      b.addEventListener('click', function () {
        if (picks.mani !== 'mani-gel') return;
        extras[b.dataset.extra] = !extras[b.dataset.extra];
        b.setAttribute('aria-pressed', String(!!extras[b.dataset.extra])); recalc();
      });
    });
    ['whenDay','whenTime'].forEach(function (id) {
      $$('#' + id + ' .chip').forEach(function (b) {
        b.addEventListener('click', function () {
          var on = b.getAttribute('aria-pressed') !== 'true';
          $$('#' + id + ' .chip').forEach(function (x) { x.setAttribute('aria-pressed', 'false'); });
          b.setAttribute('aria-pressed', String(on)); recalc();
        });
      });
    });
    tArea.addEventListener('input', recalc);
    document.addEventListener('tryon:change', recalc);
    copyBtn.addEventListener('click', function () {
      if (!message) return;
      function fail() { status.textContent = 'Не удалось скопировать. Откройте Telegram и выберите услуги вручную.'; }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(message).then(function () {
          status.textContent = 'Заказ скопирован'; say('Заказ скопирован');
        }).catch(fail);
      } else {
        var temp = document.createElement('textarea'); temp.value = message; temp.style.position = 'fixed';
        temp.style.left = '-9999px'; document.body.appendChild(temp); temp.select();
        var ok = false; try { ok = document.execCommand('copy'); } catch (e) {}
        temp.remove(); if (ok) { status.textContent = 'Заказ скопирован'; say('Заказ скопирован'); } else fail();
      }
    });
    send.addEventListener('click', function (e) { if (!message) e.preventDefault(); });
    render();
  });

  /* ---------- Примерка ---------- */
  var SH = { oval: 9, almond: 17, square: 6 };
  function nailD(shape, w) {
    var e = SH[shape], nw = w - 8, L = w > 30 ? 34 : 31, x0 = 4, y0 = 6 - e, top;
    function f(n) { return Math.round(n * 10) / 10; }
    if (shape === 'square') top = 'L' + x0 + ' ' + (y0 + 4) + ' Q' + x0 + ' ' + y0 + ' ' + (x0 + 4) + ' ' + y0 + ' L' + (x0 + nw - 4) + ' ' + y0 + ' Q' + (x0 + nw) + ' ' + y0 + ' ' + (x0 + nw) + ' ' + (y0 + 4);
    else if (shape === 'oval') top = 'L' + x0 + ' ' + f(y0 + nw / 2) + ' A' + f(nw / 2) + ' ' + f(nw / 2) + ' 0 0 1 ' + (x0 + nw) + ' ' + f(y0 + nw / 2);
    else top = 'L' + x0 + ' ' + f(y0 + nw * .95) + ' C' + x0 + ' ' + f(y0 + nw * .3) + ' ' + f(x0 + nw * .32) + ' ' + (y0 + 1) + ' ' + f(x0 + nw / 2) + ' ' + (y0 - 3) + ' C' + f(x0 + nw * .68) + ' ' + (y0 + 1) + ' ' + (x0 + nw) + ' ' + f(y0 + nw * .3) + ' ' + (x0 + nw) + ' ' + f(y0 + nw * .95);
    return 'M' + x0 + ' ' + L + ' ' + top + ' L' + (x0 + nw) + ' ' + L + ' Q' + f(x0 + nw / 2) + ' ' + (L + 7) + ' ' + x0 + ' ' + L + ' Z';
  }
  safe('tryon', function () {
    var svg = $('#tryonSvg'); if (!svg) return;
    var names = { oval: 'овал', almond: 'миндаль', square: 'квадрат' }, shape = 'almond', shade = $('.sw[aria-pressed="true"]');
    function apply() {
      $$('g[transform]', svg).forEach(function (g) {
        var r = $('rect', g); if (!r) return; var w = +r.getAttribute('width'), d = nailD(shape, w);
        $$('.nail,.nail-clip', g).forEach(function (p) { p.setAttribute('d', d); });
        var tip = $('.tip', g); if (tip) tip.setAttribute('height', String(30 + SH[shape] - 2));
      });
      var fin = shade.dataset.finish || '';
      $('.s1', svg).setAttribute('stop-color', shade.dataset.c1); $('.s2', svg).setAttribute('stop-color', shade.dataset.c2);
      $$('.tip', svg).forEach(function (t) { t.setAttribute('opacity', fin === 'french' ? '1' : '0'); });
      $$('.glit', svg).forEach(function (t) { t.setAttribute('opacity', fin === 'glitter' ? '.9' : '0'); });
      tryonState.shape = names[shape]; tryonState.shade = shade.dataset.name.toLowerCase();
      $('#choice').textContent = tryonState.shape + ', ' + tryonState.shade;
      svg.setAttribute('aria-label', 'Схема руки: ' + tryonState.shape + ', ' + tryonState.shade);
      $('#sendChoice').href = tgUrl('Здравствуйте! Хочу маникюр: форма ' + tryonState.shape + ', оттенок ' + tryonState.shade + '. Подскажите свободное время?');
      document.dispatchEvent(new CustomEvent('tryon:change'));
    }
    $$('[data-shape]').forEach(function (b) { b.addEventListener('click', function () { $$('[data-shape]').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); }); shape = b.dataset.shape; tryonState.touched = true; apply(); }); });
    $$('.sw').forEach(function (b) { b.addEventListener('click', function () { $$('.sw').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); }); shade = b; tryonState.touched = true; apply(); }); });
    window.__tryon = function (s, n) { var a = $('[data-shape="' + s + '"]'), c = $('.sw[data-name="' + n + '"]'); if (a) a.click(); if (c) c.click(); };
    apply();

    /* Квиз «подобрать за 3 вопроса» */
    var Q = [['occ', 'Повод', [['day', 'Каждый день'], ['work', 'Работа, офис'], ['party', 'Праздник'], ['date', 'Свидание'], ['vac', 'Отпуск']]],
      ['mood', 'Настроение', [['calm', 'Спокойное'], ['bright', 'Яркое'], ['classic', 'Классика']]],
      ['len', 'Длина', [['short', 'Короткие'], ['mid', 'Средние'], ['long', 'Длинные']]]];
    var qb = $('#quizBtn'); if (!qb) return;
    qb.addEventListener('click', function () {
      var a = {};
      openSheet('<h3 id="sheetTitle">Подберём форму и оттенок</h3>' + Q.map(function (q) { return '<div class="q-step"><div class="ctl-label">' + q[1] + '</div><div class="chips" data-q="' + q[0] + '">' + q[2].map(function (o) { return '<button class="chip" type="button" data-v="' + o[0] + '" aria-pressed="false">' + o[1] + '</button>'; }).join('') + '</div></div>'; }).join('') + '<div id="qRes" hidden><p>Попробуйте: <b id="qPick"></b></p><p class="muted" id="qWhy"></p><button class="btn" type="button" id="qShow">Показать на руке</button></div>');
      var pick;
      $$('[data-q]', sheetBody).forEach(function (g) { $$('.chip', g).forEach(function (b) { b.addEventListener('click', function () { $$('.chip', g).forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); }); a[g.dataset.q] = b.dataset.v; res(); }); }); });
      function res() {
        if (!a.occ || !a.mood || !a.len) return;
        var s = a.len === 'short' ? 'oval' : a.len === 'long' ? 'almond' : (a.occ === 'work' ? 'square' : 'almond'), c;
        if (a.mood === 'classic') c = (a.occ === 'party' || a.occ === 'date') ? 'Вишня' : 'Френч';
        else if (a.mood === 'calm') c = a.occ === 'party' ? 'Блёстки' : a.occ === 'vac' ? 'Молочный' : 'Нюд';
        else c = a.occ === 'party' ? 'Блёстки' : a.occ === 'work' ? 'Слива' : 'Вишня';
        var why = { day: 'практично и не надоест за 3 недели', work: 'аккуратно и уместно на любой встрече', party: 'заметно в свете и на фото', date: 'женственно и смело', vac: 'свежо на загорелой коже' }[a.occ];
        pick = [s, c]; $('#qPick').textContent = names[s] + ', ' + c.toLowerCase(); $('#qWhy').textContent = 'Почему: ' + why + '. Окончательно решите вместе с мастером.'; $('#qRes').hidden = false;
      }
      sheetBody.addEventListener('click', function (e) { if (e.target.id === 'qShow' && pick) { window.__tryon(pick[0], pick[1]); closeSheet(); goal('quiz_done'); var st = $('.hand-stage'); if (st) st.scrollIntoView({ behavior: 'smooth', block: 'center' }); } });
    });
  });

  /* ---------- Подология ---------- */
  safe('podo', function () {
    var foot = $('#foot'); if (!foot) return;
    var MAP = { ingrown: ['Обработка вросшего ногтя', 'Мягко освобождаем край ногтя, который врастает в кожу и мешает ходить.'],
      toes: ['Обработка пальчиков', 'Кожа вокруг ногтей и между пальцами, утолщённые ногти.'],
      callus: ['Обработка мозоли', 'Убираем мозоль и снимаем давление, чтобы было комфортно в обуви.'],
      feet: ['Обработка стоп', 'Огрубевшая кожа и трещины на пятках.'],
      system: ['Коррекционная система', 'Помогает ногтю расти ровно, если он врастает снова и снова.'],
      consult: ['Консультация', 'Мастер осмотрит стопы и подскажет, какая процедура нужна.'] };
    var curName = MAP.ingrown[0];
    function show(k) {
      var m = MAP[k]; if (!m) return; var s = find(m[0]); curName = m[0];
      $('#podoTitle').textContent = m[0]; $('#podoText').textContent = m[1];
      $('#podoPrice').textContent = s ? fmt(s.price) : ''; $('#podoTime').textContent = s ? dur(s.min) : '';
      $$('.hot', foot).forEach(function (h) { h.setAttribute('aria-pressed', String(h.dataset.podo === k)); });
    }
    $$('.hot', foot).forEach(function (h) { h.addEventListener('click', function () { show(h.dataset.podo); }); });
    $('#podoMore').addEventListener('click', function () { openInfo(curName); });
    $$('#footQuiz .chip').forEach(function (b) {
      b.addEventListener('click', function () {
        $$('#footQuiz .chip').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
        var ans = $('#footAns'), f = b.dataset.f;
        if (f === 'doctor') { ans.className = 'ans red'; ans.textContent = 'Сильная боль, гной или отёк — повод сначала показаться врачу. После лечения мастер поможет с уходом.'; return; }
        show(f); var s = find(MAP[f][0]); ans.className = 'ans'; ans.textContent = 'Похоже, подойдёт «' + MAP[f][0] + '», ' + fmt(s && s.price) + '. Карточка выше обновилась.'; goal('foot_quiz');
      });
    });
    show('ingrown');
  });

  /* ---------- Маршруты и карта ---------- */
  safe('routes', function () {
    var box = $('#mapBox'); if (!box) return;
    $$('.route-tab').forEach(function (t) {
      t.addEventListener('click', function () {
        $$('.route-tab').forEach(function (x) { x.setAttribute('aria-selected', String(x === t)); });
        box.dataset.route = t.dataset.route;
        $$('[data-route-info]').forEach(function (i) { i.hidden = i.dataset.routeInfo !== t.dataset.route; });
      });
    });
    var live = $('#mapLive'), btn = $('#mapBtn');
    if (btn && live) btn.addEventListener('click', function () { var f = $('iframe', live); if (!f.src) f.src = f.dataset.src; live.hidden = false; goal('map_open'); });
    var cl = $('#mapClose'); if (cl) cl.addEventListener('click', function () { live.hidden = true; });
  });

  /* ---------- Напоминание в календарь ---------- */
  function pad(n) { return String(n).padStart(2, '0'); }
  function icsDate(d) { return d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) + 'T' + pad(d.getHours()) + pad(d.getMinutes()) + '00'; }
  safe('remind', function () {
    $$('[data-remind]').forEach(function (b) {
      b.addEventListener('click', function () {
        var d = new Date(); d.setDate(d.getDate() + (+b.dataset.remind)); d.setHours(10, 0, 0, 0);
        var end = new Date(d.getTime() + 30 * 60000), title = 'Пора на ' + b.dataset.what;
        var ics = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Venera//RU', 'BEGIN:VEVENT', 'UID:' + Date.now() + '@venera', 'DTSTAMP:' + icsDate(new Date()), 'DTSTART:' + icsDate(d), 'DTEND:' + icsDate(end),
          'SUMMARY:' + title, 'DESCRIPTION:Запись онлайн: ' + CFG.book, 'URL:' + CFG.book, 'LOCATION:Москва\\, ' + CFG.addr.replace(/,/g, '\\,'),
          'BEGIN:VALARM', 'TRIGGER:-PT0M', 'ACTION:DISPLAY', 'DESCRIPTION:' + title, 'END:VALARM', 'END:VEVENT', 'END:VCALENDAR'].join('\r\n');
        var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([ics], { type: 'text/calendar;charset=utf-8' })); a.download = 'napominanie.ics';
        document.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
        say('Файл календаря скачан. Откройте его, и напоминание добавится'); goal('reminder');
      });
    });
  });

  /* ---------- Посоветовать подруге ---------- */
  safe('share', function () {
    var b = $('#shareBtn'); if (!b) return;
    b.addEventListener('click', function () {
      var url = /^https?:/.test(location.href) ? location.href.split('#')[0] : CFG.book;
      var text = 'Хожу на маникюр на 6-й Нововатутинской, 5. Советую, вот цены и запись:';
      goal('share');
      if (navigator.share) { navigator.share({ title: 'Венера, ногтевая студия', text: text, url: url }).catch(function () {}); return; }
      window.open('https://t.me/share/url?url=' + encodeURIComponent(url) + '&text=' + encodeURIComponent(text), '_blank', 'noopener');
    });
  });

  /* ---------- Сертификат ---------- */
  safe('gift', function () {
    var root = $('#gift'); if (!root) return;
    var cv = $('#giftCanvas'), ctx = cv.getContext('2d'); if (!ctx) return;
    var byName = function (n) { var s = find(n); return [n, s ? s.price : null]; };
    var G = { her: [byName('Маникюр с гель-лаком'), byName('Педикюр с гель-лаком'), byName('Смарт-педикюр'), ['Сумма 3 000 ₽', 3000, 1], ['Сумма 5 000 ₽', 5000, 1]],
      him: [['Мужской маникюр', null], ['Мужской педикюр', null], ['Сумма 3 000 ₽', 3000, 1], ['Сумма 5 000 ₽', 5000, 1]] };
    var who = 'her', idx = 0;
    function item() { return G[who][idx]; }
    function opts() {
      var box = $('#giftOpts'); box.innerHTML = '';
      G[who].forEach(function (g, i) {
        var b = document.createElement('button'); b.type = 'button'; b.className = 'opt'; b.setAttribute('role', 'radio'); b.setAttribute('aria-checked', String(i === idx));
        var t = document.createElement('b'); t.textContent = g[0]; var s = document.createElement('small'); s.textContent = g[2] ? 'на любые услуги' : (g[1] == null ? 'стоимость уточнит мастер' : fmt(g[1]));
        b.append(t, s); b.addEventListener('click', function () { idx = i; opts(); draw(); }); box.appendChild(b);
      });
    }
    function wrap(t, x, y, max, lh) { var w = t.split(' '), line = '', n = 0; w.forEach(function (word) { var test = line ? line + ' ' + word : word; if (ctx.measureText(test).width > max && line) { ctx.fillText(line, x, y + n * lh); n++; line = word; } else line = test; }); if (line) { ctx.fillText(line, x, y + n * lh); n++; } return n; }
    function draw() {
      var W = 1200, H = 760, him = who === 'him', it = item();
      var g = ctx.createLinearGradient(0, 0, W, H); g.addColorStop(0, him ? '#1E1B22' : '#3A1A40'); g.addColorStop(1, him ? '#0F0D12' : '#1C0A20'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      var r = ctx.createRadialGradient(980, 200, 20, 980, 200, 520); r.addColorStop(0, him ? 'rgba(190,180,200,.16)' : 'rgba(240,106,147,.32)'); r.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = r; ctx.fillRect(0, 0, W, H);
      var cols = him ? ['#F2D3C7', '#EBC6B6', '#F2D3C7'] : ['#D21E50', '#F2D7CE', '#8A4380'];
      [[960, 120, -14], [1040, 96, 0], [1120, 120, 14]].forEach(function (p, i) { ctx.save(); ctx.translate(p[0], p[1]); ctx.rotate(p[2] * Math.PI / 180); ctx.fillStyle = cols[i]; ctx.beginPath(); var w = 54, h = 132; ctx.moveTo(-w / 2, w / 2); ctx.arc(0, w / 2, w / 2, Math.PI, 0); ctx.lineTo(w / 2, h - 12); ctx.quadraticCurveTo(w / 2, h, w / 2 - 12, h); ctx.lineTo(-w / 2 + 12, h); ctx.quadraticCurveTo(-w / 2, h, -w / 2, h - 12); ctx.closePath(); ctx.fill(); ctx.fillStyle = 'rgba(255,255,255,.5)'; ctx.beginPath(); ctx.ellipse(-w / 5, h * .32, w / 9, h * .2, 0, 0, Math.PI * 2); ctx.fill(); ctx.restore(); });
      ctx.textAlign = 'left'; ctx.fillStyle = '#F6A2BC'; ctx.font = '600 24px Golos, Arial'; ctx.fillText(him ? 'ПОДАРОК ДЛЯ НЕГО' : 'ПОДАРОЧНЫЙ СЕРТИФИКАТ', 80, 104);
      ctx.fillStyle = '#fff'; ctx.font = '58px Tenor, Georgia'; ctx.fillText('Венера', 80, 176); ctx.fillStyle = '#CDB7CA'; ctx.font = '24px Golos, Arial'; ctx.fillText('ногтевая студия', 80, 212);
      ctx.fillStyle = '#fff'; ctx.font = '54px Tenor, Georgia'; var n = wrap(it[0], 80, 330, 760, 62), y = 330 + n * 62;
      ctx.font = '600 30px Golos, Arial'; ctx.fillStyle = '#F6A2BC'; ctx.fillText(it[2] ? 'на любые услуги' : (it[1] == null ? '' : fmt(it[1])), 80, y + 4); y += 56;
      var to = $('#gTo').value.trim(), from = $('#gFrom').value.trim(), wish = $('#gWish').value.trim();
      ctx.font = '30px Golos, Arial'; ctx.fillStyle = '#E8D7E4';
      if (to) { ctx.fillText('Для: ' + to, 80, y); y += 44; }
      if (from) { ctx.fillText(/^от\s/i.test(from) ? from.charAt(0).toUpperCase() + from.slice(1) : 'От: ' + from, 80, y); y += 44; }
      if (wish) { ctx.font = '30px Tenor, Georgia'; ctx.fillStyle = '#fff'; wrap('«' + wish + '»', 80, y + 8, 900, 38); }
      ctx.fillStyle = 'rgba(255,255,255,.14)'; ctx.fillRect(80, H - 128, W - 160, 1);
      ctx.font = '22px Golos, Arial'; ctx.fillStyle = '#CDB7CA'; ctx.fillText('№ ________   Действует до ________', 80, H - 84);
      ctx.fillText('Москва, ' + CFG.addr, 80, H - 50);
      ctx.textAlign = 'right'; ctx.fillText('Действует после подтверждения мастером', W - 80, H - 84); ctx.textAlign = 'left';
      var t = 'Здравствуйте! Хочу подарочный сертификат: ' + it[0].replace(/ /g, ' ') + (to ? ', для ' + to : '') + (from ? ', от ' + from.replace(/^от\s+/i, '') : '') + '. Как оформить и оплатить?';
      $('#gOrder').href = tgUrl(t);
    }
    $$('[data-gift]', root).forEach(function (b) { b.addEventListener('click', function () { $$('[data-gift]', root).forEach(function (x) { x.setAttribute('aria-selected', String(x === b)); }); who = b.dataset.gift; idx = 0; opts(); draw(); }); });
    ['gTo', 'gFrom', 'gWish'].forEach(function (id) { $('#' + id).addEventListener('input', draw); });
    $('#gDownload').addEventListener('click', function () { draw(); var a = document.createElement('a'); a.href = cv.toDataURL('image/png'); a.download = 'sertifikat-venera.png'; document.body.appendChild(a); a.click(); a.remove(); goal('gift_download'); });
    $('#gOrder').addEventListener('click', function () { goal('gift_order'); });
    opts();
    var ready = document.fonts && document.fonts.load ? Promise.all([document.fonts.load('58px Tenor'), document.fonts.load('30px Golos'), document.fonts.load('600 24px Golos')]) : Promise.resolve();
    draw(); ready.then(draw, draw);
  });

  /* ---------- Яндекс Метрика с согласием ---------- */
  safe('metrika', function () {
    if (!CFG.metrika) return;
    var key = 'venera_consent', v = null; try { v = localStorage.getItem(key); } catch (e) {}
    function load() { (function (m, e, t, r, i, k, a) { m[i] = m[i] || function () { (m[i].a = m[i].a || []).push(arguments); }; m[i].l = 1 * new Date(); k = e.createElement(t); a = e.getElementsByTagName(t)[0]; k.async = 1; k.src = r; a.parentNode.insertBefore(k, a); })(window, document, 'script', 'https://mc.yandex.ru/metrika/tag.js', 'ym'); window.ym(CFG.metrika, 'init', { clickmap: true, trackLinks: true, accurateTrackBounce: true }); }
    if (v === 'yes') { load(); return; } if (v === 'no') return;
    var c = $('#consent'); if (!c) return;
    c.innerHTML = '<p>Сайт может использовать cookie Яндекс Метрики, чтобы понимать, какие разделы полезны. <a href="politika.html">Подробнее</a></p><div class="actions"><button class="btn btn-sm" type="button" data-c="yes">Хорошо</button><button class="btn btn-sm btn-line" type="button" data-c="no">Без статистики</button></div>';
    c.hidden = false;
    $$('[data-c]', c).forEach(function (b) { b.addEventListener('click', function () { try { localStorage.setItem(key, b.dataset.c); } catch (e) {} c.hidden = true; if (b.dataset.c === 'yes') load(); }); });
  });
})();
