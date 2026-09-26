"""
Data models for the CRM sales app.

Models
------
Sale                — Core customer order record
NotificationTemplate — Reusable message blueprint with placeholder support
MessageLog          — Immutable audit trail for every dispatched notification
CRMSettings         — Singleton configuration row (auto-send toggle, etc.)
"""

from django.db import models


# ---------------------------------------------------------------------------
# Sale
# ---------------------------------------------------------------------------

class Sale(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_FOLLOWED_UP = 'followed_up'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FOLLOWED_UP, 'Followed-Up'),
    ]

    customer_name = models.CharField(max_length=255)
    phone_number = models.CharField(
        max_length=20,
        help_text='International E.164 format, e.g. +919876543210',
    )
    email = models.EmailField()
    product_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False,
        default=0,
    )
    shipping_address = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'

    def save(self, *args, **kwargs):
        """Auto-calculate total_amount before every save."""
        self.total_amount = self.quantity * self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer_name} — {self.product_name} ({self.get_status_display()})"


# ---------------------------------------------------------------------------
# NotificationTemplate
# ---------------------------------------------------------------------------

class NotificationTemplate(models.Model):
    CHANNEL_SMS = 'sms'
    CHANNEL_WHATSAPP = 'whatsapp'
    CHANNEL_BOTH = 'both'

    CHANNEL_CHOICES = [
        (CHANNEL_SMS, 'SMS'),
        (CHANNEL_WHATSAPP, 'WhatsApp'),
        (CHANNEL_BOTH, 'Both (SMS + WhatsApp)'),
    ]

    title = models.CharField(max_length=255)
    channel = models.CharField(
        max_length=10,
        choices=CHANNEL_CHOICES,
        default=CHANNEL_SMS,
    )
    body = models.TextField(
        help_text=(
            'Supported placeholders: {customer_name}, {product_name}, '
            '{quantity}, {total_amount}, {status}'
        )
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']
        verbose_name = 'Notification Template'
        verbose_name_plural = 'Notification Templates'

    def render(self, sale: 'Sale') -> str:
        """Render the body with sale-specific values substituted."""
        return self.body.format(
            customer_name=sale.customer_name,
            product_name=sale.product_name,
            quantity=sale.quantity,
            total_amount=sale.total_amount,
            status=sale.get_status_display(),
        )

    def __str__(self):
        return f"{self.title} [{self.get_channel_display()}]"


# ---------------------------------------------------------------------------
# MessageLog
# ---------------------------------------------------------------------------

class MessageLog(models.Model):
    STATUS_QUEUED = 'queued'
    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_QUEUED, 'Queued'),
        (STATUS_SENT, 'Sent'),
        (STATUS_FAILED, 'Failed'),
    ]

    CHANNEL_CHOICES = [
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
    ]

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='message_logs',
    )
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='message_logs',
    )
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    recipient = models.CharField(max_length=30)
    payload = models.TextField()
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_QUEUED,
    )
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Message Log'
        verbose_name_plural = 'Message Logs'

    def __str__(self):
        return (
            f"{self.get_channel_display()} → {self.recipient} "
            f"[{self.get_status_display()}]"
        )


# ---------------------------------------------------------------------------
# CRMSettings (singleton)
# ---------------------------------------------------------------------------

class CRMSettings(models.Model):
    """
    Application-wide CRM configuration stored as a single database row.
    Always access via CRMSettings.load() — never instantiate directly.
    """

    auto_send_enabled = models.BooleanField(
        default=False,
        verbose_name='Auto-send notifications',
        help_text=(
            'When enabled, all active notification templates will be '
            'automatically dispatched via Celery when a new sale is created.'
        ),
    )

    class Meta:
        verbose_name = 'CRM Settings'
        verbose_name_plural = 'CRM Settings'

    def save(self, *args, **kwargs):
        """Enforce singleton — always write to pk=1."""
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> 'CRMSettings':
        """Return the singleton CRMSettings row, creating it if necessary."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'CRM Settings'
