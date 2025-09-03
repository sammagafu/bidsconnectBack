from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BidViewSet, BidDocumentViewSet, BidFinancialResponseViewSet,
    BidTurnoverResponseViewSet, BidExperienceResponseViewSet,
    BidPersonnelResponseViewSet, BidOfficeResponseViewSet,
    BidSourceResponseViewSet, BidLitigationResponseViewSet,
    BidScheduleResponseViewSet, BidTechnicalResponseViewSet,
    BidEvaluationViewSet, BidAuditLogViewSet
)

app_name = 'bids'

router = DefaultRouter()
router.register(r'', BidViewSet, basename='bid')

bid_submit = BidViewSet.as_view({'post': 'submit'})

document_list = BidDocumentViewSet.as_view({'get': 'list', 'post': 'create'})
document_detail = BidDocumentViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})

financial_response_list = BidFinancialResponseViewSet.as_view({'get': 'list', 'post': 'create'})
financial_response_detail = BidFinancialResponseViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})

turnover_response_list = BidTurnoverResponseViewSet.as_view({'get': 'list', 'post': 'create'})
turnover_response_detail = BidTurnoverResponseViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})

experience_response_list = BidExperienceResponseViewSet.as_view({'get': 'list', 'post': 'create'})
experience_response_detail = BidExperienceResponseViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})

personnel_response_list = BidPersonnelResponseViewSet.as_view({'get': 'list', 'post': 'create'})
personnel_response_detail = BidPersonnelResponseViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})

office_response_list = BidOfficeResponseViewSet.as_view({'get': 'list', 'post': 'create'})
office_response_detail = BidOfficeResponseViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})

source_response_list = BidSourceResponseViewSet.as_view({'get': 'list', 'post': 'create'})
source_response_detail = BidSourceResponseViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})

litigation_response_list = BidLitigationResponseViewSet.as_view({'get': 'list', 'post': 'create'})
litigation_response_detail = BidLitigationResponseViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})

schedule_response_list = BidScheduleResponseViewSet.as_view({'get': 'list', 'post': 'create'})
schedule_response_detail = BidScheduleResponseViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})

technical_response_list = BidTechnicalResponseViewSet.as_view({'get': 'list', 'post': 'create'})
technical_response_detail = BidTechnicalResponseViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})

evaluation_list = BidEvaluationViewSet.as_view({'get': 'list', 'post': 'create'})
evaluation_detail = BidEvaluationViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})

audit_log_list = BidAuditLogViewSet.as_view({'get': 'list'})
audit_log_detail = BidAuditLogViewSet.as_view({'get': 'retrieve'})

urlpatterns = [
    path('', include(router.urls)),
    path('<int:pk>/submit/', bid_submit, name='bid-submit'),

    path('<int:bid_pk>/documents/', document_list, name='bid-document-list'),
    path('<int:bid_pk>/documents/<int:pk>/', document_detail, name='bid-document-detail'),

    path('<int:bid_pk>/financial-responses/', financial_response_list, name='bid-financial-response-list'),
    path('<int:bid_pk>/financial-responses/<int:pk>/', financial_response_detail, name='bid-financial-response-detail'),

    path('<int:bid_pk>/turnover-responses/', turnover_response_list, name='bid-turnover-response-list'),
    path('<int:bid_pk>/turnover-responses/<int:pk>/', turnover_response_detail, name='bid-turnover-response-detail'),

    path('<int:bid_pk>/experience-responses/', experience_response_list, name='bid-experience-response-list'),
    path('<int:bid_pk>/experience-responses/<int:pk>/', experience_response_detail, name='bid-experience-response-detail'),

    path('<int:bid_pk>/personnel-responses/', personnel_response_list, name='bid-personnel-response-list'),
    path('<int:bid_pk>/personnel-responses/<int:pk>/', personnel_response_detail, name='bid-personnel-response-detail'),

    path('<int:bid_pk>/office-responses/', office_response_list, name='bid-office-response-list'),
    path('<int:bid_pk>/office-responses/<int:pk>/', office_response_detail, name='bid-office-response-detail'),

    path('<int:bid_pk>/source-responses/', source_response_list, name='bid-source-response-list'),
    path('<int:bid_pk>/source-responses/<int:pk>/', source_response_detail, name='bid-source-response-detail'),

    path('<int:bid_pk>/litigation-responses/', litigation_response_list, name='bid-litigation-response-list'),
    path('<int:bid_pk>/litigation-responses/<int:pk>/', litigation_response_detail, name='bid-litigation-response-detail'),

    path('<int:bid_pk>/schedule-responses/', schedule_response_list, name='bid-schedule-response-list'),
    path('<int:bid_pk>/schedule-responses/<int:pk>/', schedule_response_detail, name='bid-schedule-response-detail'),

    path('<int:bid_pk>/technical-responses/', technical_response_list, name='bid-technical-response-list'),
    path('<int:bid_pk>/technical-responses/<int:pk>/', technical_response_detail, name='bid-technical-response-detail'),

    path('<int:bid_pk>/evaluations/', evaluation_list, name='bid-evaluation-list'),
    path('<int:bid_pk>/evaluations/<int:pk>/', evaluation_detail, name='bid-evaluation-detail'),

    path('<int:bid_pk>/audit-logs/', audit_log_list, name='bid-audit-log-list'),
    path('<int:bid_pk>/audit-logs/<int:pk>/', audit_log_detail, name='bid-audit-log-detail'),
]