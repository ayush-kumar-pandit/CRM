"""
Views for the Orders app.

Views
-----
OrderEntryView      — Dynamic multi-line-item sales entry form (GET + POST)
OrderListView       — Paginated order history
OrderDetailView     — Full order detail with items + notification status
ClientListView      — Client directory
ClientCreateView    — Add new client
ClientUpdateView    — Edit client
ProductListView     — Product / inventory management
ProductCreateView   — Add new product
ProductUpdateView   — Edit product
product_api         — JSON endpoint returning product catalogue for Alpine.js
"""

import json
import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import ClientForm, ProductForm
from .models import Client, Order, OrderItem, Product
from .tasks import dispatch_order_notifications

logger = logging.getLogger(__name__)


# ===========================================================================
# JSON API — Product catalogue for Alpine.js
# ===========================================================================

def product_api(request):
    """
    Return all in-stock products as JSON.
    Consumed by the order entry form's Alpine.js component.
    """
    products = Product.objects.filter(stock_quantity__gt=0).order_by('name')
    data = [
        {
            'id': p.pk,
            'name': p.name,
            'price': str(p.price),
            'stock': p.stock_quantity,
        }
        for p in products
    ]
    return JsonResponse({'products': data})


# ===========================================================================
# Order Entry
# ===========================================================================

def order_entry(request):
    """
    GET  — Render the interactive sales entry form.
    POST — Validate, create Order + OrderItems in an atomic transaction,
           deduct stock, and queue notification tasks.
    """
    clients = Client.objects.order_by('name')
    products_qs = Product.objects.filter(stock_quantity__gt=0).order_by('name')
    products_json = json.dumps([
        {'id': p.pk, 'name': p.name, 'price': str(p.price), 'stock': p.stock_quantity}
        for p in products_qs
    ])
    client_form = ClientForm()

    if request.method == 'POST':
        client_mode = request.POST.get('client_mode', 'existing')

        # ------------------------------------------------------------------
        # Resolve client
        # ------------------------------------------------------------------
        if client_mode == 'new':
            client_form = ClientForm(request.POST, prefix='nc')
            if not client_form.is_valid():
                messages.error(request, 'Please fix the client details below.')
                return render(request, 'orders/order_entry.html', {
                    'clients': clients,
                    'products_json': products_json,
                    'client_form': client_form,
                })
            client = client_form.save()
        else:
            client_id = request.POST.get('client_id', '').strip()
            if not client_id:
                messages.error(request, 'Please select a client.')
                return render(request, 'orders/order_entry.html', {
                    'clients': clients,
                    'products_json': products_json,
                    'client_form': client_form,
                })
            client = get_object_or_404(Client, pk=client_id)

        # ------------------------------------------------------------------
        # Parse items JSON
        # ------------------------------------------------------------------
        items_raw = request.POST.get('items_json', '[]')
        try:
            items_data = json.loads(items_raw)
        except (json.JSONDecodeError, ValueError):
            messages.error(request, 'Invalid order items. Please try again.')
            return render(request, 'orders/order_entry.html', {
                'clients': clients,
                'products_json': products_json,
                'client_form': client_form,
            })

        if not items_data:
            messages.error(request, 'Add at least one item to the order.')
            return render(request, 'orders/order_entry.html', {
                'clients': clients,
                'products_json': products_json,
                'client_form': client_form,
            })

        # ------------------------------------------------------------------
        # Validate items + create order atomically
        # ------------------------------------------------------------------
        try:
            with transaction.atomic():
                # Validate stock for all items before touching the DB
                validated = []
                for item in items_data:
                    try:
                        product_id = int(item.get('product_id', 0))
                        qty = int(item.get('quantity', 0))
                        unit_price = Decimal(str(item.get('unit_price', '0')))
                    except (ValueError, InvalidOperation):
                        raise ValueError(f'Invalid data in item: {item}')

                    if qty <= 0:
                        raise ValueError(f'Quantity must be ≥ 1.')
                    if unit_price <= 0:
                        raise ValueError(f'Unit price must be > 0.')

                    product = (
                        Product.objects.select_for_update().get(pk=product_id)
                    )
                    if product.stock_quantity < qty:
                        raise ValueError(
                            f'Insufficient stock for "{product.name}": '
                            f'available {product.stock_quantity}, requested {qty}.'
                        )
                    validated.append((product, qty, unit_price))

                # Compute total
                total = sum(p.price * 0 + qty * up for p, qty, up in validated)

                # Create Order
                order = Order.objects.create(
                    client=client,
                    total_amount=total,
                    notes=request.POST.get('notes', '').strip(),
                    status=Order.STATUS_CONFIRMED,
                )

                # Create OrderItems + deduct stock
                for product, qty, unit_price in validated:
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=qty,
                        unit_price=unit_price,
                    )
                    product.stock_quantity -= qty
                    product.save(update_fields=['stock_quantity'])

                # Recalculate from DB for accuracy
                order.recalculate_total()

        except Product.DoesNotExist:
            messages.error(request, 'One of the selected products no longer exists.')
            return render(request, 'orders/order_entry.html', {
                'clients': clients,
                'products_json': products_json,
                'client_form': client_form,
            })
        except ValueError as exc:
            messages.error(request, str(exc))
            return render(request, 'orders/order_entry.html', {
                'clients': clients,
                'products_json': products_json,
                'client_form': client_form,
            })

        # ------------------------------------------------------------------
        # Queue notifications (signal also fires, but we call explicitly
        # here so it works even without signals active in tests)
        # ------------------------------------------------------------------
        # The post_save signal already queued this; no double-queue needed.
        # dispatch_order_notifications.delay(order.pk)

        messages.success(
            request,
            f'Order #{order.pk} for <strong>{client.name}</strong> created! '
            f'WhatsApp receipt and email invoice are being sent.',
        )
        return redirect('orders:order_detail', pk=order.pk)

    return render(request, 'orders/order_entry.html', {
        'clients': clients,
        'products_json': products_json,
        'client_form': client_form,
    })


# ===========================================================================
# Order List & Detail
# ===========================================================================

class OrderListView(ListView):
    model = Order
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        qs = Order.objects.select_related('client').prefetch_related('items')
        q = self.request.GET.get('q', '').strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(client__name__icontains=q)
                | Q(client__email__icontains=q)
                | Q(client__phone_number__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class OrderDetailView(DetailView):
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return Order.objects.select_related('client').prefetch_related('items__product')


# ===========================================================================
# Client CRUD
# ===========================================================================

class ClientListView(ListView):
    model = Client
    template_name = 'orders/client_list.html'
    context_object_name = 'clients'
    paginate_by = 25

    def get_queryset(self):
        qs = Client.objects.all()
        q = self.request.GET.get('q', '').strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(name__icontains=q) | Q(email__icontains=q) | Q(phone_number__icontains=q)
            )
        return qs


class ClientCreateView(CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'orders/client_form.html'
    success_url = reverse_lazy('orders:client_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'New Client'
        ctx['submit_label'] = 'Add Client'
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Client <strong>{self.object.name}</strong> added.')
        return response


class ClientUpdateView(UpdateView):
    model = Client
    form_class = ClientForm
    template_name = 'orders/client_form.html'
    success_url = reverse_lazy('orders:client_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'Edit — {self.object.name}'
        ctx['submit_label'] = 'Save Changes'
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Client updated.')
        return response


# ===========================================================================
# Product CRUD
# ===========================================================================

class ProductListView(ListView):
    model = Product
    template_name = 'orders/product_list.html'
    context_object_name = 'products'
    paginate_by = 25


class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'orders/product_form.html'
    success_url = reverse_lazy('orders:product_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'New Product'
        ctx['submit_label'] = 'Add Product'
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Product <strong>{self.object.name}</strong> added.')
        return response


class ProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'orders/product_form.html'
    success_url = reverse_lazy('orders:product_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'Edit — {self.object.name}'
        ctx['submit_label'] = 'Save Changes'
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Product updated.')
        return response
