"""
URL configuration for src project.
"""
from django.contrib import admin
from django.urls import path, include
from app.keep_alive import ping_server
from app.views import healthz_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ping/', ping_server, name='ping'),
    path('healthz/', healthz_view, name='healthz_root'),
    path('notifications/', include(('notifications.urls', 'notifications'), namespace='notifications')),
    path('', include(('app.urls', 'app'), namespace='app')),
    path('', include('app.urls')),
]
