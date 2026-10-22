import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CRMSettings, NotificationTemplate, Sale

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Sale)
def auto_notify_on_sale_created(sender, instance, created, **kwargs):
    if not created:
        return
    settings = CRMSettings.load()
    if not settings.auto_send_enabled:
        return
    from .tasks import dispatch_notification
    for template in NotificationTemplate.objects.filter(is_active=True):
        channels = ['sms', 'whatsapp'] if template.channel == 'both' else [template.channel]
        for ch in channels:
            dispatch_notification.delay(instance.pk, template.pk, ch)
