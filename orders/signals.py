"""
Signal handlers for the Orders app.

post_save on Order — immediately queue notification tasks when a new
order is created and confirmed.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Order

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def trigger_order_notifications(sender, instance: Order, created: bool, **kwargs):
    """
    Queue dispatch_order_notifications Celery task immediately when a
    new confirmed order is saved for the first time.
    """
    if not created:
        return
    if instance.status != Order.STATUS_CONFIRMED:
        return

    from .tasks import dispatch_order_notifications  # noqa: PLC0415
    dispatch_order_notifications.delay(instance.pk)
    logger.info(
        'trigger_order_notifications: queued notifications for order #%s',
        instance.pk,
    )
