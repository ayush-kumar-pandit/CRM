from django.db import models


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
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    product_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)
    shipping_address = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        self.total_amount = self.quantity * self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer_name} — {self.product_name}"


class NotificationTemplate(models.Model):
    CHANNEL_SMS = 'sms'
    CHANNEL_WHATSAPP = 'whatsapp'
    CHANNEL_BOTH = 'both'
    CHANNEL_CHOICES = [
        (CHANNEL_SMS, 'SMS'),
        (CHANNEL_WHATSAPP, 'WhatsApp'),
        (CHANNEL_BOTH, 'Both'),
    ]

    title = models.CharField(max_length=255)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default=CHANNEL_SMS)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def render(self, sale):
        return self.body.format(
            customer_name=sale.customer_name,
            product_name=sale.product_name,
            quantity=sale.quantity,
            total_amount=sale.total_amount,
            status=sale.get_status_display(),
        )

    def __str__(self):
        return self.title


class MessageLog(models.Model):
    STATUS_QUEUED = 'queued'
    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_QUEUED, 'Queued'),
        (STATUS_SENT, 'Sent'),
        (STATUS_FAILED, 'Failed'),
    ]
    CHANNEL_CHOICES = [('sms', 'SMS'), ('whatsapp', 'WhatsApp')]

    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='message_logs')
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    recipient = models.CharField(max_length=30)
    payload = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.get_channel_display()} → {self.recipient} [{self.get_status_display()}]"


class CRMSettings(models.Model):
    auto_send_enabled = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'CRM Settings'
        verbose_name_plural = 'CRM Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'CRM Settings'
