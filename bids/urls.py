# bids/urls.py
from django.urls import path
from .views import (
    BidListCreateView, BidRetrieveUpdateDestroyView,
    BidDocumentListCreateView, BidDocumentRetrieveUpdateDestroyView,
    EvaluationCriterionListCreateView, EvaluationCriterionRetrieveUpdateDestroyView,
    EvaluationResponseListCreateView, EvaluationResponseRetrieveUpdateDestroyView,
    ContractListCreateView, ContractRetrieveUpdateDestroyView,
    AuditLogListView
)

urlpatterns = [
    # Bid URLs
    path('bids/', BidListCreateView.as_view(), name='bid-list-create'),
    path('bids/<uuid:id>/', BidRetrieveUpdateDestroyView.as_view(), name='bid-detail'),  # Updated to uuid

    # BidDocument URLs
    path('bid-documents/', BidDocumentListCreateView.as_view(), name='bid-document-list-create'),
    path('bid-documents/<int:pk>/', BidDocumentRetrieveUpdateDestroyView.as_view(), name='bid-document-detail'),

    # EvaluationCriterion URLs
    path('evaluation-criteria/', EvaluationCriterionListCreateView.as_view(), name='evaluation-criterion-list-create'),
    path('evaluation-criteria/<int:id>/', EvaluationCriterionRetrieveUpdateDestroyView.as_view(), name='evaluation-criterion-detail'),

    # EvaluationResponse URLs
    path('evaluation-responses/', EvaluationResponseListCreateView.as_view(), name='evaluation-response-list-create'),
    path('evaluation-responses/<int:id>/', EvaluationResponseRetrieveUpdateDestroyView.as_view(), name='evaluation-response-detail'),

    # Contract URLs
    path('contracts/', ContractListCreateView.as_view(), name='contract-list-create'),
    path('contracts/<int:id>/', ContractRetrieveUpdateDestroyView.as_view(), name='contract-detail'),

    # AuditLog URLs
    path('audit-logs/', AuditLogListView.as_view(), name='audit-log-list'),
]