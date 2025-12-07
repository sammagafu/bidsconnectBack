# marketplace/models.py
from django.db import models
from accounts.models import Company, CustomUser as User
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
import uuid


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Industry Category"
        verbose_name_plural = "Industry Categories"
        ordering = ['name']
        indexes = [models.Index(fields=['slug']), models.Index(fields=['name'])]

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
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Industry Sub Category"
        verbose_name_plural = "Industry Sub Categories"
        unique_together = ('category', 'slug')
        ordering = ['name']
        indexes = [models.Index(fields=['slug', 'category']), models.Index(fields=['name'])]

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


class ProductService(models.Model):
    TYPE_CHOICES = [('Service', 'Service'), ('Product', 'Product')]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='products_services')
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products_services')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='products_services')
    type = models.CharField(choices=TYPE_CHOICES, max_length=10)
    featured_image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product/Service"
        verbose_name_plural = "Products/Services"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'category']),
            models.Index(fields=['type']),
            models.Index(fields=['subcategory']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()}) - {self.company.name}"

    def clean(self):
        if self.subcategory and self.subcategory.category != self.category:
            raise ValidationError("Subcategory must belong to the selected category")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    product_service = models.ForeignKey(ProductService, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
        ordering = ['-created_at']

    def __str__(self):
        return f"Image for {self.product_service.name}"


class PriceList(models.Model):
    product_service = models.ForeignKey(ProductService, on_delete=models.CASCADE, related_name='prices')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=50, blank=True)
    minimum_quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Price List"
        verbose_name_plural = "Price Lists"
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.product_service.name} - ${self.unit_price}"


class RFQ(models.Model):
    STATUS_CHOICES = (('OPEN', 'Open'), ('CLOSED', 'Closed'))
    title = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rfqs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Request for Quote"
        verbose_name_plural = "Requests for Quote"
        ordering = ['-created_at']
        indexes = [models.Index(fields=['buyer', 'status'])]

    def __str__(self):
        return f"RFQ {self.title} - {self.buyer.email}"


class RFQItem(models.Model):
    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit = models.CharField(max_length=50, blank=True)
    type = models.CharField(choices=ProductService.TYPE_CHOICES, max_length=10, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='rfq_items')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='rfq_items')
    image = models.ImageField(upload_to='rfq_items/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "RFQ Item"
        verbose_name_plural = "RFQ Items"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.name} × {self.quantity}"


class Quote(models.Model):
    STATUS_CHOICES = (('PENDING', 'Pending'), ('ACCEPTED', 'Accepted'), ('REJECTED', 'Rejected'))
    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name='quotes')
    seller = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='quotes')
    details = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Quote"
        verbose_name_plural = "Quotes"
        ordering = ['-created_at']
        indexes = [models.Index(fields=['rfq', 'status'])]

    def __str__(self):
        return f"Quote for RFQ {self.rfq.title} by {self.seller.name}"


class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='items')
    rfq_item = models.ForeignKey(RFQItem, on_delete=models.CASCADE, related_name='quote_items')
    proposed_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    details = models.TextField(blank=True)

    class Meta:
        unique_together = ['quote', 'rfq_item']
        verbose_name = "Quote Item"
        verbose_name_plural = "Quote Items"

    def __str__(self):
        return f"{self.proposed_price} for {self.rfq_item.name}"


class CompanyReview(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='company_reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['company', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating}★ by {self.user.email}"


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    related_quote = models.ForeignKey(Quote, on_delete=models.CASCADE, null=True, blank=True, related_name='messages')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender} → {self.receiver}"


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('QUOTE', 'Quote Update'), ('MESSAGE', 'New Message'),
        ('REVIEW', 'New Review'), ('RFQ', 'RFQ Update'), ('SYSTEM', 'System')
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    related_rfq = models.ForeignKey(RFQ, null=True, blank=True, on_delete=models.CASCADE, related_name='notifications')
    related_quote = models.ForeignKey(Quote, null=True, blank=True, on_delete=models.CASCADE, related_name='notifications')
    related_message = models.ForeignKey(Message, null=True, blank=True, on_delete=models.CASCADE, related_name='notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email}: {self.message[:50]}"