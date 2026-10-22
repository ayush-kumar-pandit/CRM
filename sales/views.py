import json
from datetime import date, timedelta
from django.contrib import messages
from django.db.models import Avg, Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView
from .forms import CRMSettingsForm, NotificationTemplateForm, SaleForm
from .models import CRMSettings, MessageLog, NotificationTemplate, Sale
from .tasks import dispatch_notification


class DashboardView(TemplateView):
    template_name = 'sales/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        agg = Sale.objects.aggregate(
            total_revenue=Sum('total_amount'), total_orders=Count('id'), avg_order_value=Avg('total_amount')
        )
        ctx.update({
            'total_revenue': agg['total_revenue'] or 0,
            'total_orders': agg['total_orders'] or 0,
            'avg_order_value': agg['avg_order_value'] or 0,
            'messages_sent': MessageLog.objects.filter(status='sent').count(),
            'recent_sales': Sale.objects.order_by('-created_at')[:10],
            'pending_count': Sale.objects.filter(status='pending').count(),
            'completed_count': Sale.objects.filter(status='completed').count(),
            'followed_up_count': Sale.objects.filter(status='followed_up').count(),
        })
        return ctx


def chart_data(request):
    today = date.today()
    labels, revenue_data, order_data = [], [], []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        agg = Sale.objects.filter(created_at__date=day).aggregate(revenue=Sum('total_amount'), orders=Count('id'))
        labels.append(day.strftime('%b %d'))
        revenue_data.append(float(agg['revenue'] or 0))
        order_data.append(agg['orders'] or 0)
    return JsonResponse({'labels': labels, 'revenue': revenue_data, 'orders': order_data})


class SaleListView(ListView):
    model = Sale
    template_name = 'sales/sale_list.html'
    context_object_name = 'sales'
    paginate_by = 20

    def get_queryset(self):
        qs = Sale.objects.all()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(customer_name__icontains=q) | Q(product_name__icontains=q) | Q(email__icontains=q))
        status = self.request.GET.get('status', '')
        if status:
            qs = qs.filter(status=status)
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'q': self.request.GET.get('q', ''), 'status_filter': self.request.GET.get('status', ''),
                    'date_from': self.request.GET.get('date_from', ''), 'date_to': self.request.GET.get('date_to', ''),
                    'status_choices': Sale.STATUS_CHOICES, 'total_count': self.get_queryset().count()})
        return ctx


class SaleCreateView(CreateView):
    model = Sale
    form_class = SaleForm
    template_name = 'sales/sale_form.html'
    success_url = reverse_lazy('sales:sale_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'page_title': 'New Sale', 'submit_label': 'Create Sale'})
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Sale for <strong>{self.object.customer_name}</strong> created.')
        return response


class SaleUpdateView(UpdateView):
    model = Sale
    form_class = SaleForm
    template_name = 'sales/sale_form.html'

    def get_success_url(self):
        return reverse_lazy('sales:sale_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'page_title': f'Edit Sale #{self.object.pk}', 'submit_label': 'Save Changes'})
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Sale updated.')
        return response


class SaleDeleteView(DeleteView):
    model = Sale
    template_name = 'sales/sale_confirm_delete.html'
    success_url = reverse_lazy('sales:sale_list')

    def form_valid(self, form):
        messages.success(self.request, f'Sale deleted.')
        return super().form_valid(form)


class SaleDetailView(DetailView):
    model = Sale
    template_name = 'sales/sale_detail.html'
    context_object_name = 'sale'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'message_logs': self.object.message_logs.all(),
                    'active_templates': NotificationTemplate.objects.filter(is_active=True)})
        return ctx


class SendNotificationView(View):
    http_method_names = ['post']

    def post(self, request, pk):
        sale = get_object_or_404(Sale, pk=pk)
        template_id = request.POST.get('template_id', '').strip()
        channel = request.POST.get('channel', 'sms')
        if template_id:
            template = get_object_or_404(NotificationTemplate, pk=template_id, is_active=True)
            channels = ['sms', 'whatsapp'] if template.channel == 'both' else [channel]
            for ch in channels:
                dispatch_notification.delay(sale.pk, template.pk, ch)
            messages.success(request, 'Notification queued.')
        else:
            templates = NotificationTemplate.objects.filter(is_active=True)
            for tmpl in templates:
                chs = ['sms', 'whatsapp'] if tmpl.channel == 'both' else [tmpl.channel]
                for ch in chs:
                    dispatch_notification.delay(sale.pk, tmpl.pk, ch)
            messages.success(request, f'{templates.count()} notification(s) queued.')
        return redirect('sales:sale_detail', pk=sale.pk)


class TemplateListView(ListView):
    model = NotificationTemplate
    template_name = 'sales/template_list.html'
    context_object_name = 'templates'


class TemplateCreateView(CreateView):
    model = NotificationTemplate
    form_class = NotificationTemplateForm
    template_name = 'sales/template_form.html'
    success_url = reverse_lazy('sales:template_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'page_title': 'New Template', 'submit_label': 'Create Template'})
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Template created.')
        return response


class TemplateUpdateView(UpdateView):
    model = NotificationTemplate
    form_class = NotificationTemplateForm
    template_name = 'sales/template_form.html'
    success_url = reverse_lazy('sales:template_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'page_title': f'Edit: {self.object.title}', 'submit_label': 'Save Changes'})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Template updated.')
        return super().form_valid(form)


class TemplateDeleteView(DeleteView):
    model = NotificationTemplate
    template_name = 'sales/template_confirm_delete.html'
    success_url = reverse_lazy('sales:template_list')

    def form_valid(self, form):
        messages.success(self.request, 'Template deleted.')
        return super().form_valid(form)


class SettingsView(UpdateView):
    model = CRMSettings
    form_class = CRMSettingsForm
    template_name = 'sales/settings.html'
    success_url = reverse_lazy('sales:settings')

    def get_object(self, queryset=None):
        return CRMSettings.load()

    def form_valid(self, form):
        messages.success(self.request, 'Settings saved.')
        return super().form_valid(form)
