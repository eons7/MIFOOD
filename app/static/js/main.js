/* МИФУД — клиентские скрипты.
   Вся логика тут (а не в inline <script>) для CSP без 'unsafe-inline'. */

// === Подтверждение отправки формы (data-confirm="...") ===
document.addEventListener('submit', function (e) {
  const form = e.target;
  const msg = form && form.dataset && form.dataset.confirm;
  if (msg && !window.confirm(msg)) e.preventDefault();
});

// === HTMX: CSRF + ошибки ===
document.body.addEventListener('htmx:configRequest', function (e) {
  const token = document.querySelector('meta[name="csrf-token"]');
  if (token) e.detail.headers['X-CSRFToken'] = token.content;
});

document.body.addEventListener('htmx:responseError', function (e) {
  const msg = (e.detail && e.detail.xhr && e.detail.xhr.responseText) || 'Произошла ошибка';
  alert(msg);
});

// === Service Worker ===
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}

// === Меню: чипы категорий ===
document.addEventListener('click', function (e) {
  const chip = e.target.closest('#cat-chips .mifud-chip');
  if (!chip) return;
  document.querySelectorAll('#cat-chips .mifud-chip').forEach(function (c) {
    c.classList.remove('is-active');
  });
  chip.classList.add('is-active');
});

// === Меню: карточка кофе (выбор размера + +/-) ===
function coffeeCardOf(el) {
  return el.closest('[data-coffee-card]');
}

document.addEventListener('change', function (e) {
  const radio = e.target.closest('[data-coffee-card] input[type="radio"]');
  if (!radio) return;
  const card = coffeeCardOf(radio);
  const priceEl = card.querySelector('[data-coffee-price]');
  if (priceEl) priceEl.textContent = radio.dataset.price + ' ₽';
  const qtyEl = card.querySelector('[data-coffee-qty]');
  if (qtyEl) qtyEl.textContent = radio.dataset.qty || '0';
});

document.addEventListener('click', function (e) {
  const addBtn = e.target.closest('[data-coffee-add]');
  if (addBtn) {
    const card = coffeeCardOf(addBtn);
    const checked = card.querySelector('input[type="radio"]:checked');
    if (!checked) return;
    htmx.ajax('POST', '/menu/add/' + checked.dataset.id, { target: '#cart-badge', swap: 'outerHTML' });
    return;
  }
  const removeBtn = e.target.closest('[data-coffee-remove]');
  if (removeBtn) {
    const card = coffeeCardOf(removeBtn);
    const checked = card.querySelector('input[type="radio"]:checked');
    if (!checked) return;
    if (parseInt(checked.dataset.qty || '0', 10) <= 0) return;
    htmx.ajax('POST', '/menu/remove/' + checked.dataset.id, {
      target: '#cart-badge', swap: 'outerHTML',
      headers: { 'HX-Request': 'true' },
    });
  }
});

// После add/remove синхронизируем data-qty у радио и видимый счётчик
document.body.addEventListener('htmx:afterRequest', function (e) {
  if (!e.detail || !e.detail.successful) return;
  const path = (e.detail.pathInfo && e.detail.pathInfo.requestPath) || '';
  const m = path.match(/^\/menu\/(add|remove)\/(\d+)$/);
  if (!m) return;
  const action = m[1], id = m[2];
  document.querySelectorAll('[data-coffee-card] input[type="radio"][data-id="' + id + '"]').forEach(function (r) {
    let q = parseInt(r.dataset.qty || '0', 10);
    q = action === 'add' ? q + 1 : Math.max(0, q - 1);
    r.dataset.qty = String(q);
    if (r.checked) {
      const qv = r.closest('[data-coffee-card]').querySelector('[data-coffee-qty]');
      if (qv) qv.textContent = String(q);
    }
  });
});
