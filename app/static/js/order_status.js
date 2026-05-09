/* SSE-подписка на обновления заказа + PWA install prompt.
   Подключается только на странице статуса заказа.
   Order ID берётся из data-order-id на элементе #order-status-root. */

(function () {
  var root = document.getElementById('order-status-root');
  if (!root) return;
  var THIS_ORDER_ID = parseInt(root.dataset.orderId, 10);
  if (!THIS_ORDER_ID) return;

  var STATUS_LABELS = {
    'pending':   'Заказ ожидает',
    'confirmed': 'Заказ принят в работу',
    'ready':     'Заказ готов, можно забирать!',
    'completed': 'Заказ выдан',
    'cancelled': 'Заказ отменён',
    'expired':   'Заказ не забран вовремя',
  };

  var es = new EventSource('/sse/my-orders');
  es.addEventListener('my-order-update', function (e) {
    try {
      var data = JSON.parse(e.data);
      if (data.order_id !== THIS_ORDER_ID) return;

      // Перерисовываем шкалу статуса (партиал)
      fetch('/orders/' + THIS_ORDER_ID + '/status-block', { credentials: 'same-origin' })
        .then(function (r) { return r.text(); })
        .then(function (html) {
          var wrap = document.getElementById('status-block-wrap');
          if (wrap) wrap.innerHTML = html;
        });

      // Тост (только при смене кухонного статуса)
      if (!data.status) return;
      var toastEl = document.getElementById('order-toast');
      var bodyEl  = document.getElementById('order-toast-body');
      if (!toastEl || !bodyEl) return;
      bodyEl.textContent = STATUS_LABELS[data.status] || ('Статус: ' + data.status);
      toastEl.className = 'toast align-items-center border-0 ' + (
        data.status === 'ready'     ? 'text-bg-success' :
        data.status === 'cancelled' ? 'text-bg-danger'  :
                                      'text-bg-primary'
      );
      var t = bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 6000 });
      t.show();
    } catch (err) { /* ignore */ }
  });
})();

// === PWA install prompt ===
(function () {
  var STORAGE_KEY = 'pwa_dismissed_at';
  var DISMISS_DAYS = 60;
  var toastEl = document.getElementById('pwa-install-toast');
  if (!toastEl) return;

  if (window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone) return;

  var dismissedAt = parseInt(localStorage.getItem(STORAGE_KEY) || '0', 10);
  if (dismissedAt && (Date.now() - dismissedAt) < DISMISS_DAYS * 86400000) return;

  var deferredPrompt = null;
  var btn = document.getElementById('pwa-install-btn');
  var textEl = document.getElementById('pwa-install-text');

  function show() {
    var t = bootstrap.Toast.getOrCreateInstance(toastEl);
    t.show();
  }

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;
    setTimeout(show, 1500);
  });

  btn.addEventListener('click', function () {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      deferredPrompt.userChoice.finally(function () {
        deferredPrompt = null;
        localStorage.setItem(STORAGE_KEY, '9999999999999');
        bootstrap.Toast.getInstance(toastEl).hide();
      });
    }
  });

  document.getElementById('pwa-install-dismiss').addEventListener('click', function () {
    localStorage.setItem(STORAGE_KEY, String(Date.now()));
  });

  window.addEventListener('appinstalled', function () {
    localStorage.setItem(STORAGE_KEY, '9999999999999');
    var inst = bootstrap.Toast.getInstance(toastEl);
    if (inst) inst.hide();
  });

  var ua = window.navigator.userAgent;
  var isIOS = /iPad|iPhone|iPod/.test(ua) && !window.MSStream;
  if (isIOS && !window.navigator.standalone) {
    textEl.innerHTML = 'Нажмите <strong>Поделиться</strong> ↑ → <strong>«На экран Домой»</strong>';
    document.getElementById('pwa-install-btn').style.display = 'none';
    setTimeout(show, 1500);
  }
})();
