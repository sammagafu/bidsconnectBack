# accounts/notifications.py
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import CompanyDocument
from .constants import DOCUMENT_EXPIRY_NOTIFICATION_DAYS

def send_document_expiry_notification(document):
    """Send email notification for document nearing expiry"""
    subject = f"Document Expiry Alert: {document.get_document_type_display()}"
    expiry_date = document.expires_at.strftime('%Y-%m-%d')
    message = (
        f"Dear {document.company.owner.get_full_name() or document.company.owner.email},\n\n"
        f"The following document is nearing its expiry date:\n\n"
        f"Company: {document.company.name}\n"
        f"Document Type: {document.get_document_type_display()}\n"
        f"Category: {document.get_document_category_display()}\n"
        f"Expiry Date: {expiry_date}\n\n"
        f"Please review and update the document if necessary.\n\n"
        f"Best regards,\n"
        f"Your Company Management System"
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
        # Log the error (you might want to use proper logging)
        print(f"Failed to send notification for document {document.id}: {str(e)}")
        return False

def check_and_notify_expiring_documents():
    """Check for documents nearing expiry and send notifications"""
    notification_threshold = timezone.now() + timedelta(
        days=DOCUMENT_EXPIRY_NOTIFICATION_DAYS
    )
    
    # Get documents expiring within the notification period
    expiring_documents = CompanyDocument.objects.filter(
        is_expired=False,
        expires_at__lte=notification_threshold,
        expires_at__gt=timezone.now(),
        company__deleted_at__isnull=True,
        # Add a field to track if notification was sent
        notification_sent=False
    ).select_related('company', 'company__owner')
    
    success_count = 0
    failure_count = 0
    
    for document in expiring_documents:
        if send_document_expiry_notification(document):
            document.notification_sent = True
            document.save(update_fields=['notification_sent'])
            success_count += 1
        else:
            failure_count += 1
    
    return {
        'total_processed': success_count + failure_count,
        'successful': success_count,
        'failed': failure_count
    }