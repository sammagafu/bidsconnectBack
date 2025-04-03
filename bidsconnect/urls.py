from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/accounts/', include('djoser.urls')),
    path('api/v1/accounts/', include('djoser.urls.jwt')),
    path('api/v1/accounts/', include('accounts.urls')),
    path('api/v1/tenders/', include('tenders.urls')),
    path('api/v1/bids/', include('bids.urls')),
    path('api/v1/marketplaces/', include('marketplace.urls')),
    path('api/v1/legal-documents/', include('legal.urls')),
]