import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def dispatch_notification(self, sale_id, template_id, channel):
    from .models import MessageLog, NotificationTemplate, Sale
    from .services.messaging import get_messaging_adapter

    try:
        sale = Sale.objects.get(pk=sale_id)
        template = NotificationTemplate.objects.get(pk=template_id)
    except (Sale.DoesNotExist, NotificationTemplate.DoesNotExist) as exc:
        logger.error('dispatch_notification: object not found: %s', exc)
        return

    body = template.render(sale)
    log = MessageLog.objects.create(
        sale=sale, template=template, channel=channel,
        recipient=sale.phone_number, payload=body, status='queued',
    )
    adapter = get_messaging_adapter()
    try:
        if channel == 'sms':
            adapter.send_sms(to=sale.phone_number, body=body)
        elif channel == 'whatsapp':
            adapter.send_whatsapp(to=sale.phone_number, body=body)
        log.status = 'sent'
        log.save(update_fields=['status'])
    except Exception as exc:
        log.status = 'failed'
        log.error_message = str(exc)
        log.save(update_fields=['status', 'error_message'])
        raise self.retry(exc=exc)
