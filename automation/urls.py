# automation/urls.py
from django.urls import path
from .views import (
    PowerOfAttorneyView, TenderSecuringDeclarationView,
    LitigationHistoryView, CoverLetterView
)

urlpatterns = [
    path('power-of-attorney/', PowerOfAttorneyView.as_view(), name='power_of_attorney'),
    path('power-of-attorney/<uuid:id>/', PowerOfAttorneyView.as_view(), name='power_of_attorney_detail'),
    path('tender-securing-declaration/', TenderSecuringDeclarationView.as_view(), name='tender_securing_declaration'),
    path('tender-securing-declaration/<uuid:id>/', TenderSecuringDeclarationView.as_view(), name='tender_securing_declaration_detail'),
    path('litigation-history/', LitigationHistoryView.as_view(), name='litigation_history'),
    path('litigation-history/<uuid:id>/', LitigationHistoryView.as_view(), name='litigation_history_detail'),
    path('cover-letter/', CoverLetterView.as_view(), name='cover_letter'),
    path('cover-letter/<uuid:id>/', CoverLetterView.as_view(), name='cover_letter_detail'),
]