from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from .models import Tender, TenderSubscription, NotificationPreference

@shared_task
def send_tender_digest(frequency):
    """
    Send a digest of new tenders to users based on their NotificationPreference frequency.
    frequency: 'daily' or 'weekly'
    """
    now = timezone.now()
    # Determine timeframe
    if frequency == 'daily':
        since = now - timezone.timedelta(days=1)
    elif frequency == 'weekly':
        since = now - timezone.timedelta(weeks=1)
    else:
        return

    # Fetch new tenders in timeframe
    new_tenders = Tender.objects.filter(created_at__gte=since)
    if not new_tenders.exists():
        return

    # For each user preference matching frequency
    prefs = NotificationPreference.objects.filter(notification_frequency=frequency)
    for pref in prefs:
        user = pref.user
        # Find user's subscribed categories
        subscriptions = TenderSubscription.objects.filter(user=user)
        # Filter tenders in those categories
        user_tenders = new_tenders.filter(category__in=[s.category for s in subscriptions])
        if not user_tenders.exists():
            continue
        # Build email content
        lines = [f"- {tender.title} (Published: {tender.publication_date})" for tender in user_tenders]
        message = (
            f"Hello {user.get_full_name() or user.username},\n\n"
            f"Here is your {frequency} tender digest for {since.date()} to {now.date()}:\n"
            + "\n".join(lines)
            + "\n\nVisit the site for more details."
        )
        send_mail(
            subject=f"Your {frequency.capitalize()} Tender Digest",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True
        )
