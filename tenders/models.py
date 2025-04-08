# tenders/models.py
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser
from django.utils.text import slugify
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    
    class Meta:
        verbose_name = "Industry Category"
        verbose_name_plural = "Industry Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            counter = 1
            while Category.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

class SubCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Industry Sub Category"
        verbose_name_plural = "Industry Sub Categories"
        unique_together = ('category', 'slug')
        ordering = ['name']

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            counter = 1
            while SubCategory.objects.filter(category=self.category, slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

class ProcurementProcess(models.Model):
    PROCESS_TYPES = (
        ('open', 'Open Tendering'),
        ('selective', 'Selective Tendering'),
        ('limited', 'Limited Tendering'),
        ('direct', 'Direct Procurement'),
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    type = models.CharField(max_length=20, choices=PROCESS_TYPES)
    description = models.TextField()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            counter = 1
            while ProcurementProcess.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

class Tender(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("pending", "Pending Approval"),
        ("published", "Published"),
        ("evaluation", "Under Evaluation"),
        ("awarded", "Awarded"),
        ("closed", "Closed"),
        ("canceled", "Canceled"),
    )

    TenderTypeCountry = (
        ('National', 'National Tendering'),
        ('International', 'International Tendering'),
    )
    TenderTypeSector = (
        ('Private Company', 'Private Company Tendering'),
        ('Public Sector', 'Public Sector Tendering'),
        ('Non-Governmental Organization', 'Non-Governmental Organization Tendering'),  
        ('Government Agency', 'Government Agency Tendering'),

    )
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    reference_number = models.CharField(max_length=50, unique=True)
    tender_type_country = models.CharField(max_length=30, choices=TenderTypeCountry,default='National')
    tender_type_sector = models.CharField(max_length=30, choices=TenderTypeSector,default='Private Company')
    tenderdescription = models.TextField(default="tender description to be updated")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True)
    procurement_process = models.ForeignKey(ProcurementProcess, on_delete=models.SET_NULL, null=True)

    publication_date = models.DateTimeField(default=timezone.now)
    submission_deadline = models.DateTimeField()
    clarification_deadline = models.DateTimeField()
    evaluation_start_date = models.DateTimeField(null=True, blank=True)
    evaluation_end_date = models.DateTimeField(null=True, blank=True)
    
    estimated_budget = models.DecimalField(max_digits=16, decimal_places=2)
    currency = models.CharField(max_length=3, default='TSH')
    bid_bond_percentage = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    address = models.TextField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_tenders')
    evaluation_committee = models.ManyToManyField(CustomUser, related_name='evaluation_tenders', blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    last_status_change = models.DateTimeField(auto_now=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        indexes = [
            models.Index(fields=['-publication_date']),
            models.Index(fields=['status']),
            models.Index(fields=['slug']),
        ]
        ordering = ['-publication_date']

    def __str__(self):
        return f"{self.reference_number} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while Tender.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

class TenderDocument(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='tender_documents/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for {self.tender.title}"

class TenderSubscription(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='tender_subscriptions'
    )
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Subscribe to all tenders in this category"
    )
    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Subscribe to all tenders in this subcategory"
    )
    procurement_process = models.ForeignKey(
        ProcurementProcess,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Subscribe to all tenders with this procurement process"
    )
    keywords = models.TextField(
        blank=True,
        help_text="Comma-separated keywords to match in tender title and description"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [
            ('user', 'category', 'subcategory', 'procurement_process')
        ]
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['category']),
            models.Index(fields=['subcategory']),
            models.Index(fields=['procurement_process']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        criteria = []
        if self.category:
            criteria.append(f"Category: {self.category.name}")
        if self.subcategory:
            criteria.append(f"Subcategory: {self.subcategory.name}")
        if self.procurement_process:
            criteria.append(f"Process: {self.procurement_process.name}")
        if self.keywords:
            criteria.append(f"Keywords: {self.keywords}")
        return f"{self.user.username}'s subscription - {' | '.join(criteria)}"

    def save(self, *args, **kwargs):
        if not self.slug:
            criteria_str = "-".join(filter(None, [
                self.category.name if self.category else "",
                self.subcategory.name if self.subcategory else "",
                self.procurement_process.name if self.procurement_process else "",
                self.keywords.replace(',', '-').replace(' ', '') if self.keywords else ""
            ]))
            base_slug = slugify(f"{self.user.username}-{criteria_str}")[:190]
            self.slug = base_slug
            counter = 1
            while TenderSubscription.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"[:200]
                counter += 1
        super().save(*args, **kwargs)

class NotificationPreference(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notification_preference'
    )
    email_notifications = models.BooleanField(
        default=True,
        help_text="Receive email notifications for new matching tenders"
    )
    notification_frequency = models.CharField(
        max_length=20,
        choices=(
            ('immediate', 'Immediate'),
            ('daily', 'Daily Digest'),
            ('weekly', 'Weekly Digest'),
        ),
        default='immediate'
    )
    last_notified = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s notification preferences"

class TenderNotification(models.Model):
    subscription = models.ForeignKey(
        TenderSubscription,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    tender = models.ForeignKey(
        Tender,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    is_sent = models.BooleanField(default=False)
    delivery_status = models.CharField(
        max_length=50,
        blank=True,
        help_text="Email delivery status"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('subscription', 'tender')
        indexes = [
            models.Index(fields=['is_sent']),
            models.Index(fields=['sent_at']),
        ]

    def __str__(self):
        return f"Notification for {self.tender.title} to {self.subscription.user.username}"

class TenderStatusHistory(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20, choices=Tender.STATUS_CHOICES)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.tender.title} - {self.status} at {self.changed_at}"

# Signal handlers for automatic notification creation and sending
@receiver(post_save, sender=Tender)
def create_tender_notifications(sender, instance, created, **kwargs):
    if instance.status == 'published':
        subscriptions = TenderSubscription.objects.filter(is_active=True)

        if instance.category:
            subscriptions = subscriptions.filter(
                models.Q(category=instance.category) |
                models.Q(category__isnull=True)
            )

        if instance.subcategory:
            subscriptions = subscriptions.filter(
                models.Q(subcategory=instance.subcategory) |
                models.Q(subcategory__isnull=True)
            )

        if instance.procurement_process:
            subscriptions = subscriptions.filter(
                models.Q(procurement_process=instance.procurement_process) |
                models.Q(procurement_process__isnull=True)
            )

        for subscription in subscriptions:
            if subscription.keywords:
                keywords = [k.strip().lower() for k in subscription.keywords.split(',')]
                content = f"{instance.title} {instance.description}".lower()
                if not any(keyword in content for keyword in keywords):
                    continue

            try:
                preference = subscription.user.notification_preference
                if not preference.email_notifications:
                    continue
            except NotificationPreference.DoesNotExist:
                continue

            TenderNotification.objects.get_or_create(
                subscription=subscription,
                tender=instance,
                defaults={'is_sent': False}
            )

@receiver(post_save, sender=TenderNotification)
def send_tender_notification(sender, instance, created, **kwargs):
    if not instance.is_sent:
        user = instance.subscription.user
        preference = user.notification_preference

        if preference.notification_frequency == 'immediate':
            send_notification_email(instance)

def send_notification_email(notification):
    try:
        tender = notification.tender
        user = notification.subscription.user
        
        subject = f"New Tender Alert: {tender.title}"
        context = {
            'user': user,
            'tender': tender,
            'site_name': getattr(settings, 'SITE_NAME', 'Tender Portal'),
        }
        
        html_message = render_to_string('emails/new_tender_notification.html', context)
        plain_message = render_to_string('emails/new_tender_notification.txt', context)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        notification.is_sent = True
        notification.sent_at = timezone.now()
        notification.delivery_status = 'sent'
        notification.save()

    except Exception as e:
        notification.delivery_status = f'error: {str(e)}'
        notification.save()