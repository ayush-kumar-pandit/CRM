"""
Django Admin registrations for the CRM sales app.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import CRMSettings, MessageLog, NotificationTemplate, Sale


# ---------------------------------------------------------------------------
# Sale
# ---------------------------------------------------------------------------

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        'customer_name', 'product_name', 'quantity',
        'price', 'total_amount', 'status_badge', 'created_at',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('customer_name', 'product_name', 'email', 'phone_number')
    readonly_fields = ('total_amount', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Customer Information', {
            'fields': ('customer_name', 'email', 'phone_number'),
        }),
        ('Order Details', {
            'fields': ('product_name', 'quantity', 'price', 'total_amount'),
        }),
        ('Fulfilment', {
            'fields': ('shipping_address', 'status', 'notes'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'pending': '#b45309',
            'completed': '#059669',
            'followed_up': '#4f46e5',
        }
        color = colors.get(obj.status, '#64748b')
        return format_html(
            '<span style="color:{}; font-weight:600">{}</span>',
            color,
            obj.get_status_display(),
        )


# ---------------------------------------------------------------------------
# NotificationTemplate
# ---------------------------------------------------------------------------

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'channel', 'is_active', 'created_at')
    list_filter = ('channel', 'is_active')
    search_fields = ('title', 'body')
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(boolean=True, description='Active')
    def is_active(self, obj):
        return obj.is_active


# ---------------------------------------------------------------------------
# MessageLog
# ---------------------------------------------------------------------------

@admin.register(MessageLog)
class MessageLogAdmin(admin.ModelAdmin):
    list_display = ('sale', 'channel', 'recipient', 'status', 'sent_at')
    list_filter = ('channel', 'status', 'sent_at')
    search_fields = ('recipient', 'payload', 'sale__customer_name')
    readonly_fields = (
        'sale', 'template', 'channel', 'recipient',
        'payload', 'status', 'error_message', 'sent_at',
    )
    ordering = ('-sent_at',)

    def has_add_permission(self, request):
        return False  # Logs are system-generated; never add manually


# ---------------------------------------------------------------------------
# CRMSettings (singleton)
# ---------------------------------------------------------------------------

@admin.register(CRMSettings)
class CRMSettingsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'auto_send_enabled')

    def has_add_permission(self, request):
        # Prevent creating more than one settings row
        return not CRMSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False  # Never allow deletion of the singleton
