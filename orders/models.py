"""
Data models for the Orders & Inventory app.

Models
------
Client      — Customer contact record (normalised, separate from CRM Sale)
Product     — Inventory item with stock tracking and restock flag
Order       — A completed sale linked to a Client
OrderItem   — One line item within an Order (Product × qty × unit_price)
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class Client(models.Model):
    """A customer contact. Phone stored in E.164 format."""

    name = models.CharField(max_length=255)
    phone_number = models.CharField(
        max_length=20,
        help_text='International E.164 format, e.g. +919876543210',
    )
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'

    def __str__(self):
        return f'{self.name} ({self.phone_number})'


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class Product(models.Model):
    """An inventory item."""

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    stock_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    is_restocked = models.BooleanField(
        default=False,
        help_text='Mark True when new stock arrives — triggers weekly restock alerts.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    @property
    def in_stock(self) -> bool:
        return self.stock_quantity > 0

    def __str__(self):
        return f'{self.name} (stock: {self.stock_quantity})'


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class Order(models.Model):
    """A completed customer order containing one or more OrderItems."""

    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='orders',
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        editable=False,
    )
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CONFIRMED,
    )
    receipt_sent = models.BooleanField(
        default=False,
        help_text='Set to True once WhatsApp receipt + email invoice are dispatched.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    def recalculate_total(self):
        """Recompute total_amount from related OrderItems and save."""
        total = sum(item.line_total for item in self.items.all())
        self.total_amount = total
        self.save(update_fields=['total_amount'])

    def __str__(self):
        return f'Order #{self.pk} — {self.client.name} (₹{self.total_amount})'


# ---------------------------------------------------------------------------
# OrderItem
# ---------------------------------------------------------------------------

class OrderItem(models.Model):
    """A single product line within an Order."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items',
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    @property
    def line_total(self) -> Decimal:
        return self.quantity * self.unit_price

    def __str__(self):
        return f'{self.product.name} × {self.quantity} @ ₹{self.unit_price}'
