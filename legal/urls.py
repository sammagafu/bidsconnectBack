# legal/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PowerOfAttorneyViewSet

router = DefaultRouter()
router.register(r'power-of-attorney', PowerOfAttorneyViewSet, basename='power-of-attorney')

urlpatterns = [
    path('', include(router.urls)),
]