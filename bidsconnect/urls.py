from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/accounts/', include('djoser.urls')),  # Djoser endpoints
    path('api/v1/accounts/', include('djoser.urls.authtoken')),
    path('api/v1/accounts/', include('accounts.urls')),
]
