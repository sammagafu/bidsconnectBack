from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import (
    Category, SubCategory, ProcurementProcess, Tender, TenderDocument,
    TenderSubscription, NotificationPreference, TenderNotification, TenderStatusHistory
)
from .serializers import (
    CategorySerializer, SubCategorySerializer, ProcurementProcessSerializer, TenderSerializer,
    TenderDocumentSerializer, TenderSubscriptionSerializer, NotificationPreferenceSerializer,
    TenderNotificationSerializer, TenderStatusHistorySerializer
)

# Existing ViewSets (assumed to be present, not modified)
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

class ProcurementProcessViewSet(viewsets.ModelViewSet):
    queryset = ProcurementProcess.objects.all()
    serializer_class = ProcurementProcessSerializer
    permission_classes = [permissions.IsAuthenticated]

class TenderViewSet(viewsets.ModelViewSet):
    queryset = Tender.objects.all()
    serializer_class = TenderSerializer
    permission_classes = [permissions.IsAuthenticated]

class TenderDocumentViewSet(viewsets.ModelViewSet):
    queryset = TenderDocument.objects.all()
    serializer_class = TenderDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

class TenderSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = TenderSubscription.objects.all()
    serializer_class = TenderSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    queryset = NotificationPreference.objects.all()
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

class TenderNotificationViewSet(viewsets.ModelViewSet):
    queryset = TenderNotification.objects.all()
    serializer_class = TenderNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

# New View for creating categories with subcategories
class CategoriesWithSubcategoriesView(APIView):
    def post(self, request):
        category_data = request.data.get('category')
        subcategories_data = request.data.get('subcategories', [])

        # Validate and save the category
        category_serializer = CategorySerializer(data=category_data)
        if category_serializer.is_valid():
            category = category_serializer.save()
        else:
            return Response(category_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Validate and save each subcategory
        for subcategory_data in subcategories_data:
            subcategory_data['category'] = category.id  # Link to the newly created category
            subcategory_serializer = SubCategorySerializer(data=subcategory_data)
            if subcategory_serializer.is_valid():
                subcategory_serializer.save()
            else:
                return Response(subcategory_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "Category and subcategories created successfully"},
            status=status.HTTP_201_CREATED
        )