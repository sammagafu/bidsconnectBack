"""
Tender digest task. Uses Celery if available; otherwise run via management command:
  python manage.py send_tender_digest daily
  python manage.py send_tender_digest weekly
"""
from tenders.digest import build_and_send_tender_digests

try:
    from celery import shared_task

    @shared_task
    def send_tender_digest(frequency):
        """
        Send a digest of new published tenders to users who subscribe to
        categories/subcategories/procurement and have notification_frequency = frequency.
        frequency: 'daily' or 'weekly'
        """
        if frequency not in ('daily', 'weekly'):
            return
        return build_and_send_tender_digests(frequency)
except ImportError:
    # Celery not installed; use management command for cron
    def send_tender_digest(frequency):
        if frequency not in ('daily', 'weekly'):
            return
        return build_and_send_tender_digests(frequency)
