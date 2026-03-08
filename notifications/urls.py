from django.urls import path
from .views import NotificationsListView, NotificationMarkReadView, NotificationsReadyView

app_name = 'notifications'
urlpatterns = [
    path('', NotificationsListView.as_view(), name='notifications-list'),
    path('<str:pk>/', NotificationMarkReadView.as_view(), name='notification-detail'),
    path('ping/', NotificationsReadyView.as_view(), name='notifications-ready'),
]
