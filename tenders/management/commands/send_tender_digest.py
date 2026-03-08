from django.core.management.base import BaseCommand
from tenders.digest import build_and_send_tender_digests


class Command(BaseCommand):
    help = (
        "Send tender digest emails to users who subscribe to categories/subcategories/procurement "
        "and have notification_frequency set to daily or weekly. Run via cron: "
        "python manage.py send_tender_digest daily  # and/or send_tender_digest weekly"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'frequency',
            type=str,
            choices=['daily', 'weekly'],
            help='Digest frequency: daily or weekly',
        )

    def handle(self, *args, **options):
        frequency = options['frequency']
        self.stdout.write(f"Sending {frequency} tender digests...")
        stats = build_and_send_tender_digests(frequency)
        self.stdout.write(
            self.style.SUCCESS(
                f"Done: sent={stats['sent_count']}, skipped_no_tenders={stats['skipped_no_tenders']}, "
                f"skipped_no_pref={stats['skipped_no_pref']}, errors={stats['error_count']}"
            )
        )
