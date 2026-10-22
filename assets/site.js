/* Венера, ногтевая студия — все интерактивные модули.
   Каждый модуль сам проверяет, есть ли его разметка на странице, и молча выходит, если нет. */
(async function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  function json(id) { try { return JSON.parse($('#' + id).textContent); } catch (e) { return {}; } }
  var CFG = json('site-data'), INFO = json('info-data');
  var ORIGINAL_SERVICES = (CFG.services || []).slice();
  var catalogLoaded = false;
  /* Единый каталог услуг: при сетевой ошибке сохраняем прежний встроенный прайс.
     Важно: статические текстовые цены на страницах пока не синхронизированы. */
  try {
    var response = await fetch('data/services.json', { cache: 'no-store' });
    if (!response.ok) throw new Error('HTTP ' + response.status);
    var catalog = await response.json();
    if (catalog.schemaVersion !== 1 || !Array.isArray(catalog.services) ||
        !Array.isArray(catalog.categories) || !Array.isArray(catalog.extras)) {
      throw new Error('Некорректная структура каталога');
    }
    var categoryIds = catalog.categories.map(function (c) { return c.id; });
    var seenIds = {};
    catalog.services.forEach(function (item) {
      if (!item || typeof item.id !== 'string' || seenIds[item.id] ||
          typeof item.name !== 'string' || !item.name.trim() ||
          categoryIds.indexOf(item.cat) < 0 ||
          (item.price !== null && (!Number.isInteger(item.price) || item.price < 0)) ||
          (item.min !== null && (!Number.isInteger(item.min) || item.min < 1))) {
        throw new Error('Ошибка данных услуги');
      }
      seenIds[item.id] = true;
    });
    catalogLoaded = true;
    CFG.services = catalog.services.filter(function (item) {
      return !item.status || item.status === 'published';
    });
    CFG.extras = catalog.extras.filter(function (item) {
      return !item.status || item.status === 'published';
    });
    CFG.cats = catalog.categories;
    CFG.individualVisit = catalog.individualVisit;
  } catch (error) {
    if (window.console) console.warn('[catalog] Встроенный прайс используется как резервный', error);
  }
  /* Обновляем существующие таблицы прайса из единого каталога, не используя innerHTML
     с пользовательскими данными. Скрытые услуги убираем из таблиц. */
  function syncPriceTables() {
    var byName = {}, byId = {};
    (CFG.services || []).forEach(function (item) { byId[item.id] = item; if ((item.master || 'venera') === 'venera') byName[item.name] = item; });
    var originalByName = {};
    ORIGINAL_SERVICES.forEach(function (item) {
      if ((item.master || 'venera') !== 'venera') return;
      originalByName[item.name] = item;
      if (byId[item.id]) byName[item.name] = byId[item.id];
    });
    document.querySelectorAll('table.prices tr:not(.cat)').forEach(function (row) {
      var cells = row.querySelectorAll('td');
      if (cells.length !== 2) return;
      var info = cells[0].querySelector('[data-info]');
      var raw = info ? info.getAttribute('data-info') : '';
      if (!raw) {
        var clone = cells[0].cloneNode(true);
        clone.querySelectorAll('small,button').forEach(function (n) { n.remove(); });
        raw = clone.textContent.trim();
      }
      var rowId = row.dataset.serviceId;
      var item = rowId ? byId[rowId] : byName[raw];
      if (rowId && !item && catalogLoaded) { row.hidden = true; return; }
      if (!item && catalogLoaded && originalByName[raw]) { row.hidden = true; return; }
      if (!item) return;
      if (item.status && item.status !== 'published') { row.hidden = true; return; }
      if (info) info.setAttribute('data-info', item.name);
      var titleNode = cells[0].firstChild;
      if (titleNode && titleNode.nodeType === 3) titleNode.textContent = item.name + ' ';
      cells[1].textContent = item.price === null ? 'По запросу' : new Intl.NumberFormat('ru-RU').format(item.price) + ' ₽';
      var small = cells[0].querySelector('small');
      if (small) {
        var minutes = item.min;
        var duration = minutes ? (minutes >= 60 ? Math.floor(minutes / 60) + ' ч' + (minutes % 60 ? ' ' + minutes % 60 + ' мин' : '') : minutes + ' мин') : '';
        small.textContent = [duration, item.note].filter(Boolean).join(' · ');
      }
    });
  }
  syncPriceTables();
  var SVC = CFG.services || [];
  function fmt(n) { return n == null ? 'по запросу' : new Intl.NumberFormat('ru-RU').format(n) + ' ₽'; }
  function dur(m) { if (!m) return ''; var h = Math.floor(m / 60), mm = m % 60; return h && mm ? h + ' ч ' + mm + ' мин' : h ? h + ' ч' : mm + ' мин'; }
  function tgUrl(text) { return 'https://t.me/' + CFG.tg + '?text=' + encodeURIComponent(text); }
  function find(name) {
    for (var i = 0; i < SVC.length; i++) if (SVC[i].name === name) return SVC[i];
    for (var j = 0; j < ORIGINAL_SERVICES.length; j++) {
      if (ORIGINAL_SERVICES[j].name === name) {
        for (var k = 0; k < SVC.length; k++) if (SVC[k].id === ORIGINAL_SERVICES[j].id) return SVC[k];
      }
    }
    return null;
  }
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
  function esc(t) { var d = document.createElement('div'); d.textContent = String(t == null ? '' : t); return d.innerHTML.replace(/\"/g, '&quot;').replace(/'/g, '&#39;'); }
  function safeHref(url) { try { var u = new URL(url, location.href); return u.protocol === 'https:' || u.protocol === 'http:' ? esc(u.href) : '#'; } catch (e) { return '#'; } }

  /* ---------- «Что это?» ---------- */
  function openInfo(name, serviceId) {
    var d = INFO[name]; if (!d) return; var s = serviceId ? SVC.find(function(item){return item.id===serviceId;}) : find(name);
    var meta = s ? '<div class="sheet-meta"><span>' + fmt(s.price) + '</span>' + (s.min ? '<span>' + dur(s.min) + '</span>' : '') + '</div>' : '';
    var bookingUrl = s && s.cat === 'men' ? tgUrl('Здравствуйте! Хочу записаться: ' + name + '.') : s && s.master === 'julia' ? 'https://bumpix.net/463374' : CFG.book;
    openSheet('<h3 id="sheetTitle">' + esc(name) + '</h3>' + meta + '<h4>Что это</h4><p>' + esc(d.what) + '</p><h4>Откуда пошло</h4><p>' + esc(d.origin) + '</p><h4>Кому подходит</h4><p>' + esc(d.why) + '</p>' +
      '<div class="actions" style="margin-top:16px"><a class="btn" href="' + safeHref(bookingUrl) + '" target="_blank" rel="noopener">'+(s && s.cat === 'men' ? 'Написать Венере' : 'Записаться')+'</a><a class="btn btn-line" href="' + safeHref(tgUrl('Здравствуйте! Хочу записаться: ' + name.toLowerCase() + '.')) + '" target="_blank" rel="noopener">Спросить в Telegram</a></div>');
    goal('info_open');
  }
  document.addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('[data-info]'); if (b) { e.preventDefault(); var row=b.closest('[data-service-id]');openInfo(b.dataset.info,b.dataset.serviceId||(row&&row.dataset.serviceId)); } });

  /* ---------- Калькулятор: несколько услуг, комментарий и честный итог ---------- */
  var tryonState = { shape: 'миндаль', shade: 'вишня', touched: false };
  safe('calc', function () {
    var root = $('#calc'); if (!root) return;
    var mensManicurePage = root.dataset.mensManicure === 'true';
    var list = $('#svcList'), extrasBox = $('#extras'), tab = 'mani';
    var picks = {}, addons = {}, noteInput, copyButton, statusNode, message = '', master = 'venera';
    var masterSelect=document.createElement('div');masterSelect.className='booking-master-switch';masterSelect.setAttribute('role','group');masterSelect.setAttribute('aria-label','Выбор мастера');
    var masterLabel=document.createElement('strong');masterLabel.textContent='1. Выберите мастера';masterSelect.append(masterLabel);
    [['venera','Венера'],['julia','Юлия']].forEach(function(pair){var button=document.createElement('button');button.type='button';button.className='btn btn-line';button.textContent=pair[1];button.dataset.master=pair[0];button.addEventListener('click',function(){master=pair[0];picks={};addons={};tab='mani';render();});masterSelect.append(button);});
    if (!mensManicurePage) list.parentNode.insertBefore(masterSelect,list.parentNode.firstChild);
    var groups = {
      mani: [{title:'Маникюр',ids:['mani-gel','mani-plain']},{title:'Наращивание и коррекция',ids:['ext','corr-gel','corr-poly']}],
      pedi: [{title:'Педикюр',ids:['smart','pedi-toes','pedi-gel']}],
      podo: [{title:'Комплексный уход',ids:['podo-pedi']},{title:'Локальная обработка',ids:['ingrown','feet','toes','callus','system']},{title:'Консультация',ids:['consult']}],
      men: [{title:'Мужской уход',ids:['men-mani','men-pedi','men-both']}]
    };
    var sectionIntro = {mani:'Выберите один вариант маникюра. Наращивание и коррекция — альтернативы, а не дополнительные услуги.',
      pedi:'Выберите один вариант педикюра: процедуры различаются составом и не суммируются.',
      podo:'Выберите одну основную процедуру для предварительного расчёта. Совмещение обработок и необходимость дополнительных процедур согласовываются с мастером.',
      men:'Мужские услуги записывает Венера в Telegram. Выберите уход и добавьте пожелания; цену и длительность она подтвердит в переписке.'};
    var requested = new URLSearchParams(location.search).get('service');
    var initial = SVC.find(function(s){return s.id === requested && (!mensManicurePage || s.id === 'men-mani');});
    if (initial) {master=initial.master||'venera';tab=initial.cat;picks[tab]=initial.id;}
    else if (mensManicurePage) {tab='men';picks.men='men-mani';}
    else {picks.mani='mani-gel';}
    extrasBox.replaceChildren();
    (CFG.extras||[]).forEach(function(x){var button=document.createElement('button');button.type='button';button.className='extra';button.dataset.extra=x.id;button.setAttribute('aria-pressed','false');button.textContent=x.name+' · '+(x.from?'от ':'')+fmt(x.price);extrasBox.append(button);});
    var banner = document.createElement('div');banner.className='booking-selection booking-selection-v2';banner.setAttribute('role','status');
    var selectionText=document.createElement('strong');
    var reset=document.createElement('button');reset.type='button';reset.className='booking-reset';reset.textContent='Очистить';
    banner.append(selectionText,reset);list.parentNode.insertBefore(banner,list);
    var help=document.createElement('p');help.className='booking-context';help.id='bookingContext';list.parentNode.insertBefore(help,list);
    var wrap=document.createElement('div');wrap.className='booking-entry';
    var label=document.createElement('label');label.htmlFor='bookingComment';label.textContent='Пожелания к записи';
    noteInput=document.createElement('textarea');noteInput.id='bookingComment';noteInput.rows=2;noteInput.maxLength=500;
    noteInput.placeholder='Например: хочу маникюр и педикюр в один визит';
    var hint=document.createElement('p');hint.className='booking-hint';hint.textContent='Расчёт предварительный. Совместимость, длительность и итоговую стоимость подтверждает мастер.';
    copyButton=document.createElement('button');copyButton.type='button';copyButton.id='copyRequest';copyButton.className='btn btn-line';copyButton.textContent='Скопировать список';
    statusNode=document.createElement('span');statusNode.className='booking-hint';statusNode.setAttribute('role','status');
    wrap.append(label,noteInput,hint,copyButton,statusNode);
    var send=$('#sendReq');send.parentNode.insertBefore(wrap,send);
    var privateBox=document.createElement('div');privateBox.className='booking-private';
    var privateLabel=document.createElement('label');
    var privateInput=document.createElement('input');privateInput.type='checkbox';privateInput.id='privateVisit';
    privateInput.setAttribute('aria-describedby','privateVisitHelp privateVisitPrice');
    var privateTitle=document.createElement('span');privateTitle.textContent='Индивидуальный визит — без других клиентов';
    privateLabel.append(privateInput,privateTitle);
    var privateHelp=document.createElement('p');privateHelp.id='privateVisitHelp';privateHelp.className='booking-hint';
    privateHelp.textContent='Доплата по максимальной стоимости записей, которые перекрывает визит. Услуга, пересекающая его окончание, учитывается целиком. Расписание не синхронизируется; дату и отсутствие других клиентов подтверждает Венера.';
    var privatePrice=document.createElement('p');privatePrice.id='privateVisitPrice';privatePrice.className='booking-private-price';
    privatePrice.setAttribute('role','status');privateBox.append(privateLabel,privateHelp,privatePrice);
    if (mensManicurePage) list.parentNode.append(privateBox);
    var bookingLink=$('.summary > a.btn:not(#sendReq)',root);
    var preview=document.createElement('details');preview.className='booking-preview';
    var previewLabel=document.createElement('summary');previewLabel.textContent='Посмотреть текст заявки';
    var previewText=document.createElement('pre');previewText.id='requestPreview';preview.append(previewLabel,previewText);
    send.parentNode.insertBefore(preview,send);
    function available(){return SVC.filter(function(s){return (s.master||'venera')===master && (!mensManicurePage || s.id==='men-mani');});}
    function chosen(){return ['mani','pedi','men','podo'].map(function(cat){return available().find(function(s){return s.id===picks[cat];});}).filter(Boolean);}
    function canAddExtras(){return ['mani-gel','julia-gel','julia-hard-gel','julia-hard-poly','julia-ext'].indexOf(picks.mani)>=0;}
    function extras(){return canAddExtras() ? (CFG.extras||[]).filter(function(x){return (x.master||'venera')===master && !!addons[x.id];}) : [];}
    function clearConflicts(s){
      if(s.cat==='podo'){delete picks.mani;delete picks.pedi;delete picks.men;addons={};}
      else{
        delete picks.podo;
        if(s.cat==='mani'){if(picks.men==='men-mani'||picks.men==='men-both')delete picks.men;}
        if(s.cat==='pedi'){if(picks.men==='men-pedi'||picks.men==='men-both')delete picks.men;}
        if(s.cat==='men'){
          if(s.id==='men-both'){delete picks.mani;delete picks.pedi;addons={};}
          if(s.id==='men-mani'){delete picks.mani;addons={};}
          if(s.id==='men-pedi')delete picks.pedi;
        }
      }
    }
    function select(s){if(picks[s.cat]===s.id)delete picks[s.cat];else{clearConflicts(s);picks[s.cat]=s.id;}
      if(!canAddExtras())addons={};render();}
    function render(){
      list.replaceChildren();help.textContent=sectionIntro[tab];
      $$('.booking-master-switch button',root).forEach(function(btn){btn.setAttribute('aria-pressed',String(btn.dataset.master===master));});
      var displayGroups=master==='julia' ? {mani:[{title:'Маникюр, укрепление и наращивание',ids:['julia-mani','julia-gel','julia-hard-gel','julia-hard-poly','julia-ext','julia-remove']}],pedi:[{title:'Педикюр',ids:['julia-toes']}],podo:[],men:[]} : groups;
      (displayGroups[tab]||[]).forEach(function(g){
        var group=document.createElement('section');group.className='booking-group';
        var head=document.createElement('h3');head.className='booking-group-title';head.textContent=g.title;group.append(head);
        var choices=document.createElement('div');choices.className='booking-group-choices';
        g.ids.forEach(function(id){
          var s=available().find(function(item){return item.id===id;});if(!s)return;
          var row=document.createElement('div');row.className='svc svc-compact';row.dataset.selected=String(picks[s.cat]===s.id);
          var btn=document.createElement('button');btn.type='button';btn.className='nm';
          btn.setAttribute('aria-pressed',String(picks[s.cat]===s.id));btn.setAttribute('aria-label',s.name+', '+(s.price==null?'цена по запросу':fmt(s.price)));
          var dot=document.createElement('span');dot.className='dot';dot.setAttribute('aria-hidden','true');
          var title=document.createElement('span');title.className='booking-service-name';title.textContent=s.name;
          if(s.note){var detail=document.createElement('small');detail.textContent=s.note;title.append(detail);}
          btn.append(dot,title);btn.addEventListener('click',function(){select(s);});row.append(btn);
          if(INFO[s.name]){var info=document.createElement('button');info.type='button';info.className='info-btn';info.textContent='i';info.dataset.info=s.name;info.dataset.serviceId=s.id;info.setAttribute('aria-label','Подробнее: '+s.name);row.append(info);}
          var price=document.createElement('div');price.className='pr';price.textContent=s.price==null?'По запросу':fmt(s.price);
          if(s.min){var time=document.createElement('small');time.textContent=dur(s.min);price.append(time);}
          row.append(price);choices.append(row);
        });
        group.append(choices);list.append(group);
      });
      var extraVisible=tab==='mani'&&canAddExtras();extrasBox.hidden=!extraVisible;
      $$('.extra',root).forEach(function(el){var x=(CFG.extras||[]).find(function(e){return e.id===el.dataset.extra;});el.hidden=!x||(x.master||'venera')!==master;});
      $$('.extra',root).forEach(function(el){el.setAttribute('aria-pressed',String(extraVisible&&!!addons[el.dataset.extra]));});
      $$('.tab',root).forEach(function(el){el.hidden=!available().some(function(s){return s.cat===el.dataset.tab;});el.setAttribute('aria-selected',String(el.dataset.tab===tab));});
      recalc();
    }
    function selectedChip(id){var el=$('#'+id+' [aria-pressed="true"]');return el?el.textContent.trim().toLowerCase():'';}
    function recalc(){
      var sv=chosen(),add=extras(),unknown=sv.some(function(x){return x.price==null;});
      var price=sv.reduce(function(v,x){return v+(x.price||0);},0)+add.reduce(function(v,x){return v+x.price;},0);
      var timed=sv.concat(add);
      var mins=sv.length&&timed.every(function(x){return Number.isInteger(x.min)&&x.min>0;})?timed.reduce(function(v,x){return v+x.min;},0):null;
      var fromPrice=add.some(function(x){return x.from;});
      var approx=sv.some(function(x){return !!x.priceStatus;});
      var privateAllowed=mensManicurePage&&picks.men==='men-mani';
      privateBox.hidden=!privateAllowed;
      if(!privateAllowed)privateInput.checked=false;
      var privateQuote=null;
      if(privateAllowed&&!unknown&&mins!=null&&window.BookingPricing){
        privateQuote=window.BookingPricing.individualVisit(SVC,CFG.individualVisit,master,price,mins);
      }
      privatePrice.textContent=!sv.length?'Выберите услуги для расчёта доплаты':privateQuote ? 'Доплата: '+fmt(privateQuote.surcharge)+' за '+dur(mins) : 'Доплата по запросу: нужны полные цены и длительности всех выбранных услуг';
      var privateUnknown=privateInput.checked&&!privateQuote;
      var finalPrice=privateInput.checked&&privateQuote?privateQuote.total:price;
      approx=approx||(privateInput.checked&&privateQuote&&privateQuote.estimated);
      var pricePrefix=fromPrice?'от ':approx?'≈ ':'';
      var totalText=unknown||privateUnknown?'Стоимость уточняется':pricePrefix+fmt(finalPrice);
      bookingLink.hidden=!!picks.men||privateInput.checked||!sv.length;
      if(master==='julia'){bookingLink.href='https://bumpix.net/463374';bookingLink.target='_blank';bookingLink.rel='noopener';}
      else {bookingLink.href=CFG.book;bookingLink.target='_blank';bookingLink.rel='noopener';}
      statusNode.textContent='';
      var names=sv.map(function(x){return x.name;});
      selectionText.textContent=names.length?'В вашем списке: '+names.join(' + '):'Услуги не выбраны';
      reset.hidden=!names.length;
      var lines=$('#lines');lines.replaceChildren();
      function line(a,b){var li=document.createElement('li'),left=document.createElement('span'),right=document.createElement('span');left.textContent=a;right.textContent=b;li.append(left,right);lines.append(li);}
      sv.forEach(function(x){line(x.name,x.price==null?'По запросу':fmt(x.price));});
      add.forEach(function(x){line('Дополнительно: '+x.name,(x.from?'от ':'+')+fmt(x.price));});
      if(privateInput.checked&&sv.length)line('Индивидуальный визит',privateQuote?'+ '+fmt(privateQuote.surcharge):'По запросу');
      var total=$('#total'),time=$('#time');
      if(!sv.length){total.textContent='Выберите услугу';total.classList.add('ask');time.textContent='';message='';previewText.textContent='Выберите услуги';send.removeAttribute('href');send.setAttribute('aria-disabled','true');copyButton.disabled=true;return;}
      total.textContent=totalText;
      total.classList.toggle('ask',unknown||privateUnknown);
      time.textContent=mins==null?'Время уточняется':'≈ '+dur(mins);
      var parts=['Здравствуйте! Хочу записаться к '+(master==='julia'?'Юлии':'Венере')+' на следующие услуги:'];
      sv.forEach(function(x){parts.push('• '+x.name+' — '+(x.price==null?'по запросу':fmt(x.price)));});
      add.forEach(function(x){parts.push('• '+x.name+' — '+(x.from?'от ':'')+fmt(x.price));});
      if(privateInput.checked){
        parts.push('','Индивидуальный визит — без других клиентов.');
        parts.push('Стоимость выбранных услуг: '+(unknown?'по запросу':fmt(price)));
        parts.push('Доплата: '+(privateQuote?fmt(privateQuote.surcharge):'по запросу'));
        if(privateQuote)privateQuote.breakdown.forEach(function(x){parts.push('  '+x.label+': '+fmt(x.surcharge));});
        parts.push('Расчёт по максимальным перекрываемым записям, без проверки расписания.');
      }
      parts.push('','Предварительная стоимость: '+(unknown||privateUnknown?'уточняется':pricePrefix+fmt(finalPrice)));
      parts.push('Предварительное время: '+(mins==null?'уточняется':dur(mins)));
      if(picks.mani&&tryonState.touched)parts.push('Пожелания: форма '+tryonState.shape+', оттенок '+tryonState.shade+'.');
      var day=selectedChip('whenDay'),hour=selectedChip('whenTime');
      if(day||hour)parts.push('Удобное время: '+[day,hour].filter(Boolean).join(', ')+'.');
      if(noteInput.value.trim())parts.push('Комментарий: '+noteInput.value.trim());
      parts.push('','Подтвердите, пожалуйста, стоимость и время'+(privateInput.checked?', а также возможность визита без других клиентов':'')+'. Это заявка, время ещё не забронировано.');
      message=parts.join('\n');previewText.textContent=message;send.href=tgUrl(message);send.removeAttribute('aria-disabled');copyButton.disabled=false;
    }
    reset.addEventListener('click',function(){picks={};addons={};privateInput.checked=false;render();});
    $$('.tab',root).forEach(function(el){el.addEventListener('click',function(){tab=el.dataset.tab;render();});});
    $$('.extra',root).forEach(function(el){el.addEventListener('click',function(){if(!canAddExtras())return;addons[el.dataset.extra]=!addons[el.dataset.extra];render();});});
    ['whenDay','whenTime'].forEach(function(id){$$('#'+id+' .chip').forEach(function(el){el.addEventListener('click',function(){var on=el.getAttribute('aria-pressed')!=='true';$$('#'+id+' .chip').forEach(function(x){x.setAttribute('aria-pressed','false');});el.setAttribute('aria-pressed',String(on));recalc();});});});
    noteInput.addEventListener('input',recalc);document.addEventListener('tryon:change',recalc);
    privateInput.addEventListener('change',recalc);
    copyButton.addEventListener('click',function(){if(!message)return;if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(message).then(function(){statusNode.textContent='Список скопирован';}).catch(function(){statusNode.textContent='Не удалось скопировать';});else statusNode.textContent='Скопируйте список через кнопку отправки';});
    send.addEventListener('click',function(e){if(!message)e.preventDefault();});
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
      openSheet('<h3 id="sheetTitle">Подберём форму и оттенок</h3>' + Q.map(function (q) { return '<div class="q-step"><div class="ctl-label">' + q[1] + '</div><div class="chips" data-q="' + q[0] + '">' + q[2].map(function (o) { return '<button class="chip" type="button" data-v="' + o[0] + '" aria-pressed="false">' + o[1] + '</button>'; }).join('') + '</div></div>'; }).join('') + '<div id="qRes" hidden><p>Попробуйте: <b id="qPick"></b></p><p class="muted" id="qWhy"></p><button class="btn" type="button" id="qShow">Применить к заявке</button></div>');
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
      sheetBody.addEventListener('click', function (e) { if (e.target.id === 'qShow' && pick) { window.__tryon(pick[0], pick[1]); closeSheet(); goal('quiz_done'); var st = $('.tryon'); if (st) st.scrollIntoView({ behavior: 'smooth', block: 'center' }); say('Форма и цвет добавлены к заявке'); } });
    });
  });

  /* ---------- Подология ---------- */
  safe('podo', function () {
    var foot = $('#foot'); if (!foot) return;
    var MAP = { ingrown: ['Обработка вросшего ногтя', 'Если ноготь врастает, есть боль или воспаление, сначала требуется медицинская оценка. Возможность последующего ухода обсудите со специалистом.'],
      toes: ['Обработка пальчиков', 'Кожа вокруг ногтей и между пальцами, утолщённые ногти.'],
      callus: ['Обработка мозоли', 'Уход за участками огрубевшей кожи. При боли, повреждении кожи или воспалении сначала обратитесь к врачу.'],
      feet: ['Обработка стоп', 'Косметический уход за огрубевшей кожей. Болезненные или глубокие трещины требуют врачебного осмотра.'],
      system: ['Коррекционная система', 'Метод коррекции ногтевой пластины. Возможность и правомерность услуги уточняйте у специалиста.'],
      consult: ['Консультация', 'Мастер расскажет о доступном косметическом уходе. Диагностика и лечение заболеваний требуют обращения к врачу.'] };
    var curName = MAP.ingrown[0];
    function show(k) {
      var m = MAP[k]; if (!m) return; var s = find(m[0]); curName = m[0];
      $('#podoTitle').textContent = m[0]; $('#podoText').textContent = m[1];
      var needsDoctor = k === 'ingrown' || k === 'system';
      $('#podoPrice').textContent = needsDoctor ? 'Уточняется' : (s ? fmt(s.price) : '');
      $('#podoTime').textContent = needsDoctor ? 'после консультации' : (s ? dur(s.min) : '');
      var book = $('.podo-card .actions a.btn');
      if (book) book.hidden = needsDoctor;
      $$('.hot', foot).forEach(function (h) { h.setAttribute('aria-pressed', String(h.dataset.podo === k)); });
    }
    $$('.hot', foot).forEach(function (h) { h.addEventListener('click', function () { show(h.dataset.podo); }); });
    $('#podoMore').addEventListener('click', function () { openInfo(curName); });
    $$('#footQuiz .chip').forEach(function (b) {
      b.addEventListener('click', function () {
        $$('#footQuiz .chip').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
        var ans = $('#footAns'), f = b.dataset.f;
        if (f === 'doctor') { ans.className = 'ans red'; ans.textContent = 'Сильная боль, гной или отёк — повод сначала показаться врачу. После лечения мастер поможет с уходом.'; return; }
        show(f); var s = find(MAP[f][0]); ans.className = 'ans'; ans.textContent = 'Вы выбрали тему «' + MAP[f][0] + '». Описание и ориентир из прайса показаны выше. При жалобах на боль или воспаление — к врачу.'; goal('foot_quiz');
      });
    });
    show('feet');
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
      var box = $('#giftOpts'); box.replaceChildren();
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


  /* ---------- Портфолио: реальные фотографии, фильтры, клавиатура, свайпы ---------- */
  safe('portfolio', function () {
    var items = json('portfolio-data');
    var dialog = $('#portfolioViewer'), img = $('#folioImage');
    var cards = Array.prototype.slice.call(document.querySelectorAll('[data-work-index]'));
    var filterButtons = Array.prototype.slice.call(document.querySelectorAll('[data-work-filter]'));
    if (!dialog || !img || !Array.isArray(items) || !items.length || !cards.length) return;
    var counter = $('#folioCounter'), caption = $('#folioCaption');
    var trigger = null, current = -1, swipeStart = null, sourceTicket = 0;
    var visibleIds = function () {
      return cards.filter(function (card) { return !card.hidden; })
        .map(function (card) { return Number(card.dataset.workIndex); });
    };
    function loadAt(index) {
      var visible = visibleIds(), record = items[index];
      if (!record || visible.indexOf(index) < 0) return;
      current = index;
      img.classList.add('folio-loading');
      var ticket = ++sourceTicket;
      var loader = new Image();
      loader.onload = function () {
        if (ticket !== sourceTicket) return;
        img.src = record.full; img.alt = 'Фото из галереи ВенераNAILART: ' + record.title;
        img.classList.remove('folio-loading');
      };
      loader.onerror = function () {
        if (ticket !== sourceTicket) return;
        img.src = record.thumb; img.alt = 'Фото из галереи ВенераNAILART: ' + record.title;
        img.classList.remove('folio-loading');
      };
      loader.src = record.full;
      var pos = visible.indexOf(index);
      counter.textContent = (pos + 1) + ' / ' + visible.length;
      caption.textContent = record.title;
      if (visible.length > 1) {
        var next = items[visible[(pos + 1) % visible.length]];
        if (next) { var pre = new Image(); pre.src = next.full; }
      }
      $('.folio-prev', dialog).hidden = visible.length < 2;
      $('.folio-next', dialog).hidden = visible.length < 2;
    }
    function move(by) {
      var visible = visibleIds(), pos = visible.indexOf(current);
      if (pos < 0 || visible.length < 2) return;
      loadAt(visible[(pos + by + visible.length) % visible.length]);
    }
    function openViewer(index, el) {
      var record = items[index]; if (!record || !dialog.showModal) return;
      trigger = el;
      document.body.classList.add('folio-open');
      dialog.showModal();
      loadAt(index);
      $('.folio-close', dialog).focus();
    }
    cards.forEach(function (el) {
      el.addEventListener('click', function () {
        openViewer(Number(el.dataset.workIndex), el);
      });
    });
    $('.folio-close', dialog).addEventListener('click', function () { dialog.close(); });
    $('.folio-prev', dialog).addEventListener('click', function () { move(-1); });
    $('.folio-next', dialog).addEventListener('click', function () { move(1); });
    dialog.addEventListener('click', function (e) { if (e.target === dialog) dialog.close(); });
    dialog.addEventListener('close', function () {
      sourceTicket++;
      document.body.classList.remove('folio-open');
      if (trigger && trigger.isConnected) trigger.focus();
    });
    document.addEventListener('keydown', function (e) {
      if (!dialog.open) return;
      if (e.key === 'ArrowLeft') { e.preventDefault(); move(-1); }
      if (e.key === 'ArrowRight') { e.preventDefault(); move(1); }
    });
    var view = $('.folio-visual', dialog);
    view.addEventListener('touchstart', function (e) {
      if (e.touches.length !== 1) { swipeStart = null; return; }
      swipeStart = {x:e.touches[0].clientX, y:e.touches[0].clientY};
    }, {passive:true});
    view.addEventListener('touchend', function (e) {
      if (!swipeStart || !e.changedTouches.length) return;
      var dx=e.changedTouches[0].clientX-swipeStart.x;
      var dy=e.changedTouches[0].clientY-swipeStart.y;
      swipeStart=null;
      if (Math.abs(dx) > 48 && Math.abs(dx) > Math.abs(dy)*1.25) move(dx > 0 ? -1 : 1);
    }, {passive:true});
    filterButtons.forEach(function (b) {
      b.addEventListener('click', function () {
        var category=b.dataset.workFilter;
        filterButtons.forEach(function (other) {
          other.setAttribute('aria-pressed', String(other === b));
        });
        cards.forEach(function (card) {
          card.hidden = category !== 'all' && card.dataset.workKind !== category;
        });
      });
    });
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
