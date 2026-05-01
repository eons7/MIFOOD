import os
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app import create_app
from app.extensions import db
from app.models.menu import Category, MenuItem
from app.models.user import User
from app.services.auth_service import set_password

# Импорт моделей до конфигурации relationship'ов SQLAlchemy.
from app.models.order import Order, OrderItem  # noqa: F401
from app.models.reservation import Reservation, Table  # noqa: F401


SEED_IMAGES_DIR = Path(__file__).resolve().parent.parent / 'seed_images'
UPLOADS_DIR = Path(__file__).resolve().parent / 'static' / 'uploads'
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.webp')
MAX_SIZE = (800, 800)
JPEG_QUALITY = 85


def process_seed_images():
    """Берёт raw-файлы из seed_images/<slug>.<ext>, жмёт и кладёт
    в static/uploads/<slug>.jpg.

    Валидация:
      • whitelist расширений (IMAGE_EXTS) — остальные пропускаются;
      • Pillow verify — защита от переименованных бинарников;
      • EXIF-ориентация применяется до ресайза;
      • thumbnail до MAX_SIZE с сохранением пропорций;
      • альфа-канал сводится на белый фон (JPEG его не поддерживает);
      • итоговый файл всегда .jpg — чтобы find_image работал предсказуемо.
    """
    if not SEED_IMAGES_DIR.exists():
        print(f'ℹ️  {SEED_IMAGES_DIR} не найдена — нечего обрабатывать.')
        return

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    processed = 0
    skipped = 0
    for src in sorted(SEED_IMAGES_DIR.iterdir()):
        if not src.is_file() or src.name.startswith('.'):
            continue

        ext = src.suffix.lower()
        if ext not in IMAGE_EXTS:
            print(f'⚠️  {src.name}: расширение {ext!r} не в whitelist {IMAGE_EXTS}')
            skipped += 1
            continue

        try:
            with Image.open(src) as img:
                img.verify()
        except (UnidentifiedImageError, OSError) as e:
            print(f'⚠️  {src.name}: не валидное изображение ({e})')
            skipped += 1
            continue

        try:
            with Image.open(src) as img:
                img = ImageOps.exif_transpose(img)
                img.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)

                if img.mode in ('RGBA', 'LA'):
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[-1])
                    img = bg
                elif img.mode == 'P':
                    img = img.convert('RGBA')
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[-1])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                dst = UPLOADS_DIR / f'{src.stem}.jpg'
                img.save(dst, 'JPEG', quality=JPEG_QUALITY, optimize=True)
                print(f'🖼️  {src.name} → uploads/{dst.name} ({dst.stat().st_size // 1024} КБ, {img.size[0]}×{img.size[1]})')
                processed += 1
        except Exception as e:
            print(f'⚠️  {src.name}: ошибка обработки ({e})')
            skipped += 1

    print(f'📦 Фото: обработано {processed}, пропущено {skipped}')


def find_image(slug: str) -> str | None:
    """Ищет файл uploads/<slug>.<ext> и возвращает URL-путь для шаблона.

    После process_seed_images() все файлы сохранены как .jpg, но сохраняем
    поиск по всем IMAGE_EXTS — на случай, если кто-то положил файл вручную.
    """
    if not slug:
        return None
    for ext in IMAGE_EXTS:
        filename = slug + ext
        if (UPLOADS_DIR / filename).is_file():
            return '/static/uploads/' + filename
    return None


app = create_app()


with app.app_context():
    db.create_all()

    # ========== ОБРАБОТКА ФОТО ==========
    # Raw-файлы из seed_images/ → сжатые .jpg в static/uploads/
    process_seed_images()

    # ========== ДЕМО-ЮЗЕРЫ ==========
    demo_users = [
        {'name': 'Admin',  'email': 'admin@mifi.ru', 'password': 'password', 'is_admin': True},   # nosec B105 — seed
        {'name': 'Иван',   'email': 'ivan@mifi.ru',  'password': 'password', 'is_admin': False},  # nosec B105 — seed
    ]
    users_added = 0
    for u in demo_users:
        if not User.query.filter_by(email=u['email']).first():
            user = User(name=u['name'], email=u['email'], is_admin=u['is_admin'])
            set_password(user, u['password'])
            db.session.add(user)
            users_added += 1
            print(f'✅ Юзер: {u["email"]} (admin={u["is_admin"]})')
    if users_added:
        db.session.commit()
    print(f'👤 Юзеры: добавлено {users_added}, всего {User.query.count()}')

    # ========== КАТЕГОРИИ ==========
    first_courses = Category.query.filter_by(name='Первые блюда').first()
    drinks = Category.query.filter_by(name='Напитки').first()
    sandwiches = Category.query.filter_by(name='Сэндвичи').first()

    if not first_courses:
        first_courses = Category(name='Первые блюда')
        db.session.add(first_courses)
        print('✅ Создана категория: Первые блюда')

    if not drinks:
        drinks = Category(name='Напитки')
        db.session.add(drinks)
        print('✅ Создана категория: Напитки')

    if not sandwiches:
        sandwiches = Category(name='Сэндвичи')
        db.session.add(sandwiches)
        print('✅ Создана категория: Сэндвичи')

    extras = Category.query.filter_by(name='Добавки').first()
    if not extras:
        extras = Category(name='Добавки')
        db.session.add(extras)
        print('✅ Создана категория: Добавки')

    db.session.commit()
    print('📌 Категории сохранены')

    # Миграция: перенос «Шот эспрессо», «Сироп», «Альтернативное молоко»
    # из «Напитки» в «Добавки»
    extras_names = ('Шот эспрессо', 'Сироп', 'Альтернативное молоко')
    moved = 0
    for n in extras_names:
        it = MenuItem.query.filter_by(name=n, category_id=drinks.id).first()
        if it:
            it.category_id = extras.id
            moved += 1
    if moved:
        db.session.commit()
        print(f'🔀 Перенесено в «Добавки»: {moved}')

    # ========== СТОЛЫ ==========
    tables_spec = [
        (1, 2), (2, 2), (3, 4), (4, 4), (5, 4), (6, 6), (7, 6), (8, 8),
    ]
    tables_added = 0
    for number, seats in tables_spec:
        if not Table.query.filter_by(number=number).first():
            db.session.add(Table(number=number, seats=seats, is_active=True))
            tables_added += 1
    db.session.commit()
    print(f'🪑 Столы: добавлено {tables_added}, всего {Table.query.count()}')

    # ========== БЛЮДА ==========
    # slug — это имя файла без расширения в app/static/uploads/
    # Положи файл <slug>.jpg (или .png / .webp) — seed подхватит автоматически.
    new_products = [
        # Первые блюда
        {'name': 'Солянка',        'price': 150.0, 'category_name': 'Первые блюда', 'slug': 'solyanka'},
        {'name': 'Уха',            'price': 180.0, 'category_name': 'Первые блюда', 'slug': 'uha'},
        {'name': 'Щи',             'price': 110.0, 'category_name': 'Первые блюда', 'slug': 'shchi'},
        {'name': 'Лапша куриная',  'price': 130.0, 'category_name': 'Первые блюда', 'slug': 'lapsha_kurinaya'},
        {'name': 'Грибной суп',    'price': 140.0, 'category_name': 'Первые блюда', 'slug': 'gribnoy_sup'},

        # Напитки
        {'name': 'Эспрессо_S',                 'price': 100.0, 'category_name': 'Напитки', 'slug': 'espresso_s'},
        {'name': 'Американо_S',                'price': 110.0, 'category_name': 'Напитки', 'slug': 'americano_s'},
        {'name': 'Американо_M',                'price': 130.0, 'category_name': 'Напитки', 'slug': 'americano_m'},
        {'name': 'Капучино_M',                 'price': 170.0, 'category_name': 'Напитки', 'slug': 'cappuccino_m'},
        {'name': 'Капучино_L',                 'price': 210.0, 'category_name': 'Напитки', 'slug': 'cappuccino_l'},
        {'name': 'Флэт уайт_S',                'price': 150.0, 'category_name': 'Напитки', 'slug': 'flat_white_s'},
        {'name': 'Флэт уайт_M',                'price': 190.0, 'category_name': 'Напитки', 'slug': 'flat_white_m'},
        {'name': 'Моккачино_M',                'price': 180.0, 'category_name': 'Напитки', 'slug': 'mocha_m'},
        {'name': 'Моккачино_L',                'price': 210.0, 'category_name': 'Напитки', 'slug': 'mocha_l'},
        {'name': 'Латте_M',                    'price': 170.0, 'category_name': 'Напитки', 'slug': 'latte_m'},
        {'name': 'Латте_L',                    'price': 210.0, 'category_name': 'Напитки', 'slug': 'latte_l'},
        {'name': 'Раф_M',                      'price': 220.0, 'category_name': 'Напитки', 'slug': 'raf_m'},
        {'name': 'Раф_L',                      'price': 260.0, 'category_name': 'Напитки', 'slug': 'raf_l'},
        {'name': 'Какао_M',                    'price': 130.0, 'category_name': 'Напитки', 'slug': 'cocoa_m'},
        {'name': 'Какао_L',                    'price': 180.0, 'category_name': 'Напитки', 'slug': 'cocoa_l'},
        {'name': 'Фруктовый чай_M',            'price': 130.0, 'category_name': 'Напитки', 'slug': 'fruit_tea_m'},
        {'name': 'Фруктовый чай_L',            'price': 160.0, 'category_name': 'Напитки', 'slug': 'fruit_tea_l'},
        {'name': 'Бамбл_M',                    'price': 210.0, 'category_name': 'Напитки', 'slug': 'bumble_m'},
        {'name': 'Эспрессо тоник_M',           'price': 210.0, 'category_name': 'Напитки', 'slug': 'espresso_tonic_m'},
        {'name': 'Айс Латте_M',                'price': 210.0, 'category_name': 'Напитки', 'slug': 'ice_latte_m'},
        {'name': 'Фруктовый чай холодный_M',   'price': 160.0, 'category_name': 'Напитки', 'slug': 'fruit_tea_cold_m'},
        {'name': 'Шот эспрессо',               'price': 35.0,  'category_name': 'Добавки', 'slug': 'espresso_shot'},
        {'name': 'Сироп',                      'price': 30.0,  'category_name': 'Добавки', 'slug': 'syrup'},
        {'name': 'Альтернативное молоко',      'price': 50.0,  'category_name': 'Добавки', 'slug': 'alt_milk'},

        # Сэндвичи
        {'name': 'Сэндвич с ветчиной и сыром в белом хлебе',  'price': 180.0, 'category_name': 'Сэндвичи', 'slug': 'sandwich_ham_cheese_white'},
        {'name': 'Сэндвич с ветчиной и сыром в чёрном хлебе', 'price': 180.0, 'category_name': 'Сэндвичи', 'slug': 'sandwich_ham_cheese_black'},
        {'name': 'Сэндвич с курицей в белом хлебе',           'price': 180.0, 'category_name': 'Сэндвичи', 'slug': 'sandwich_chicken_white'},
        {'name': 'Сэндвич с курицей в чёрном хлебе',          'price': 180.0, 'category_name': 'Сэндвичи', 'slug': 'sandwich_chicken_black'},
        {'name': 'Сэндвич с индейкой в белом хлебе',          'price': 180.0, 'category_name': 'Сэндвичи', 'slug': 'sandwich_turkey_white'},
        {'name': 'Сэндвич с индейкой в чёрном хлебе',         'price': 180.0, 'category_name': 'Сэндвичи', 'slug': 'sandwich_turkey_black'},
        {'name': 'Сэндвич с ростбифом',                       'price': 180.0, 'category_name': 'Сэндвичи', 'slug': 'sandwich_roastbeef'},
        {'name': 'Шаурма в пите',                             'price': 180.0, 'category_name': 'Сэндвичи', 'slug': 'shawarma_pita'},
        {'name': 'Сэндвич с ростбифом в пите',                'price': 180.0, 'category_name': 'Сэндвичи', 'slug': 'sandwich_roastbeef_pita'},
        {'name': 'Шаурма',                                    'price': 110.0, 'category_name': 'Сэндвичи', 'slug': 'shawarma'},
    ]

    added_count = 0
    updated_image_count = 0
    missing_images = []

    for product in new_products:
        category = Category.query.filter_by(name=product['category_name']).first()
        image_url = find_image(product['slug'])

        if image_url is None:
            missing_images.append(product['slug'])

        existing = MenuItem.query.filter_by(
            name=product['name'],
            category_id=category.id,
        ).first()

        if not existing:
            item = MenuItem(
                name=product['name'],
                price=product['price'],
                category_id=category.id,
                image_url=image_url,
            )
            db.session.add(item)
            added_count += 1
            print(f'✅ {product["name"]} — {product["price"]:.0f} ₽ (image: {image_url or "—"})')
        else:
            # Если картинка появилась — обновим существующий товар.
            if image_url and existing.image_url != image_url:
                existing.image_url = image_url
                updated_image_count += 1
                print(f'🖼️  Обновлена картинка: {product["name"]} → {image_url}')

    db.session.commit()

    # ========== СТАТИСТИКА ==========
    print(f'\n{"="*50}')
    print(f'📊 СТАТИСТИКА:')
    print(f'   Добавлено новых:   {added_count}')
    print(f'   Обновлено картинок: {updated_image_count}')
    print(f'   Всего в БД:        {MenuItem.query.count()}')
    if missing_images:
        print(f'\n📷 Нет файлов в app/static/uploads/ для слагов ({len(missing_images)} шт):')
        for s in missing_images:
            print(f'   • {s}.jpg  (или .png / .webp)')
    else:
        print('\n🎉 Все картинки на месте!')
    print("="*50)
