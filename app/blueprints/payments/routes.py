"""Webhook от ЮKassa. Принимает уведомление, перепроверяет платёж через API,
обновляет заказ. Идемпотентен (повторный webhook = no-op)."""
from flask import Blueprint, request, current_app, abort

from app.extensions import db, csrf
from app.models import Order
from app.services import payment_service, pubsub
from app.utils.security import audit

payments_bp = Blueprint('payments', __name__)


@payments_bp.route('/yookassa/webhook', methods=['POST'])
@csrf.exempt
def yookassa_webhook():
    """ЮKassa POSTит сюда уведомления (`payment.succeeded` и др.).

    Безопасность: подписи у ЮKassa нет, защищаемся re-fetch из API.
    Любой может слать сюда POST — мы всё равно идём в реальный API
    и берём истинное состояние платежа. Подделать без secret_key нельзя.
    """
    body = request.get_json(silent=True) or {}
    event = body.get('event')
    payment_obj = body.get('object') or {}
    payment_id = payment_obj.get('id')

    if not payment_id:
        return ('', 400)

    # Re-fetch — единственный надёжный источник истины.
    try:
        payment = payment_service.fetch_payment(payment_id)
    except Exception as exc:
        current_app.logger.exception('webhook.fetch_failed: %s', exc)
        return ('', 200)  # 200 чтобы ЮKassa не повторял; разберёмся вручную

    # Только успешные оплаты обрабатываем (отмены/возвраты — backlog).
    if event != 'payment.succeeded' or payment.status != 'succeeded':
        return ('', 200)

    order = Order.query.filter_by(payment_id=payment_id).first()
    if order is None:
        # Возможно платёж не наш — игнорируем без ошибки.
        current_app.logger.warning('webhook: order not found for payment %s', payment_id)
        return ('', 200)

    if order.is_paid:
        return ('', 200)  # идемпотентность

    order.is_paid = True
    db.session.commit()

    audit('payment.succeeded', order_id=order.id, payment_id=payment_id)
    pubsub.publish({
        'type': 'order-status',
        'order_id': order.id,
        'status': order.status,
        'user_id': order.user_id,
    })
    return ('', 200)
