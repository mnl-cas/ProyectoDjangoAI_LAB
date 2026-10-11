/* VisionStock — alertas SweetAlert2 y pequeños comportamientos de interfaz */
(function () {
  'use strict';

  var cls = {
    popup: 'vs-popup',
    confirmButton: 'vs-confirm',
    cancelButton: 'vs-cancel'
  };

  // Mensajes de Django -> toasts
  var toast = Swal.mixin({
    toast: true,
    position: 'top-end',
    showConfirmButton: false,
    timer: 3800,
    timerProgressBar: true,
    customClass: { popup: 'vs-toast' }
  });

  document.querySelectorAll('[data-flash]').forEach(function (el, i) {
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

  // Confirmación antes de enviar formularios: <form data-confirm="..." data-confirm-title="...">
  document.addEventListener('submit', function (e) {
    var form = e.target;
    var msg = form.getAttribute('data-confirm');
    if (!msg || form.dataset.confirmed) return;
    e.preventDefault();
    var peligro = form.hasAttribute('data-danger');
    Swal.fire({
      title: form.getAttribute('data-confirm-title') || '¿Estás seguro?',
      text: msg,
      icon: peligro ? 'warning' : 'question',
      showCancelButton: true,
      confirmButtonText: form.getAttribute('data-confirm-button') || 'Confirmar',
      cancelButtonText: 'Cancelar',
      reverseButtons: true,
      focusCancel: peligro,
      customClass: {
        popup: cls.popup,
        confirmButton: 'vs-confirm' + (peligro ? ' vs-danger' : ''),
        cancelButton: cls.cancelButton
      }
    }).then(function (r) {
      if (r.isConfirmed) {
        form.dataset.confirmed = '1';
        form.submit();
      }
    });
  });

  // Estado de carga en formularios lentos (análisis de imagen)
  document.querySelectorAll('form[data-loading]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (e.defaultPrevented) return;
      Swal.fire({
        title: form.getAttribute('data-loading'),
        text: 'Esto puede tardar unos segundos.',
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        customClass: { popup: cls.popup },
        didOpen: function () { Swal.showLoading(); }
      });
    });
  });

  // Enlace activo en la barra de navegación
  var path = location.pathname;
  var mejor = null;
  document.querySelectorAll('.nav-link').forEach(function (a) {
    var href = a.getAttribute('href');
    var coincide = href === '/' ? path === '/' : path.indexOf(href) === 0;
    if (coincide && (!mejor || href.length > mejor.getAttribute('href').length)) mejor = a;
  });
  if (mejor) mejor.classList.add('active');

  // Zona de arrastre para subir imágenes
  document.querySelectorAll('.dropzone').forEach(function (zone) {
    var input = zone.querySelector('input[type=file]');
    var label = zone.querySelector('[data-filename]');
    var preview = document.querySelector(zone.getAttribute('data-preview') || '#none');
    function actualizar() {
      var files = input.files;
      if (!files.length) return;
      if (label) label.textContent = files.length === 1 ? files[0].name : files.length + ' imágenes seleccionadas';
      if (preview && files[0]) {
        preview.src = URL.createObjectURL(files[0]);
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
})();
