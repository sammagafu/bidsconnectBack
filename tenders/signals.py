# tenders/signals.py
# Tender notifications are sent from Tender.save() when status transitions to 'published'
# (see Tender.save() in models.py). No signal handlers here to avoid duplicate/broken logic.
