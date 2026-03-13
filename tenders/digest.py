"""
Tender digest: send a summary of new (published) tenders to users who subscribe
to categories/subcategories/procurement processes, based on their notification frequency.
"""
import logging
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.db.models import Q

logger = logging.getLogger(__name__)


def get_tenders_for_subscription(subscription, tender_queryset):
    """
    Return tenders from tender_queryset that match this subscription
    (by category, subcategory, or procurement_process).
    """
    q = Q()
    if subscription.category_id:
        q |= Q(category_id=subscription.category_id)
    if subscription.subcategory_id:
        q |= Q(subcategory_id=subscription.subcategory_id)
    if subscription.procurement_process_id:
        q |= Q(procurement_process_id=subscription.procurement_process_id)
    if not q:
        return tender_queryset.none()
    return tender_queryset.filter(q).distinct()


def build_and_send_tender_digests(frequency):
    """
    Send a digest of new published tenders to users who have subscribed to
    categories (or subcategories/procurement processes) and have notification
    frequency set to `frequency`.

    frequency: 'daily' or 'weekly'

    Returns dict with keys: sent_count, skipped_no_pref, skipped_no_tenders, error_count.
    """
    assert frequency in ('daily', 'weekly'), "frequency must be 'daily' or 'weekly'"
    now = timezone.now()
    if frequency == 'daily':
        since = now - timezone.timedelta(days=1)
    else:
        since = now - timezone.timedelta(weeks=1)

    from .models import Tender, TenderSubscription, NotificationPreference

    # Published tenders in the timeframe (by publication_date)
    new_tenders = (
        Tender.objects.filter(
            status='published',
            publication_date__gte=since,
            publication_date__lte=now,
        )
        .select_related('category', 'subcategory', 'procurement_process')
        .order_by('-publication_date')
    )
    stats = {'sent_count': 0, 'skipped_no_pref': 0, 'skipped_no_tenders': 0, 'error_count': 0}

    # Users who want this frequency and have email on
    prefs = (
        NotificationPreference.objects.filter(
            notification_frequency=frequency,
            email_notifications=True,
        )
        .select_related('user')
    )
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@bidsconnect.co.tz')

    for pref in prefs:
        user = pref.user
        subscriptions = TenderSubscription.objects.filter(user=user, is_active=True)
        if not subscriptions.exists():
            stats['skipped_no_pref'] += 1
            continue

        # Collect all tenders that match any of the user's subscriptions
        seen_ids = set()
        user_tenders = []
        for sub in subscriptions:
            for t in get_tenders_for_subscription(sub, new_tenders):
                if t.id not in seen_ids:
                    seen_ids.add(t.id)
                    user_tenders.append(t)

        if not user_tenders:
            stats['skipped_no_tenders'] += 1
            continue

        # Build plain text and HTML
        date_range = f"{since.date()} to {now.date()}"
        lines = []
        for t in user_tenders:
            pub = t.publication_date.strftime('%Y-%m-%d') if t.publication_date else '—'
            deadline = t.submission_deadline.strftime('%Y-%m-%d %H:%M') if t.submission_deadline else '—'
            lines.append({
                'title': t.title,
                'reference_number': t.reference_number,
                'slug': getattr(t, 'slug', ''),
                'publication_date': pub,
                'submission_deadline': deadline,
                'category': t.category.name if t.category else '—',
            })
        site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
        plain_message = (
            f"Hello {user.get_full_name() or user.email},\n\n"
            f"Here is your {frequency} tender digest for {date_range}:\n\n"
            + "\n".join(
                f"- {t['title']} (Ref: {t['reference_number']}, Deadline: {t['submission_deadline']})"
                for t in lines
            )
            + "\n\nLog in to BidsConnect to view full details and submit a bid.\n\n— BidsConnect"
        )
        context = {
            'user': user,
            'frequency': frequency,
            'date_range': date_range,
            'tenders': lines,
            'site_url': site_url,
        }
        html_message = None
        try:
            html_message = render_to_string('emails/tender_digest.html', context)
        except Exception as e:
            logger.warning("Tender digest HTML template failed: %s", e)

        try:
            send_mail(
                subject=f"Your {frequency.capitalize()} Tender Digest — BidsConnect",
                message=plain_message,
                from_email=from_email,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            stats['sent_count'] += 1
            # Update last_notified
            pref.last_notified = now
            pref.save(update_fields=['last_notified'])
        except Exception as e:
            logger.exception("Failed to send tender digest to %s: %s", user.email, e)
            stats['error_count'] += 1

    return stats
