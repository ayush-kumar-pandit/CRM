from django.contrib import admin
from .models import CRMSettings, MessageLog, NotificationTemplate, Sale


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'product_name', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('customer_name', 'email', 'phone_number')
    readonly_fields = ('total_amount', 'created_at', 'updated_at')


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'channel', 'is_active', 'created_at')
    list_filter = ('channel', 'is_active')


@admin.register(MessageLog)
class MessageLogAdmin(admin.ModelAdmin):
    list_display = ('sale', 'channel', 'recipient', 'status', 'sent_at')
    readonly_fields = ('sale', 'template', 'channel', 'recipient', 'payload', 'status', 'error_message', 'sent_at')

    def has_add_permission(self, request):
        return False


@admin.register(CRMSettings)
class CRMSettingsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'auto_send_enabled')

    def has_add_permission(self, request):
        return not CRMSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
