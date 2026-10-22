"""
Notification services for the Orders app.

Functions
---------
send_whatsapp_receipt(order)   — WhatsApp message via Twilio adapter (reuses sales app adapter)
send_email_invoice(order)      — HTML email via Django's SMTP backend
send_whatsapp_message(to, body) — Raw WhatsApp send (reused by scheduled tasks)
send_restock_alert(client, products) — Restock notification via WhatsApp + Email
send_greeting_message(client)  — Weekly greeting via WhatsApp + Email
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# WhatsApp helpers
# ---------------------------------------------------------------------------

def _get_whatsapp_adapter():
    """Reuse the Twilio/Stub adapter from the sales app."""
    from sales.services.messaging import get_messaging_adapter
    return get_messaging_adapter()


def send_whatsapp_message(to: str, body: str) -> dict:
    """Send a raw WhatsApp message to any E.164 number."""
    adapter = _get_whatsapp_adapter()
    try:
        result = adapter.send_whatsapp(to=to, body=body)
        logger.info('WhatsApp sent to %s', to)
        return result
    except Exception as exc:
        logger.error('WhatsApp failed to %s: %s', to, exc)
        raise


def send_whatsapp_receipt(order) -> dict:
    """
    Send a purchase receipt summary via WhatsApp immediately after order creation.

    Message format:
        ✅ Purchase Receipt — SalesPilot
        Hi [Name], here's your receipt for Order #[id]:

        • Product 1 × 2  =  ₹200.00
        • Product 2 × 1  =  ₹150.00

        Total: ₹350.00
        Date: 22 Oct 2026

        Thank you for your purchase! 🙏
    """
    items_lines = '\n'.join(
        f'  • {item.product.name} × {item.quantity}  =  ₹{item.line_total:,.2f}'
        for item in order.items.select_related('product').all()
    )
    body = (
        f'✅ *Purchase Receipt — SalesPilot*\n\n'
        f'Hi {order.client.name}, here\'s your receipt for *Order #{order.pk}*:\n\n'
        f'{items_lines}\n\n'
        f'*Total: ₹{order.total_amount:,.2f}*\n'
        f'Date: {order.created_at.strftime("%d %b %Y")}\n\n'
        f'Thank you for your purchase! 🙏'
    )
    return send_whatsapp_message(to=order.client.phone_number, body=body)


# ---------------------------------------------------------------------------
# Email helpers
# ---------------------------------------------------------------------------

def send_email_invoice(order) -> None:
    """
    Render and send an HTML email invoice for a completed order.

    Uses Django's EmailMultiAlternatives to attach both plain-text and
    HTML versions of the invoice.
    """
    subject = f'Your Invoice — Order #{order.pk} | SalesPilot'
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@salespilot.com')
    to_email = order.client.email

    # Render HTML body from template
    html_body = render_to_string(
        'orders/email/invoice.html',
        {
            'order': order,
            'items': order.items.select_related('product').all(),
            'company_name': 'SalesPilot',
            'now': timezone.now(),
        },
    )

    # Plain-text fallback
    plain_body = (
        f'Dear {order.client.name},\n\n'
        f'Thank you for your purchase!\n\n'
        f'Order #{order.pk} — Total: ₹{order.total_amount:,.2f}\n\n'
        f'Please find your invoice details at the link below.\n\n'
        f'SalesPilot Team'
    )

    try:
        msg = EmailMultiAlternatives(subject, plain_body, from_email, [to_email])
        msg.attach_alternative(html_body, 'text/html')
        msg.send()
        logger.info('Email invoice sent to %s for order #%s', to_email, order.pk)
    except Exception as exc:
        logger.error('Email failed for order #%s: %s', order.pk, exc)
        raise


# ---------------------------------------------------------------------------
# Scheduled task helpers
# ---------------------------------------------------------------------------

def send_restock_alert(client, products) -> None:
    """
    Notify a client about restocked products via WhatsApp + Email.
    Called by the weekly Celery Beat task.
    """
    if not products:
        return

    product_lines = '\n'.join(f'  • {p.name} — ₹{p.price:,.2f}' for p in products)

    # WhatsApp
    wa_body = (
        f'🎉 *Great news, {client.name}!*\n\n'
        f'The following items are back in stock:\n\n'
        f'{product_lines}\n\n'
        f'Visit us or reply to this message to place your order.\n'
        f'— SalesPilot Team'
    )
    try:
        send_whatsapp_message(to=client.phone_number, body=wa_body)
    except Exception:
        pass  # Already logged in send_whatsapp_message

    # Email
    subject = '🎉 Restocked Items — SalesPilot'
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@salespilot.com')
    html_body = render_to_string(
        'orders/email/restock_alert.html',
        {'client': client, 'products': products, 'company_name': 'SalesPilot'},
    )
    plain_body = f'Hi {client.name},\n\nThese items are back in stock:\n{product_lines}\n\n— SalesPilot'
    try:
        msg = EmailMultiAlternatives(subject, plain_body, from_email, [client.email])
        msg.attach_alternative(html_body, 'text/html')
        msg.send()
        logger.info('Restock alert email sent to %s', client.email)
    except Exception as exc:
        logger.error('Restock email failed for %s: %s', client.email, exc)


def send_greeting_message(client) -> None:
    """
    Send a weekly greeting/promotional ping via WhatsApp + Email.
    Called by the weekly Celery Beat task.
    """
    # WhatsApp
    wa_body = (
        f'👋 Hi {client.name}!\n\n'
        f'Hope you\'re having a wonderful week. 😊\n\n'
        f'We have great deals waiting for you at SalesPilot. '
        f'Reply to this message or visit us to explore!\n\n'
        f'— SalesPilot Team'
    )
    try:
        send_whatsapp_message(to=client.phone_number, body=wa_body)
    except Exception:
        pass

    # Email
    subject = '👋 Hello from SalesPilot!'
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@salespilot.com')
    html_body = render_to_string(
        'orders/email/greeting.html',
        {'client': client, 'company_name': 'SalesPilot'},
    )
    plain_body = f'Hi {client.name},\n\nWe miss you! Come check out our latest offers.\n\n— SalesPilot'
    try:
        msg = EmailMultiAlternatives(subject, plain_body, from_email, [client.email])
        msg.attach_alternative(html_body, 'text/html')
        msg.send()
        logger.info('Greeting email sent to %s', client.email)
    except Exception as exc:
        logger.error('Greeting email failed for %s: %s', client.email, exc)
