"""
Celery tasks for the CRM sales app.

Tasks
-----
dispatch_notification — Sends a single notification (SMS or WhatsApp)
                        via the configured messaging adapter and updates
                        the MessageLog status accordingly.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def dispatch_notification(self, sale_id: int, template_id: int, channel: str):
    """
    Dispatch one notification and record the outcome in MessageLog.

    Parameters
    ----------
    sale_id     : pk of the Sale record
    template_id : pk of the NotificationTemplate to use
    channel     : 'sms' | 'whatsapp'

    Retry policy
    ------------
    Up to 3 automatic retries with a 60-second back-off when the messaging
    adapter raises an exception (e.g. network error, Twilio 5xx).
    """
    # Lazy imports keep the module importable before Django is fully set up
    from .models import MessageLog, NotificationTemplate, Sale
    from .services.messaging import get_messaging_adapter

    # ------------------------------------------------------------------
    # 1. Fetch related objects
    # ------------------------------------------------------------------
    try:
        sale = Sale.objects.get(pk=sale_id)
        template = NotificationTemplate.objects.get(pk=template_id)
    except Sale.DoesNotExist:
        logger.error('dispatch_notification: Sale pk=%s not found.', sale_id)
        return
    except NotificationTemplate.DoesNotExist:
        logger.error(
            'dispatch_notification: NotificationTemplate pk=%s not found.',
            template_id,
        )
        return

    # ------------------------------------------------------------------
    # 2. Render the template body
    # ------------------------------------------------------------------
    try:
        body = template.render(sale)
    except KeyError as exc:
        logger.error(
            'dispatch_notification: template pk=%s has bad placeholder: %s',
            template_id,
            exc,
        )
        return

    # ------------------------------------------------------------------
    # 3. Create a MessageLog row in QUEUED state
    # ------------------------------------------------------------------
    log = MessageLog.objects.create(
        sale=sale,
        template=template,
        channel=channel,
        recipient=sale.phone_number,
        payload=body,
        status=MessageLog.STATUS_QUEUED,
    )

    # ------------------------------------------------------------------
    # 4. Attempt delivery via the adapter
    # ------------------------------------------------------------------
    adapter = get_messaging_adapter()
    try:
        if channel == 'sms':
            adapter.send_sms(to=sale.phone_number, body=body)
        elif channel == 'whatsapp':
            adapter.send_whatsapp(to=sale.phone_number, body=body)
        else:
            raise ValueError(f'Unknown channel: {channel!r}')

        log.status = MessageLog.STATUS_SENT
        log.save(update_fields=['status'])
        logger.info(
            'dispatch_notification: sent %s to %s (log pk=%s)',
            channel,
            sale.phone_number,
            log.pk,
        )

    except Exception as exc:
        log.status = MessageLog.STATUS_FAILED
        log.error_message = str(exc)
        log.save(update_fields=['status', 'error_message'])
        logger.error(
            'dispatch_notification: failed for log pk=%s — %s. '
            'Retry %d/%d.',
            log.pk,
            exc,
            self.request.retries,
            self.max_retries,
        )
        raise self.retry(exc=exc)
