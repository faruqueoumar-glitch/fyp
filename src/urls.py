"""
URL configuration for src project.
"""
from django.contrib import admin
from django.urls import path, include
from app.keep_alive import ping_server

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ping/', ping_server, name='ping'),
    path('notifications/', include(('notifications.urls', 'notifications'), namespace='notifications')),
    path('', include(('app.urls', 'app'), namespace='app')),
    path('', include('app.urls')),
]
