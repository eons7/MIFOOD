"""Обёртка над ЮKassa SDK: создание платежа и верификация webhook."""
from flask import current_app
from yookassa import Configuration, Payment


def is_enabled() -> bool:
    """True если в конфиге заданы ключи ЮKassa."""
    return bool(
        current_app.config.get('YOOKASSA_SHOP_ID')
        and current_app.config.get('YOOKASSA_SECRET_KEY')
    )


def _init():
    Configuration.account_id = current_app.config['YOOKASSA_SHOP_ID']
    Configuration.secret_key = current_app.config['YOOKASSA_SECRET_KEY']


def create_payment(order, return_url: str) -> Payment:
    """Создаёт платёж в ЮKassa, возвращает объект Payment.

    `confirmation_url` для редиректа клиента — `payment.confirmation.confirmation_url`.
    `payment.id` нужно сохранить в `order.payment_id` для последующей привязки
    webhook к заказу.
    """
    _init()
    payment = Payment.create({
        'amount': {
            'value': f'{order.total_price:.2f}',
            'currency': 'RUB',
        },
        'confirmation': {
            'type': 'redirect',
            'return_url': return_url,
        },
        'capture': True,
        'description': f'Заказ #{order.id} МИФУД',
        'metadata': {'order_id': str(order.id)},
    })
    return payment


def fetch_payment(payment_id: str) -> Payment:
    """Запрашивает актуальное состояние платежа из API ЮKassa.
    Используется в webhook-handler для верификации (вместо проверки подписи —
    ЮKassa подписи в webhook не отдаёт, рекомендованный путь — re-fetch)."""
    _init()
    return Payment.find_one(payment_id)
