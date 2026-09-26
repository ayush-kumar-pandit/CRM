"""
URL configuration for the CRM project.

All application routes are delegated to the `sales` app; the Django admin
is mounted at /admin/.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('sales.urls')),
]
