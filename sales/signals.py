"""
Signal handlers for the CRM sales app.

post_save on Sale — optionally auto-dispatch Celery notification tasks
when a new sale is created, based on the CRMSettings singleton.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CRMSettings, NotificationTemplate, Sale

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Sale)
def auto_notify_on_sale_created(sender, instance: Sale, created: bool, **kwargs):
    """
    Triggered after every Sale save.

    When a *new* sale is created and auto-send is enabled in CRMSettings,
    this handler enqueues a Celery task for every active NotificationTemplate.
    """
    if not created:
        return  # Only fire on creation, not updates

    settings = CRMSettings.load()
    if not settings.auto_send_enabled:
        logger.debug(
            'auto_notify_on_sale_created: auto-send disabled — skipping sale pk=%s',
            instance.pk,
        )
        return

    # Import here to avoid circular imports at module load time
    from .tasks import dispatch_notification  # noqa: PLC0415

    active_templates = NotificationTemplate.objects.filter(is_active=True)
    if not active_templates.exists():
        logger.info(
            'auto_notify_on_sale_created: no active templates found — skipping.'
        )
        return

    queued = 0
    for template in active_templates:
        channels = (
            ['sms', 'whatsapp']
            if template.channel == NotificationTemplate.CHANNEL_BOTH
            else [template.channel]
        )
        for channel in channels:
            dispatch_notification.delay(instance.pk, template.pk, channel)
            queued += 1

    logger.info(
        'auto_notify_on_sale_created: queued %d task(s) for sale pk=%s',
        queued,
        instance.pk,
    )
