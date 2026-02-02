from django.urls import path
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions


class NotificationsReadyView(APIView):
    """Placeholder until notification endpoints are implemented."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"app": "notifications", "status": "ready"})


app_name = 'notifications'
urlpatterns = [
    path('', NotificationsReadyView.as_view(), name='notifications-ready'),
]
