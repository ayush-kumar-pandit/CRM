from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('api/chart-data/', views.chart_data, name='chart_data'),
    path('sales/', views.SaleListView.as_view(), name='sale_list'),
    path('sales/new/', views.SaleCreateView.as_view(), name='sale_create'),
    path('sales/<int:pk>/', views.SaleDetailView.as_view(), name='sale_detail'),
    path('sales/<int:pk>/edit/', views.SaleUpdateView.as_view(), name='sale_update'),
    path('sales/<int:pk>/delete/', views.SaleDeleteView.as_view(), name='sale_delete'),
    path('sales/<int:pk>/send/', views.SendNotificationView.as_view(), name='sale_send_notification'),
    path('templates/', views.TemplateListView.as_view(), name='template_list'),
    path('templates/new/', views.TemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:pk>/edit/', views.TemplateUpdateView.as_view(), name='template_update'),
    path('templates/<int:pk>/delete/', views.TemplateDeleteView.as_view(), name='template_delete'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
]
