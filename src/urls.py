"""
URL configuration for src project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('notifications/', include(('notifications.urls', 'notifications'), namespace='notifications')),
    path('', include(('app.urls', 'app'), namespace='app')),
    path('', include('app.urls')),
]
