"""
Views for the CRM sales app.

Views
-----
DashboardView           — Executive KPI dashboard
chart_data              — JSON endpoint for Chart.js
SaleListView            — Paginated, filterable sales table
SaleCreateView          — Create a new sale
SaleUpdateView          — Edit an existing sale
SaleDeleteView          — Confirm & delete a sale
SaleDetailView          — Sale detail + message log
SendNotificationView    — POST-only: queue notification tasks
TemplateListView        — List notification templates
TemplateCreateView      — Create a notification template
TemplateUpdateView      — Edit a notification template
TemplateDeleteView      — Delete a notification template
SettingsView            — CRM settings singleton form
"""

import json
import logging
from datetime import date, timedelta

from django.contrib import messages
from django.db.models import Avg, Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import CRMSettingsForm, NotificationTemplateForm, SaleForm
from .models import CRMSettings, MessageLog, NotificationTemplate, Sale
from .tasks import dispatch_notification

logger = logging.getLogger(__name__)


# ===========================================================================
# Dashboard
# ===========================================================================

class DashboardView(TemplateView):
    template_name = 'sales/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # KPI aggregates
        aggregates = Sale.objects.aggregate(
            total_revenue=Sum('total_amount'),
            total_orders=Count('id'),
            avg_order_value=Avg('total_amount'),
        )
        ctx['total_revenue'] = aggregates['total_revenue'] or 0
        ctx['total_orders'] = aggregates['total_orders'] or 0
        ctx['avg_order_value'] = aggregates['avg_order_value'] or 0
        ctx['messages_sent'] = MessageLog.objects.filter(
            status=MessageLog.STATUS_SENT
        ).count()

        # Recent activity
        ctx['recent_sales'] = (
            Sale.objects.select_related()
            .order_by('-created_at')[:10]
        )

        # Status breakdown for quick stats
        ctx['pending_count'] = Sale.objects.filter(status=Sale.STATUS_PENDING).count()
        ctx['completed_count'] = Sale.objects.filter(status=Sale.STATUS_COMPLETED).count()
        ctx['followed_up_count'] = Sale.objects.filter(status=Sale.STATUS_FOLLOWED_UP).count()

        return ctx


# ===========================================================================
# Chart data API
# ===========================================================================

def chart_data(request):
    """
    Return JSON payload for the Chart.js sales trend chart.

    Response shape:
    {
        "labels": ["2024-01-01", ...],   # last 30 days
        "revenue": [1234.50, ...],
        "orders":  [5, ...]
    }
    """
    today = date.today()
    labels, revenue_data, order_data = [], [], []

    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        agg = Sale.objects.filter(created_at__date=day).aggregate(
            revenue=Sum('total_amount'),
            orders=Count('id'),
        )
        labels.append(day.strftime('%b %d'))
        revenue_data.append(float(agg['revenue'] or 0))
        order_data.append(agg['orders'] or 0)

    return JsonResponse({
        'labels': labels,
        'revenue': revenue_data,
        'orders': order_data,
    })


# ===========================================================================
# Sales CRUD
# ===========================================================================

class SaleListView(ListView):
    model = Sale
    template_name = 'sales/sale_list.html'
    context_object_name = 'sales'
    paginate_by = 20

    def get_queryset(self):
        qs = Sale.objects.all()
        params = self.request.GET

        # Text search
        q = params.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(customer_name__icontains=q)
                | Q(product_name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone_number__icontains=q)
            )

        # Status filter
        status = params.get('status', '').strip()
        if status:
            qs = qs.filter(status=status)

        # Date range filter
        date_from = params.get('date_from', '').strip()
        date_to = params.get('date_to', '').strip()
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['status_filter'] = self.request.GET.get('status', '')
        ctx['date_from'] = self.request.GET.get('date_from', '')
        ctx['date_to'] = self.request.GET.get('date_to', '')
        ctx['status_choices'] = Sale.STATUS_CHOICES
        ctx['total_count'] = self.get_queryset().count()
        return ctx


class SaleCreateView(CreateView):
    model = Sale
    form_class = SaleForm
    template_name = 'sales/sale_form.html'
    success_url = reverse_lazy('sales:sale_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'New Sale'
        ctx['submit_label'] = 'Create Sale'
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Sale for <strong>{self.object.customer_name}</strong> created successfully.',
        )
        return response


class SaleUpdateView(UpdateView):
    model = Sale
    form_class = SaleForm
    template_name = 'sales/sale_form.html'

    def get_success_url(self):
        return reverse_lazy('sales:sale_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'Edit Sale #{self.object.pk}'
        ctx['submit_label'] = 'Save Changes'
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Sale updated successfully.')
        return response


class SaleDeleteView(DeleteView):
    model = Sale
    template_name = 'sales/sale_confirm_delete.html'
    success_url = reverse_lazy('sales:sale_list')

    def form_valid(self, form):
        sale = self.get_object()
        messages.success(
            self.request,
            f'Sale for <strong>{sale.customer_name}</strong> deleted.',
        )
        return super().form_valid(form)


class SaleDetailView(DetailView):
    model = Sale
    template_name = 'sales/sale_detail.html'
    context_object_name = 'sale'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['message_logs'] = self.object.message_logs.select_related('template').all()
        ctx['active_templates'] = NotificationTemplate.objects.filter(is_active=True)
        return ctx


# ===========================================================================
# Send Notification (POST-only)
# ===========================================================================

class SendNotificationView(View):
    """
    Queue one or all active notification templates for a specific sale.

    POST params (all optional):
        template_id — pk of a specific NotificationTemplate to send
        channel     — 'sms' | 'whatsapp' (used only with template_id)

    If template_id is not provided, all active templates are queued.
    """

    http_method_names = ['post']

    def post(self, request, pk):
        sale = get_object_or_404(Sale, pk=pk)
        template_id = request.POST.get('template_id', '').strip()
        channel = request.POST.get('channel', 'sms').strip()

        if template_id:
            template = get_object_or_404(NotificationTemplate, pk=template_id, is_active=True)
            channels = (
                ['sms', 'whatsapp']
                if template.channel == NotificationTemplate.CHANNEL_BOTH
                else [channel]
            )
            for ch in channels:
                dispatch_notification.delay(sale.pk, template.pk, ch)
            messages.success(
                request,
                f'Notification "<strong>{template.title}</strong>" queued for dispatch.',
            )
        else:
            # Send all active templates
            active_templates = NotificationTemplate.objects.filter(is_active=True)
            queued = 0
            for tmpl in active_templates:
                chs = (
                    ['sms', 'whatsapp']
                    if tmpl.channel == NotificationTemplate.CHANNEL_BOTH
                    else [tmpl.channel]
                )
                for ch in chs:
                    dispatch_notification.delay(sale.pk, tmpl.pk, ch)
                    queued += 1
            messages.success(
                request,
                f'{queued} notification task(s) queued for dispatch.',
            )

        return redirect('sales:sale_detail', pk=sale.pk)


# ===========================================================================
# Notification Templates CRUD
# ===========================================================================

class TemplateListView(ListView):
    model = NotificationTemplate
    template_name = 'sales/template_list.html'
    context_object_name = 'templates'
    paginate_by = 20


class TemplateCreateView(CreateView):
    model = NotificationTemplate
    form_class = NotificationTemplateForm
    template_name = 'sales/template_form.html'
    success_url = reverse_lazy('sales:template_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'New Template'
        ctx['submit_label'] = 'Create Template'
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Notification template created.')
        return response


class TemplateUpdateView(UpdateView):
    model = NotificationTemplate
    form_class = NotificationTemplateForm
    template_name = 'sales/template_form.html'
    success_url = reverse_lazy('sales:template_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'Edit Template: {self.object.title}'
        ctx['submit_label'] = 'Save Changes'
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Template updated successfully.')
        return response


class TemplateDeleteView(DeleteView):
    model = NotificationTemplate
    template_name = 'sales/template_confirm_delete.html'
    success_url = reverse_lazy('sales:template_list')

    def form_valid(self, form):
        obj = self.get_object()
        messages.success(self.request, f'Template "<strong>{obj.title}</strong>" deleted.')
        return super().form_valid(form)


# ===========================================================================
# Settings (singleton)
# ===========================================================================

class SettingsView(UpdateView):
    model = CRMSettings
    form_class = CRMSettingsForm
    template_name = 'sales/settings.html'
    success_url = reverse_lazy('sales:settings')

    def get_object(self, queryset=None):
        """Always return (or create) the singleton CRMSettings row."""
        return CRMSettings.load()

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Settings saved successfully.')
        return response
