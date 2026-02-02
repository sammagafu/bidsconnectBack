from django.urls import path
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions


class AnalyticsReadyView(APIView):
    """Placeholder until analytics endpoints are implemented."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"app": "analytics", "status": "ready"})


app_name = 'analytics'
urlpatterns = [
    path('', AnalyticsReadyView.as_view(), name='analytics-ready'),
]
