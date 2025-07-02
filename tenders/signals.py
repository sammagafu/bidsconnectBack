from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import Tender, TenderSubscription, TenderNotification, NotificationPreference

@receiver(post_save, sender=Tender)
def send_tender_notifications(sender, instance, created, **kwargs):
    """Send notifications to subscribed users when a new tender is created."""
    if created:
        # Find users subscribed to the tender's category
        subscriptions = TenderSubscription.objects.filter(category=instance.category)
        for subscription in subscriptions:
            user = subscription.user
            # Check notification preferences
            prefs = NotificationPreference.objects.filter(user=user).first()
            if prefs and prefs.notification_frequency:  # Simplified check
                message = f"A new tender '{instance.title}' has been published in {instance.category.name}."
                # Create notification record
                TenderNotification.objects.create(
                    user=user,
                    tender=instance,
                    message=message
                )
                # Send email notification
                send_mail(
                    subject=f"New Tender: {instance.title}",
                    message=message,
                    from_email='no-reply@tenderapp.com',
                    recipient_list=[user.email],
                    fail_silently=True
                )