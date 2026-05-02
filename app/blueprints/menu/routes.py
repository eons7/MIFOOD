import re

from flask import Blueprint, render_template, redirect, url_for, request, session
from flask_login import login_required

from app.extensions import limiter
from app.models import MenuItem, Category
from app.repositories import menu_repository

menu_bp = Blueprint('menu', __name__)

_COFFEE_SUFFIX_RE = re.compile(r'^(.+)_([SML])$')
_SIZE_ORDER = {'S': 0, 'M': 1, 'L': 2}

# Порядок категорий: меньшее число = выше. Отсутствующие — в конец по алфавиту.
_CATEGORY_ORDER = {
    'Сэндвичи':     0,
    'Первые блюда': 1,
    'Напитки':      2,
    'Добавки':      3,
}


def _sort_items(items: list) -> list:
    """Сортировка по (приоритет категории, имя категории, имя позиции)."""
    def key(it):
        cat_name = it.category.name if it.category else ''
        return (_CATEGORY_ORDER.get(cat_name, 99), cat_name, it.name)
    return sorted(items, key=key)


def _cart_total(cart: dict) -> float:
    if not cart:
        return 0
    ids = [int(k) for k in cart.keys()]
    items = MenuItem.query.filter(MenuItem.id.in_(ids)).all()
    return sum(item.price * cart.get(str(item.id), 0) for item in items)


def _cart_count(cart: dict) -> int:
    return sum(cart.values()) if cart else 0


def _group_coffee(items: list) -> list:
    """Объединяет позиции с суффиксами _S/_M/_L в одну карточку coffee."""
    buckets: dict[str, list] = {}
    for it in items:
        m = _COFFEE_SUFFIX_RE.match(it.name)
        if m:
            buckets.setdefault(m.group(1), []).append((m.group(2), it))

    result = []
    seen = set()
    for it in items:
        m = _COFFEE_SUFFIX_RE.match(it.name)
        prefix = m.group(1) if m else None
        if prefix and prefix in buckets:
            if prefix in seen:
                continue
            seen.add(prefix)
            entries = buckets[prefix]
            entries.sort(key=lambda x: _SIZE_ORDER[x[0]])
            first = entries[0][1]
            result.append({
                'kind': 'coffee',
                'name': prefix,
                'description': first.description,
                'image_url': first.image_url,
                'category': first.category,
                'sizes': [{'size': s, 'item': i} for s, i in entries],
            })
        else:
            result.append({'kind': 'single', 'item': it})
    return result


@menu_bp.route('/', methods=['GET'])
@login_required
def index():
    q = request.args.get('q', '').strip()
    category_id = request.args.get('category_id', type=int) or request.args.get('category', type=int)

    query = MenuItem.query.filter_by(is_available=True)
    if category_id:
        query = query.filter_by(category_id=category_id)

    items = _sort_items(query.all())
    # Поиск в Python: SQLite LIKE/LOWER не case-insensitive для кириллицы.
    if q:
        ql = q.lower()
        items = [it for it in items if ql in it.name.lower()]

    categories = Category.query.order_by(Category.name).all()

    cart = session.get('cart', {})
    cart_total = _cart_total(cart)

    return render_template(
        'menu/index.html',
        groups=_group_coffee(items),
        categories=categories,
        cart=cart,
        cart_total=cart_total,
    )


@menu_bp.route('/items', methods=['GET'])
@login_required
def items():
    """HTMX-partial: список блюд для поиска/фильтров."""
    q = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int) or request.args.get('category_id', type=int)

    query = MenuItem.query.filter_by(is_available=True)
    if category_id:
        query = query.filter_by(category_id=category_id)

    items = _sort_items(query.all())
    if q:
        ql = q.lower()
        items = [it for it in items if ql in it.name.lower()]

    cart = session.get('cart', {})
    return render_template('menu/_items_list.html', groups=_group_coffee(items), cart=cart)


@menu_bp.route('/add/<int:id>', methods=['POST'])
@login_required
@limiter.limit('120 per minute')
def add_to_cart(id):
    item = menu_repository.get_item_by_id(id)
    if item is None or not item.is_available:
        return "Блюдо недоступно", 400

    cart = session.get('cart', {})
    key = str(id)
    if cart.get(key, 0) >= 10:
        return "Достигнут лимит 10 штук одной позиции", 400

    cart[key] = cart.get(key, 0) + 1
    session['cart'] = cart
    session.modified = True

    return render_template(
        'menu/_cart_badge.html',
        cart_total=_cart_total(cart),
        cart_count=_cart_count(cart),
        item_id=id,
        item_qty=cart[key],
    )


@menu_bp.route('/remove/<int:id>', methods=['POST'])
@login_required
@limiter.limit('120 per minute')
def remove_from_cart(id):
    cart = session.get('cart', {})
    key = str(id)
    if key in cart:
        cart[key] -= 1
        if cart[key] <= 0:
            cart.pop(key, None)
        session['cart'] = cart
        session.modified = True

    if request.headers.get('HX-Request'):
        return render_template(
            'menu/_cart_badge.html',
            cart_total=_cart_total(cart),
            cart_count=_cart_count(cart),
            item_id=id,
            item_qty=cart.get(key, 0),
        )
    return redirect(url_for('orders.create'))


@menu_bp.route('/update/<int:id>', methods=['POST'])
@login_required
@limiter.limit('120 per minute')
def update_cart(id):
    qty = request.form.get('quantity', type=int) or 0
    cart = session.get('cart', {})
    key = str(id)
    if qty <= 0:
        cart.pop(key, None)
    else:
        cart[key] = min(qty, 10)
    session['cart'] = cart
    session.modified = True

    return render_template('menu/_cart_fragment.html', cart=cart, cart_total=_cart_total(cart), cart_count=_cart_count(cart))
