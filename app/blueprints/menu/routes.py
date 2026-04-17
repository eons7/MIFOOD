from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from app import db
from app.models import MenuItem, Category

menu_bp = Blueprint('menu', __name__)

@menu_bp.route('/', methods=['GET'])
@login_required
def index():
    q = request.args.get('q', '').strip()
    category_id = request.args.get('category_id', type=int)
    
    query = MenuItem.query.filter_by(is_available=True)
    if q:
        query = query.filter(MenuItem.name.ilike(f'%{q}%'))
    if category_id:
        query = query.filter_by(category_id=category_id)
        
    items = query.order_by(MenuItem.name).all()
    categories = Category.query.all()
    
    cart = session.get('cart', {})
    cart_total = 0 # Здесь должна быть логика подсчета суммы корзины по ID
    
    if request.headers.get('HX-Request'):
        return render_template('menu/_items_list.html', items=items)
    return render_template('menu/index.html', items=items, categories=categories, cart_total=cart_total)

@menu_bp.route('/add/<int:id>', methods=['POST'])
@login_required
def add_to_cart(id):
    item = MenuItem.query.get_or_404(id)
    if not item.is_available:
        return "Ошибка", 400
    if 'cart' not in session:
        session['cart'] = {}
        
    if sum(session['cart'].values()) >= 10:
        return "Достигнут лимит 10 блюд", 400
        
    key = str(id)
    session['cart'][key] = session['cart'].get(key, 0) + 1
    session.modified = True
    return render_template('menu/_cart_badge.html')

@menu_bp.route('/remove/<int:id>', methods=['POST'])
@login_required
def remove_from_cart(id):
    if 'cart' in session:
        session['cart'].pop(str(id), None)
        session.modified = True
    return redirect(url_for('orders.create'))

@menu_bp.route('/update/<int:id>', methods=['POST'])
@login_required
def update_cart(id):
    qty = request.form.get('quantity', type=int)
    key = str(id)
    if qty <= 0:
        session['cart'].pop(key, None)
    else:
        session['cart'][key] = min(qty, 10)
    session.modified = True
    return render_template('menu/_cart_fragment.html')