from rest_framework import serializers
from .models import Payment
from django.contrib.auth import get_user_model

User = get_user_model()

class PaymentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'content_type', 'object_id', 'order_tracking_id',
            'amount', 'currency', 'status', 'payment_method', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'order_tracking_id', 'created_at']