from app import create_app          # Функция для создания приложения Flask
from extensions import db           # Объект базы данных SQLAlchemy
from models.menu import Category, MenuItem  # Модели категорий и блюд
from models.user import User        # Модель пользователя (если нужна)


# Создаем экземпляр приложения
app = create_app()


with app.app_context():
    
    # ========== ЧАСТЬ 1: ПРОВЕРКА И СОЗДАНИЕ КАТЕГОРИЙ ==========
    

    first_courses = Category.query.filter_by(name='Первые блюда').first()
    
    # Ищем категорию "Напитки"
    drinks = Category.query.filter_by(name='Напитки').first()
    sandwiches = Category.query.filter_by(name='Сэндвичи').first()
    
  
    if not first_courses:
        # Создаем новый объект категории
        first_courses = Category(name='Первые блюда')
        # Добавляем объект в сессию базы данных (в очередь на добавление)
        db.session.add(first_courses)
        print('✅ Создана категория: Первые блюда')
    
  
    if not drinks:
        # Создаем новую категорию
        drinks = Category(name='Напитки')
        # Добавляем в сессию
        db.session.add(drinks)
        print('✅ Создана категория: Напитки')

    if not sandwiches:
        sandwiches = Category(name='Сэндвичи')
        db.session.add(sandwiches)
        print('✅ Создана категория: Сэндвичи')
    

    db.session.commit()
    print('📌 Категории сохранены в базе данных')
    

    new_products = [
        # Первые блюда
        {'name': 'Солянка', 'price': 150.0, 'category_name': 'Первые блюда'},
        {'name': 'Уха', 'price': 180.0, 'category_name': 'Первые блюда'},
        {'name': 'Щи', 'price': 110.0, 'category_name': 'Первые блюда'},
        {'name': 'Лапша куриная', 'price': 130.0, 'category_name': 'Первые блюда'},
        {'name': 'Грибной суп', 'price': 140.0, 'category_name': 'Первые блюда'},
        
        # Напитки 
        {'name': 'Эспрессо_S', 'price': 100.0, 'category_name': 'Напитки'},
        {'name': 'Американо_S', 'price': 110.0, 'category_name': 'Напитки'},
        {'name': 'Американо_M', 'price': 130.0, 'category_name': 'Напитки'},
        {'name': 'Капучино_M', 'price': 170.0, 'category_name': 'Напитки'},
        {'name': 'Капучино_L', 'price': 210.0, 'category_name': 'Напитки'},
        {'name': 'Флэт уайт_S', 'price': 150.0, 'category_name': 'Напитки'},
        {'name': 'Флэт уайт_M', 'price': 190.0, 'category_name': 'Напитки'},
        {'name': 'Моккачино_M', 'price': 180.0, 'category_name': 'Напитки'},
        {'name': 'Моккачино_L', 'price': 210.0, 'category_name': 'Напитки'},
        {'name': 'Латте_M', 'price': 170.0, 'category_name': 'Напитки'},
        {'name': 'Латте_L', 'price': 210.0, 'category_name': 'Напитки'},
        {'name': 'Раф_M', 'price': 220.0, 'category_name': 'Напитки'},
        {'name': 'Раф_L', 'price': 260.0, 'category_name': 'Напитки'},
        {'name': 'Какао_M', 'price': 130.0, 'category_name': 'Напитки'},
        {'name': 'Какао_L', 'price': 180.0, 'category_name': 'Напитки'},
        {'name': 'Фруктовый чай_M', 'price': 130.0, 'category_name': 'Напитки'},
        {'name': 'Фруктовый чай_L', 'price': 160.0, 'category_name': 'Напитки'},
        {'name': 'Бамбл_M', 'price': 210.0, 'category_name': 'Напитки'},
        {'name': 'Эспрессо тоник_M', 'price': 210.0, 'category_name': 'Напитки'},
        {'name': 'Айс Латте_M', 'price': 210.0, 'category_name': 'Напитки'},
        {'name': 'Фруктовый чай холодный_M', 'price': 160.0, 'category_name': 'Напитки'},
        {'name': 'Шот эспрессо', 'price': 35.0, 'category_name': 'Напитки'},
        {'name': 'Сироп', 'price': 30.0, 'category_name': 'Напитки'},
        {'name': 'Альтернативное молоко', 'price': 50.0, 'category_name': 'Напитки'},
    

        # Сэндвичи
        {'name': 'Сэндвич с ветчиной и сыром в белом хлебе', 'price': 180.0, 'category_name': 'Сэндвичи'},
        {'name': 'Сэндвич с ветчиной и сыром в чёрном хлебе', 'price': 180.0, 'category_name': 'Сэндвичи'},
        {'name': 'Сэндвич с курицей в белом хлебе', 'price': 180.0, 'category_name': 'Сэндвичи'},
        {'name': 'Сэндвич с курицей в чёрном хлебе', 'price': 180.0, 'category_name': 'Сэндвичи'},
        {'name': 'Сэндвич с индейкой в белом хлебе', 'price': 180.0, 'category_name': 'Сэндвичи'},
        {'name': 'Сэндвич с индейкой в чёрном хлебе', 'price': 180.0, 'category_name': 'Сэндвичи'},
        {'name': 'Сэндвич с ростбифом', 'price': 180.0, 'category_name': 'Сэндвичи'},
        {'name': 'Шаурма в пите', 'price': 180.0, 'category_name': 'Сэндвичи'},
        {'name': 'Сэндвич с ростифом в пите', 'price': 180.0, 'category_name': 'Сэндвичи'},
        {'name': 'Шаурма', 'price': 110.0, 'category_name': 'Сэндвичи'},
    ]
    

    added_count = 0
    
    # Перебираем каждый продукт из списка
    for product in new_products:
     
        category = Category.query.filter_by(name=product['category_name']).first()
        
        # Проверяем, существует ли уже такой продукт в этой категории
        # Чтобы не добавлять дубликаты
        existing = MenuItem.query.filter_by(
            name=product['name'],           # Имя продукта должно совпадать
            category_id=category.id          # ID категории должно совпадать
        ).first()
        
        # Если продукт не найден (existing == None)
        if not existing:
            # Создаем новый объект MenuItem
            item = MenuItem(
                name=product['name'],        # Название блюда
                price=product['price'],      # Цена блюда
                category_id=category.id      # ID категории (связь с таблицей Category)
            )
            
            # Добавляем объект в сессию базы данных
            db.session.add(item)
            
            # Увеличиваем счетчик добавленных продуктов
            added_count += 1
            
            # Выводим сообщение об успешном добавлении
            print(f'✅ Добавлен: {product["name"]} - {product["price"]} руб. (категория: {product["category_name"]})')
        else:
            # Если продукт уже существует, выводим предупреждение
            print(f'⚠️ Продукт "{product["name"]}" уже существует в категории "{product["category_name"]}"')
    
    # Сохраняем все добавленные продукты в базу данных
  
    db.session.commit()
    
    # ВЫВОД СТАТИСТИКИ
    
    print(f'\n{"="*50}')
    print(f'📊 СТАТИСТИКА ДОБАВЛЕНИЯ:')
    print(f'{"="*50}')
    print(f'✅ Всего добавлено продуктов: {added_count}')
    
    # ОТОБРАЖЕНИЕ ВСЕХ ПРОДУКТОВ
    
    print(f'\n🍽️ ТЕКУЩИЙ СПИСОК ПРОДУКТОВ В БАЗЕ ДАННЫХ:')
    print(f'{"="*50}')
    
    # Получаем все продукты из базы данных
    # order_by(MenuItem.category_id) - сортируем по ID категории
    all_items = MenuItem.query.order_by(MenuItem.category_id).all()
    
    # Переменная для хранения текущей категории (для группировки)
    current_category = None
    
    # Перебираем все продукты
    for item in all_items:
        # Получаем объект категории для текущего продукта
        cat = Category.query.get(item.category_id)
        
        # Если категория изменилась, выводим заголовок категории
        if current_category != cat.name:
            current_category = cat.name
            print(f'\n📁 {cat.name}:')
        
        # Выводим информацию о продукте
        # Форматируем цену с двумя знаками после запятой
        print(f'  • {item.name} - {item.price:.2f} руб.')
    
    # Выводим общее количество продуктов
    total_count = MenuItem.query.count()
    print(f'\n{"="*50}')
    print(f'📊 Всего продуктов в базе: {total_count}')
    print(f'{"="*50}')