from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/accounts/', include('djoser.urls')),
    path('api/v1/accounts/', include('djoser.urls.jwt')),
    path('api/v1/accounts/', include('accounts.urls')),
    path('api/v1/tenders/', include('tenders.urls')),
    path('api/v1/bids/', include('bids.urls')),
    path('api/v1/marketplaces/', include('marketplace.urls')),
    path('api/v1/legal-documents/', include('legal.urls')),
    path('api/v1/automation/', include('automation.urls')),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)