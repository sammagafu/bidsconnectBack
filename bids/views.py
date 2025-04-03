# bids/views.py
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import (
    Bid, BidDocument, EvaluationCriterion, EvaluationResponse,
    Contract, AuditLog
)
from .serializers import (
    BidSerializer, BidDocumentSerializer, EvaluationCriterionSerializer,
    EvaluationResponseSerializer, ContractSerializer, AuditLogSerializer
)

class BidListCreateView(generics.ListCreateAPIView):
    queryset = Bid.objects.all()
    serializer_class = BidSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return queryset
        return queryset.filter(tender__status='published')

    def perform_create(self, serializer):
        serializer.save(bidder=self.request.user)

class BidRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    lookup_field = 'id'  # UUID is the primary key, so 'id' is fine

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_update(self, serializer):
        bid = self.get_object()
        if bid.status not in ['draft']:
            return Response({"detail": "Can only update draft bids."}, status=status.HTTP_403_FORBIDDEN)
        serializer.save()

    def perform_destroy(self, bid):
        if bid.status not in ['draft', 'withdrawn']:
            return Response({"detail": "Can only delete draft or withdrawn bids."}, status=status.HTTP_403_FORBIDDEN)
        bid.delete()

class BidDocumentListCreateView(generics.ListCreateAPIView):
    queryset = BidDocument.objects.all()
    serializer_class = BidDocumentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        bid = get_object_or_404(Bid, id=self.request.data.get('bid'))
        if bid.bidder != self.request.user and not self.request.user.is_staff:
            return Response({"detail": "You can only upload documents for your own bids."}, status=status.HTTP_403_FORBIDDEN)
        serializer.save()

class BidDocumentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BidDocument.objects.all()
    serializer_class = BidDocumentSerializer
    permission_classes = [IsAuthenticated]

class EvaluationCriterionListCreateView(generics.ListCreateAPIView):
    queryset = EvaluationCriterion.objects.all()
    serializer_class = EvaluationCriterionSerializer
    permission_classes = [IsAdminUser]

class EvaluationCriterionRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = EvaluationCriterion.objects.all()
    serializer_class = EvaluationCriterionSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'id'

class EvaluationResponseListCreateView(generics.ListCreateAPIView):
    queryset = EvaluationResponse.objects.all()
    serializer_class = EvaluationResponseSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(evaluated_by=self.request.user)

class EvaluationResponseRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = EvaluationResponse.objects.all()
    serializer_class = EvaluationResponseSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'id'

class ContractListCreateView(generics.ListCreateAPIView):
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(signed_by=self.request.user)

class ContractRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'id'

class AuditLogListView(generics.ListAPIView):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]