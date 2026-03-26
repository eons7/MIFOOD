from app.extensions import db

#-
class Category(db.Model):
    __tablename__ = 'categories'

    id   = db.Column(db.Integer,    primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)

    # Связи
    menu_items = db.relationship('MenuItem', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'


class MenuItem(db.Model):
    __tablename__ = 'menu_items'

    id           = db.Column(db.Integer,     primary_key=True)
    name         = db.Column(db.String(150), nullable=False)
    description  = db.Column(db.Text,        nullable=True)
    price        = db.Column(db.Float,       nullable=False)
    image_url    = db.Column(db.String(300), nullable=True)
    is_available = db.Column(db.Boolean,     nullable=False, default=True)
    category_id  = db.Column(db.Integer,     db.ForeignKey('categories.id'), nullable=False)

    # Связи
    order_items = db.relationship('OrderItem', backref='menu_item', lazy=True)

    def __repr__(self):
        return f'<MenuItem {self.name} — {self.price}₽>'
    def toggle_availability(self):
        self.is_available = not self.is_available
