/* VisionStock — interfaz: alertas SweetAlert2, animaciones y componentes dinámicos */
(function () {
  'use strict';

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hasSwal = typeof window.Swal !== 'undefined';

  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $$(sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); }
  function norm(s) { return (s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, ''); }

  /* ------------------------------------------------------------------
     1. SweetAlert2: mensajes de Django, confirmaciones y estados de carga
     ------------------------------------------------------------------ */
  var cls = { popup: 'vs-popup', confirmButton: 'vs-confirm', cancelButton: 'vs-cancel' };

  if (hasSwal) {
    var toast = Swal.mixin({
      toast: true, position: 'top-end', showConfirmButton: false,
      timer: 3800, timerProgressBar: true, customClass: { popup: 'vs-toast' }
    });

    $$('[data-flash]').forEach(function (el, i) {
      var tipo = el.getAttribute('data-flash');
      if (['success', 'error', 'warning', 'info'].indexOf(tipo) === -1) tipo = 'info';
      var texto = el.textContent.trim();
      // Los errores y avisos largos se muestran como diálogo para que no se pasen por alto
      if (tipo === 'error' || texto.length > 90) {
        Swal.fire({ icon: tipo, text: texto, confirmButtonText: 'Entendido', customClass: cls });
      } else {
        setTimeout(function () { toast.fire({ icon: tipo, title: texto }); }, i * 250);
      }
    });
  }

  // Confirmación antes de enviar: <form data-confirm="..." data-confirm-title="...">
  document.addEventListener('submit', function (e) {
    var form = e.target;
    var msg = form.getAttribute('data-confirm');
    if (!msg || form.dataset.confirmed) return;
    e.preventDefault();
    var peligro = form.hasAttribute('data-danger');
    if (!hasSwal) {
      if (window.confirm(msg)) { form.dataset.confirmed = '1'; form.submit(); }
      return;
    }
    Swal.fire({
      title: form.getAttribute('data-confirm-title') || '¿Estás seguro?',
      text: msg,
      icon: peligro ? 'warning' : 'question',
      showCancelButton: true,
      confirmButtonText: form.getAttribute('data-confirm-button') || 'Confirmar',
      cancelButtonText: 'Cancelar',
      reverseButtons: true,
      focusCancel: peligro,
      customClass: { popup: cls.popup, confirmButton: cls.confirmButton, cancelButton: cls.cancelButton }
    }).then(function (r) {
      if (r.isConfirmed) { form.dataset.confirmed = '1'; form.submit(); }
    });
  });

  // Estado de carga en formularios lentos (análisis de imagen)
  $$('form[data-loading]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (e.defaultPrevented || !hasSwal) return;
      Swal.fire({
        title: form.getAttribute('data-loading'),
        text: 'Esto puede tardar unos segundos.',
        allowOutsideClick: false, allowEscapeKey: false, showConfirmButton: false,
        customClass: { popup: cls.popup },
        didOpen: function () { Swal.showLoading(); }
      });
    });
  });

  // Botón de envío con estado "ocupado" (evita dobles envíos)
  document.addEventListener('submit', function (e) {
    if (e.defaultPrevented) return;
    var btn = $('button[type=submit].btn:not(.small)', e.target);
    if (!btn) return;
    setTimeout(function () { btn.classList.add('is-busy'); }, 0);
  });
  window.addEventListener('pageshow', function (e) {
    if (!e.persisted) return;
    $$('.is-busy').forEach(function (b) { b.classList.remove('is-busy'); });
    var m = $('main'); if (m) m.classList.remove('leaving');
  });

  /* ------------------------------------------------------------------
     2. Navegación: enlace activo, píldora con rebote, ajuste al espacio
        disponible y barra dinámica (sombra, progreso, ocultar al bajar)
     ------------------------------------------------------------------ */
  var path = location.pathname;
  var mejor = null;
  $$('.nav-link').forEach(function (a) {
    var href = a.getAttribute('href');
    var coincide = href === '/' ? path === '/' : path.indexOf(href) === 0;
    if (coincide && (!mejor || href.length > mejor.getAttribute('href').length)) mejor = a;
  });
  if (mejor) mejor.classList.add('active');

  var nav = $('.nav');
  var navLinks = $('.nav-links');
  if (navLinks) {
    $$('.nav-link', navLinks).forEach(function (a, i) { a.style.setProperty('--i', i); });
    var pill = document.createElement('span');
    pill.className = 'nav-pill';
    navLinks.appendChild(pill);
    var moveTo = function (a) {
      if (!a) { pill.style.opacity = 0; return; }
      pill.style.opacity = 1;
      pill.style.width = a.offsetWidth + 'px';
      pill.style.transform = 'translateX(' + a.offsetLeft + 'px)';
    };
    var desborda = function () { return navLinks.scrollWidth > navLinks.clientWidth + 1; };
    // Si las secciones no caben: 1) oculta el nombre de usuario, 2) pasa el menú a otra fila
    var ajustar = function () {
      if (!nav) return;
      nav.classList.remove('no-who', 'wrap');
      if (desborda()) nav.classList.add('no-who');
      if (desborda()) nav.classList.add('wrap');
      moveTo(mejor);
    };
    var pend = false;
    var reajustar = function () {
      if (pend) return;
      pend = true;
      requestAnimationFrame(function () { pend = false; ajustar(); });
    };
    ajustar();
    requestAnimationFrame(function () { requestAnimationFrame(function () { pill.classList.add('ready'); }); });
    $$('.nav-link', navLinks).forEach(function (a) {
      a.addEventListener('mouseenter', function () { moveTo(a); });
      a.addEventListener('focus', function () { moveTo(a); });
    });
    navLinks.addEventListener('mouseleave', function () { moveTo(mejor); });
    window.addEventListener('resize', reajustar);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(reajustar);
    if (mejor && desborda()) navLinks.scrollLeft = Math.max(0, mejor.offsetLeft - 24);
  }

  if (nav) {
    var bar = document.createElement('span');
    bar.className = 'nav-progress';
    nav.appendChild(bar);
    var lastY = window.scrollY, ticking = false;
    var onScroll = function () {
      var y = window.scrollY;
      var max = document.documentElement.scrollHeight - window.innerHeight;
      nav.classList.toggle('scrolled', y > 8);
      bar.style.transform = 'scaleX(' + (max > 0 ? Math.min(1, Math.max(0, y / max)) : 0) + ')';
      var d = y - lastY;
      if (!reduce && Math.abs(d) > 6) {
        if (d > 0 && y > 140 && !nav.contains(document.activeElement)) nav.classList.add('hide');
        else if (d < 0) nav.classList.remove('hide');
        lastY = y;
      }
      if (y <= 8) nav.classList.remove('hide');
      ticking = false;
    };
    window.addEventListener('scroll', function () {
      if (!ticking) { ticking = true; requestAnimationFrame(onScroll); }
    }, { passive: true });
    nav.addEventListener('focusin', function () { nav.classList.remove('hide'); });
    onScroll();
  }

  /* ------------------------------------------------------------------
     3. Medidores y contadores (se activan al revelarse el bloque)
     ------------------------------------------------------------------ */
  function fillMeter(m) {
    if (m.dataset.filled) return;
    m.dataset.filled = '1';
    var v = parseFloat(m.dataset.value) || 0;
    var mark = parseFloat(m.dataset.mark) || 0;
    var head = parseFloat(m.dataset.headroom) || 1;
    var scale = Math.max(v, mark * head, 1);
    var bar = m.firstElementChild;
    var tick = $('.meter-mark', m);
    if (tick && mark > 0) {
      tick.style.left = (mark / scale * 100) + '%';
      tick.classList.add('on');
    }
    requestAnimationFrame(function () { bar.style.width = Math.min(100, v / scale * 100) + '%'; });
  }

  function countUp(el, delay) {
    if (el.dataset.counted) return;
    el.dataset.counted = '1';
    var txt = el.textContent.trim();
    var m = /^(\D*)(\d+)(\D*)$/.exec(txt);
    if (!m || reduce) return;
    var target = parseInt(m[2], 10);
    if (target < 1 || target > 9999999) return;
    var dur = 900;
    var t0 = null;
    el.textContent = m[1] + '0' + m[3];
    function tick(ts) {
      if (t0 === null) t0 = ts;
      var p = Math.min(1, (ts - t0) / dur);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = m[1] + Math.round(target * eased) + m[3];
      if (p < 1) requestAnimationFrame(tick); else el.textContent = txt;
    }
    setTimeout(function () { requestAnimationFrame(tick); }, delay + 150);
  }

  function activate(block, delay) {
    $$('.meter', block).forEach(function (m) { setTimeout(function () { fillMeter(m); }, delay + 250); });
    if (block.matches && block.matches('.meter')) fillMeter(block);
    $$('.stat .value', block).forEach(function (v) { countUp(v, delay); });
    $$('.ci-stats b', block).forEach(function (v) { countUp(v, delay + 200); });
    if (block.matches && block.matches('.stat')) { var v = $('.value', block); if (v) countUp(v, delay); }
  }

  /* ------------------------------------------------------------------
     4. Entrada en cascada: fade-in + slide-up escalonado
     ------------------------------------------------------------------ */
  var REVEAL = [
    '.back', '.page-head', '.search', '.segmented',
    '.grid > *', '.mini-stats > *', '.split-media', '.split-data > .card',
    'main > .card', 'main > form > .card', 'main > form > .form-actions', 'main > .form-actions',
    '.card-body > form > .field', '.card-body > form > .row2', '.card-body > form > .btn',
    '.card-body > form > .form-actions', '.card-body > form > .help',
    '.auth-card > *', '.perm-section', '.carousel-item',
    '.list > li', 'tbody > tr', '.thumbs > .thumb'
  ].join(',');

  var targets = $$(REVEAL);

  if (!('IntersectionObserver' in window) || reduce) {
    targets.forEach(function (el) { el.classList.add('in'); });
    $$('.meter').forEach(fillMeter);
    $$('.stat .value').forEach(function (v) { v.dataset.counted = '1'; });
  } else {
    targets.forEach(function (el) { el.classList.add('reveal'); });
    var io = new IntersectionObserver(function (entries) {
      var vis = entries.filter(function (en) { return en.isIntersecting; }).sort(function (a, b) {
        return (a.target.compareDocumentPosition(b.target) & 4) ? -1 : 1;
      });
      vis.forEach(function (en, i) {
        var el = en.target;
        var delay = Math.min(i, 16) * 55;
        el.style.setProperty('--d', delay + 'ms');
        el.classList.add('in');
        io.unobserve(el);
        activate(el, delay);
      });
    }, { threshold: 0.06, rootMargin: '0px 0px -3% 0px' });
    targets.forEach(function (el) { io.observe(el); });
    // Red de seguridad: medidores que no estén dentro de un bloque animado
    setTimeout(function () { $$('.meter').forEach(fillMeter); }, 2500);
  }

  /* ------------------------------------------------------------------
     5. Carrusel: flechas de cristal, puntos de página, teclado y arrastre
     ------------------------------------------------------------------ */
  $$('.carousel').forEach(function (car) {
    var items = $$('.carousel-item', car);
    if (!items.length) return;
    var wrap = document.createElement('div');
    wrap.className = 'carousel-wrap';
    car.parentNode.insertBefore(wrap, car);
    wrap.appendChild(car);

    function chevron(dir) {
      return '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="' +
        (dir === 'prev' ? 'M15 5l-7 7 7 7' : 'M9 5l7 7-7 7') + '"/></svg>';
    }
    function mk(dir, label) {
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'carousel-btn ' + dir + ' off'; b.setAttribute('aria-label', label);
      b.innerHTML = chevron(dir);
      wrap.appendChild(b);
      return b;
    }
    var prev = mk('prev', 'Anterior');
    var next = mk('next', 'Siguiente');

    var dots = document.createElement('div');
    dots.className = 'carousel-dots';
    items.forEach(function (it, i) {
      var d = document.createElement('button');
      d.type = 'button'; d.className = 'dot'; d.setAttribute('aria-label', 'Ir al elemento ' + (i + 1));
      d.addEventListener('click', function () { scrollToItem(i); });
      dots.appendChild(d);
    });
    wrap.appendChild(dots);

    var behavior = reduce ? 'auto' : 'smooth';
    function offsetOf(i) { return items[i].offsetLeft - items[0].offsetLeft; }
    function scrollToItem(i) { car.scrollTo({ left: offsetOf(i), behavior: behavior }); }
    function page(dir) {
      var step = items.length > 1 ? offsetOf(1) : car.clientWidth;
      var n = Math.max(1, Math.floor(car.clientWidth / step));
      car.scrollBy({ left: dir * step * n, behavior: behavior });
    }

    function update() {
      var max = car.scrollWidth - car.clientWidth;
      var x = car.scrollLeft;
      var atStart = x <= 6, atEnd = x >= max - 6;
      prev.classList.toggle('off', atStart);
      next.classList.toggle('off', atEnd);
      prev.tabIndex = atStart ? -1 : 0;
      next.tabIndex = atEnd ? -1 : 0;
      dots.hidden = max <= 2;
      car.style.setProperty('--fl', atStart ? '0px' : '36px');
      car.style.setProperty('--fr', atEnd ? '0px' : '36px');
      var idx = 0, best = Infinity;
      items.forEach(function (it, i) {
        var d = Math.abs(offsetOf(i) - x);
        if (d < best) { best = d; idx = i; }
      });
      if (atEnd) idx = items.length - 1;
      Array.prototype.forEach.call(dots.children, function (d, i) {
        d.classList.toggle('on', i === idx);
        if (i === idx) d.setAttribute('aria-current', 'true'); else d.removeAttribute('aria-current');
      });
    }
    prev.addEventListener('click', function () { page(-1); });
    next.addEventListener('click', function () { page(1); });
    car.addEventListener('scroll', function () { requestAnimationFrame(update); }, { passive: true });
    car.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { e.preventDefault(); page(1); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); page(-1); }
    });
    window.addEventListener('resize', update);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(update);
    update();

    // Arrastrar con el ratón
    var down = false, moved = false, startX = 0, startLeft = 0;
    car.addEventListener('mousedown', function (e) {
      if (e.button !== 0) return;
      down = true; moved = false; startX = e.pageX; startLeft = car.scrollLeft;
    });
    window.addEventListener('mousemove', function (e) {
      if (!down) return;
      var dx = e.pageX - startX;
      if (Math.abs(dx) > 5) { moved = true; car.classList.add('dragging'); }
      if (moved) car.scrollLeft = startLeft - dx;
    });
    window.addEventListener('mouseup', function () {
      if (!down) return;
      down = false;
      setTimeout(function () { car.classList.remove('dragging'); }, 0);
    });
    car.addEventListener('click', function (e) { if (moved) { e.preventDefault(); e.stopPropagation(); moved = false; } }, true);
    car.addEventListener('dragstart', function (e) { e.preventDefault(); });
  });

  /* ------------------------------------------------------------------
     6. Lightbox para miniaturas y vistas previas
     ------------------------------------------------------------------ */
  var lb = null, lbImgs = [], lbIdx = 0;
  function buildLightbox() {
    lb = document.createElement('div');
    lb.className = 'lightbox';
    lb.setAttribute('role', 'dialog');
    lb.setAttribute('aria-modal', 'true');
    lb.innerHTML = '<img alt=""><button type="button" class="lb-btn lb-close" aria-label="Cerrar">×</button>' +
      '<button type="button" class="lb-btn lb-prev" aria-label="Anterior">‹</button>' +
      '<button type="button" class="lb-btn lb-next" aria-label="Siguiente">›</button><div class="lb-count"></div>';
    document.body.appendChild(lb);
    lb.addEventListener('click', function (e) {
      if (e.target === lb || e.target.classList.contains('lb-close')) closeLb();
      else if (e.target.classList.contains('lb-prev')) stepLb(-1);
      else if (e.target.classList.contains('lb-next')) stepLb(1);
    });
  }
  function showLb() {
    var img = $('img', lb);
    img.src = lbImgs[lbIdx].src;
    img.alt = lbImgs[lbIdx].alt || '';
    $('.lb-count', lb).textContent = lbImgs.length > 1 ? (lbIdx + 1) + ' / ' + lbImgs.length : '';
    $('.lb-prev', lb).hidden = $('.lb-next', lb).hidden = lbImgs.length < 2;
  }
  function openLb(list, idx) {
    if (!lb) buildLightbox();
    lbImgs = list; lbIdx = idx; showLb();
    requestAnimationFrame(function () { lb.classList.add('open'); });
  }
  function closeLb() { if (lb) lb.classList.remove('open'); }
  function stepLb(d) { lbIdx = (lbIdx + d + lbImgs.length) % lbImgs.length; showLb(); }

  document.addEventListener('click', function (e) {
    var img = e.target.closest ? e.target.closest('.thumbs img, img.preview') : null;
    if (!img) return;
    var group = img.closest('.thumbs');
    var list = group ? $$('img', group) : [img];
    openLb(list, Math.max(0, list.indexOf(img)));
  });
  document.addEventListener('keydown', function (e) {
    if (!lb || !lb.classList.contains('open')) return;
    if (e.key === 'Escape') closeLb();
    else if (e.key === 'ArrowLeft') stepLb(-1);
    else if (e.key === 'ArrowRight') stepLb(1);
  });

  /* ------------------------------------------------------------------
     7. Filtro en vivo: <input data-live-filter="#id-de-la-tabla-o-lista">
     ------------------------------------------------------------------ */
  $$('input[data-live-filter]').forEach(function (input) {
    var target = $(input.getAttribute('data-live-filter'));
    if (!target) return;
    var emptyMsg = $('[data-filter-empty]', target.parentNode) || $('[data-filter-empty]');
    var rows = $$('tbody tr, .list > li', target).filter(function (r) { return !r.querySelector('td[colspan]'); });
    var cache = rows.map(function (r) { return norm(r.textContent); });
    input.addEventListener('input', function () {
      var q = norm(input.value.trim());
      var shown = 0;
      rows.forEach(function (r, i) {
        var ok = !q || cache[i].indexOf(q) !== -1;
        r.hidden = !ok;
        if (ok) shown++;
      });
      if (emptyMsg) emptyMsg.hidden = !(q && shown === 0);
    });
  });

  /* ------------------------------------------------------------------
     8. Permisos: marcar/quitar todo por sección y contador
     ------------------------------------------------------------------ */
  $$('.perm-section').forEach(function (sec) {
    var boxes = $$('input[type=checkbox]', sec);
    var count = $('[data-perm-count]', sec);
    var toggle = $('[data-perm-toggle]', sec);
    function refresh() {
      var on = boxes.filter(function (b) { return b.checked; }).length;
      if (count) count.textContent = on + ' de ' + boxes.length;
      if (toggle) toggle.textContent = on === boxes.length ? 'Quitar todo' : 'Marcar todo';
    }
    boxes.forEach(function (b) { b.addEventListener('change', refresh); });
    if (toggle) toggle.addEventListener('click', function () {
      var todos = boxes.every(function (b) { return b.checked; });
      boxes.forEach(function (b) { b.checked = !todos; });
      refresh();
    });
    refresh();
  });

  /* ------------------------------------------------------------------
     9. Contraseñas: botón para mostrar/ocultar
     ------------------------------------------------------------------ */
  var EYE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>';
  var EYE_OFF = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 3l18 18M10.6 5.1A10.7 10.7 0 0 1 12 5c6.4 0 10 7 10 7a17 17 0 0 1-3.2 4.1M6.6 6.6A16.6 16.6 0 0 0 2 12s3.6 7 10 7a10.5 10.5 0 0 0 4.4-.9M9.9 9.9a3 3 0 0 0 4.2 4.2"/></svg>';
  $$('.auth-card input[type=password]').forEach(function (input) {
    var hadFocus = document.activeElement === input;
    var wrap = document.createElement('div');
    wrap.className = 'pw';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    var btn = document.createElement('button');
    btn.type = 'button'; btn.className = 'pw-toggle'; btn.setAttribute('aria-label', 'Mostrar contraseña'); btn.innerHTML = EYE;
    wrap.appendChild(btn);
    btn.addEventListener('click', function () {
      var ver = input.type === 'password';
      input.type = ver ? 'text' : 'password';
      btn.innerHTML = ver ? EYE_OFF : EYE;
      btn.setAttribute('aria-label', ver ? 'Ocultar contraseña' : 'Mostrar contraseña');
    });
    if (hadFocus) input.focus();
  });

  /* ------------------------------------------------------------------
     10. Zona de arrastre para subir imágenes
     ------------------------------------------------------------------ */
  $$('.dropzone').forEach(function (zone) {
    var input = $('input[type=file]', zone);
    var label = $('[data-filename]', zone);
    var preview = document.querySelector(zone.getAttribute('data-preview') || '#none');
    function actualizar() {
      var files = input.files;
      if (!files.length) return;
      if (label) label.textContent = files.length === 1 ? files[0].name : files.length + ' imágenes seleccionadas';
      if (preview && files[0]) {
        preview.hidden = true;
        preview.src = URL.createObjectURL(files[0]);
        void preview.offsetWidth;
        preview.hidden = false;
      }
    }
    input.addEventListener('change', actualizar);
    ['dragenter', 'dragover'].forEach(function (ev) {
      zone.addEventListener(ev, function (e) { e.preventDefault(); zone.classList.add('drag'); });
    });
    ['dragleave', 'drop'].forEach(function (ev) {
      zone.addEventListener(ev, function (e) { e.preventDefault(); zone.classList.remove('drag'); });
    });
    zone.addEventListener('drop', function (e) {
      if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; actualizar(); }
    });
  });

  /* ------------------------------------------------------------------
     11. Transición de salida entre páginas
     ------------------------------------------------------------------ */
  document.addEventListener('click', function (e) {
    var a = e.target.closest ? e.target.closest('a[href]') : null;
    if (!a || reduce || e.defaultPrevented || e.button !== 0) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (a.target && a.target !== '_self') return;
    if (a.hasAttribute('download') || a.hasAttribute('data-no-leave')) return;
    var href = a.getAttribute('href');
    if (!href || href.charAt(0) === '#' || /^(javascript|mailto|tel):/i.test(href)) return;
    if (a.origin !== location.origin) return;
    var main = $('main');
    if (!main) return;
    e.preventDefault();
    main.classList.add('leaving');
    setTimeout(function () { location.href = a.href; }, 150);
    setTimeout(function () { main.classList.remove('leaving'); }, 2500);
  });
})();