"""
Celery tasks for the Orders app.

Immediate tasks (triggered on order creation)
---------------------------------------------
dispatch_order_notifications(order_id) — WhatsApp receipt + Email invoice

Scheduled tasks (Celery Beat — configured in settings.py)
----------------------------------------------------------
send_weekly_restock_notifications()    — Ping all clients about restocked products
send_weekly_greeting()                 — Weekly relationship/promo message to all clients
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Immediate: post-sale receipt dispatch
# ---------------------------------------------------------------------------

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def dispatch_order_notifications(self, order_id: int):
    """
    Send WhatsApp receipt + HTML email invoice for a completed order.

    Triggered immediately after order creation (via signal or view).
    Retries up to 3 times on failure with 60-second back-off.
    """
    from .models import Order
    from .services.notifications import send_whatsapp_receipt, send_email_invoice

    try:
        order = Order.objects.select_related('client').prefetch_related(
            'items__product'
        ).get(pk=order_id)
    except Order.DoesNotExist:
        logger.error('dispatch_order_notifications: Order pk=%s not found.', order_id)
        return

    errors = []

    # 1. WhatsApp receipt
    try:
        send_whatsapp_receipt(order)
    except Exception as exc:
        logger.error('WhatsApp receipt failed for order #%s: %s', order_id, exc)
        errors.append(('whatsapp', str(exc)))

    # 2. Email invoice
    try:
        send_email_invoice(order)
    except Exception as exc:
        logger.error('Email invoice failed for order #%s: %s', order_id, exc)
        errors.append(('email', str(exc)))

    # Mark receipt_sent if both succeeded
    if not errors:
        Order.objects.filter(pk=order_id).update(receipt_sent=True)
        logger.info('All notifications dispatched for order #%s', order_id)
    else:
        logger.warning(
            'Order #%s: %d notification(s) failed — %s. Retrying…',
            order_id,
            len(errors),
            errors,
        )
        raise self.retry(exc=Exception(str(errors)))


# ---------------------------------------------------------------------------
# Scheduled: weekly restock notifications
# ---------------------------------------------------------------------------

@shared_task
def send_weekly_restock_notifications():
    """
    Weekly Celery Beat task (runs every Monday at 09:00).

    Fetches all products flagged with `is_restocked=True` and sends a
    WhatsApp + Email alert to every active client.
    """
    from .models import Client, Product
    from .services.notifications import send_restock_alert

    restocked = list(Product.objects.filter(is_restocked=True, stock_quantity__gt=0))
    if not restocked:
        logger.info('send_weekly_restock_notifications: No restocked products — skipping.')
        return

    clients = Client.objects.all()
    count = 0
    for client in clients:
        try:
            send_restock_alert(client, restocked)
            count += 1
        except Exception as exc:
            logger.error('Restock alert failed for client %s: %s', client.pk, exc)

    logger.info(
        'send_weekly_restock_notifications: Sent restock alerts to %d client(s) '
        'for %d product(s).',
        count,
        len(restocked),
    )


# ---------------------------------------------------------------------------
# Scheduled: weekly greeting messages
# ---------------------------------------------------------------------------

@shared_task
def send_weekly_greeting():
    """
    Weekly Celery Beat task (runs every Monday at 08:00).

    Sends a friendly relationship/promo ping to all clients via
    WhatsApp + Email.
    """
    from .models import Client
    from .services.notifications import send_greeting_message

    clients = Client.objects.all()
    count = 0
    for client in clients:
        try:
            send_greeting_message(client)
            count += 1
        except Exception as exc:
            logger.error('Greeting failed for client %s: %s', client.pk, exc)

    logger.info('send_weekly_greeting: Greeted %d client(s).', count)
