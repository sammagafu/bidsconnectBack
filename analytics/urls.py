from django.urls import path
from .views import AnalyticsDashboardView, AnalyticsReadyView

app_name = 'analytics'
urlpatterns = [
    path('', AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
    path('ping/', AnalyticsReadyView.as_view(), name='analytics-ready'),
]
