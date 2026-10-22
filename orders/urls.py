"""
URL configuration for the Orders app.
All URLs are namespaced under 'orders'.
"""

from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    # ------------------------------------------------------------------
    # Sales Entry (main workflow)
    # ------------------------------------------------------------------
    path('orders/new/', views.order_entry, name='order_create'),
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),

    # ------------------------------------------------------------------
    # Client management
    # ------------------------------------------------------------------
    path('clients/', views.ClientListView.as_view(), name='client_list'),
    path('clients/new/', views.ClientCreateView.as_view(), name='client_create'),
    path('clients/<int:pk>/edit/', views.ClientUpdateView.as_view(), name='client_update'),

    # ------------------------------------------------------------------
    # Product / Inventory management
    # ------------------------------------------------------------------
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/new/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_update'),

    # ------------------------------------------------------------------
    # JSON API
    # ------------------------------------------------------------------
    path('api/products/', views.product_api, name='product_api'),
]
