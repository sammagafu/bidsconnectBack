# bids/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from .models import Bid, BidDocument, AuditLog
from .serializers import BidSerializer, BidDocumentSerializer, AuditLogSerializer


class BidViewSet(viewsets.ModelViewSet):
    @action(detail=False, methods=['get'], url_path='by-company')
    def by_company(self, request):
        """
        Returns all bids submitted by a specific company. Pass company_id as a query parameter.
        """
        company_id = request.query_params.get('company_id')
        if not company_id:
            return Response({'detail': 'company_id query parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)
        qs = self.get_queryset().filter(company_id=company_id)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
    """
    Authenticated users can list/create/update their bids w/ nested docs.
    Admins can change any bid’s status.
    """
    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        user = self.request.user
        return Bid.objects.all() if user.is_staff else Bid.objects.filter(bidder=user)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        if self.action in ['update', 'partial_update']:
            ctx['bid_instance'] = self.get_object()
        return ctx

    def create(self, request, *args, **kwargs):
        # Ensure nested file uploads get saved
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser], url_path='change-status')
    def change_status(self, request, pk=None):
        bid = self.get_object()
        new_status = request.data.get('status')
        if new_status not in [c[0] for c in Bid.STATUS_CHOICES]:
            return Response({'detail': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)
        bid.status = new_status
        bid.save()
        return Response(self.get_serializer(bid).data)


class BidDocumentViewSet(viewsets.ModelViewSet):
    """
    CRUD on individual bid documents (supports file uploads).
    """
    queryset = BidDocument.objects.all()
    serializer_class = BidDocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only view of audit logs (admin only).
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]
