"""
Django Admin registrations for the Orders & Inventory app.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Client, Order, OrderItem, Product


# ---------------------------------------------------------------------------
# Inline: OrderItem inside Order
# ---------------------------------------------------------------------------

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('line_total_display',)
    fields = ('product', 'quantity', 'unit_price', 'line_total_display')

    @admin.display(description='Line Total')
    def line_total_display(self, obj):
        return f'₹{obj.line_total:,.2f}' if obj.pk else '—'


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'email', 'order_count', 'created_at')
    search_fields = ('name', 'email', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Orders')
    def order_count(self, obj):
        return obj.orders.count()


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock_badge', 'is_restocked', 'updated_at')
    list_filter = ('is_restocked',)
    search_fields = ('name',)
    list_editable = ('is_restocked',)
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Stock')
    def stock_badge(self, obj):
        color = '#059669' if obj.stock_quantity > 0 else '#dc2626'
        return format_html(
            '<span style="color:{}; font-weight:600">{}</span>',
            color,
            obj.stock_quantity,
        )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'total_amount', 'status', 'receipt_sent', 'created_at')
    list_filter = ('status', 'receipt_sent', 'created_at')
    search_fields = ('client__name', 'client__email', 'client__phone_number')
    readonly_fields = ('total_amount', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False  # Orders must be created through the sales entry UI


# ---------------------------------------------------------------------------
# OrderItem (standalone, for audit access)
# ---------------------------------------------------------------------------

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'unit_price', 'line_total_display')
    readonly_fields = ('order', 'product', 'quantity', 'unit_price')

    @admin.display(description='Line Total')
    def line_total_display(self, obj):
        return f'₹{obj.line_total:,.2f}'

    def has_add_permission(self, request):
        return False
