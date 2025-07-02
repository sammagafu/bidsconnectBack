# accounts/notifications.py

import logging
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from .models import CompanyDocument
from .constants import DOCUMENT_EXPIRY_NOTIFICATION_DAYS

logger = logging.getLogger(__name__)


def send_document_expiry_notification(document):
    subject = f"Document Expiry Alert: {document.get_document_type_display()}"
    expiry = document.expires_at.strftime('%Y-%m-%d')
    message = (
        f"Dear {document.company.owner.get_full_name() or document.company.owner.email},\n\n"
        f"Your document '{document.document_file.name}' for company '{document.company.name}' "
        f"is expiring on {expiry}.\nPlease renew it before expiry.\n\n"
        "Best regards,\nCompany Management System"
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[document.company.owner.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send expiry notification for doc {document.id}: {e}")
        return False


def check_and_notify_expiring_documents():
    threshold = timezone.now() + timedelta(days=DOCUMENT_EXPIRY_NOTIFICATION_DAYS)
    docs = CompanyDocument.objects.filter(
        is_expired=False,
        expires_at__lte=threshold,
        expires_at__gt=timezone.now(),
        company__deleted_at__isnull=True
    ).select_related('company')

    success = 0
    failure = 0
    for doc in docs:
        if send_document_expiry_notification(doc):
            doc.notification_sent[str(DOCUMENT_EXPIRY_NOTIFICATION_DAYS)] = True
            doc.save(update_fields=['notification_sent'])
            success += 1
        else:
            failure += 1

    return {'total': success + failure, 'sent': success, 'failed': failure}
