from django.db import models
from accounts.models import Company, CustomUser as User
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Industry Category"
        verbose_name_plural = "Industry Categories"
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['name']),
        ]

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
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE,
        related_name='subcategories'
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Industry Sub Category"
        verbose_name_plural = "Industry Sub Categories"
        unique_together = ('category', 'slug')
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug', 'category']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            counter = 1
            while SubCategory.objects.filter(
                category=self.category, 
                slug=self.slug
            ).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

class ProductService(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ('Service', 'Service'),
        ('Product', 'Product'),
    ]

    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='products'
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE,
        related_name='products'
    )
    subcategory = models.ForeignKey(
        SubCategory, 
        on_delete=models.CASCADE,
        related_name='products'
    )
    type = models.CharField(
        choices=DOCUMENT_TYPE_CHOICES, 
        max_length=10
    )
    featured_image = models.ImageField(
        upload_to='products/', 
        blank=True, 
        null=True
    )
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
        # Validate that subcategory belongs to the selected category
        if self.subcategory and self.subcategory.category != self.category:
            raise ValidationError(
                "Subcategory must belong to the selected category"
            )
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class ProductImage(models.Model):
    product_service = models.ForeignKey(
        ProductService, 
        on_delete=models.CASCADE, 
        related_name='images'
    )
    image = models.ImageField(upload_to='product_images/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product_service']),
        ]

    def __str__(self):
        return f"Image for {self.product_service.name}"

class PriceList(models.Model):
    product_service = models.ForeignKey(
        ProductService, 
        on_delete=models.CASCADE, 
        related_name='prices'
    )
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    unit = models.CharField(max_length=50, blank=True)
    minimum_quantity = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Price List"
        verbose_name_plural = "Price Lists"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['product_service', 'is_active']),
        ]

    def __str__(self):
        return f"{self.product_service.name} - ${self.unit_price}"

class QuoteRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    )
    
    customer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='quote_requests'
    )
    product_service = models.ForeignKey(
        ProductService, 
        on_delete=models.CASCADE,
        related_name='quote_requests'
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)]
    )
    additional_details = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='PENDING'
    )
    total_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Quote Request"
        verbose_name_plural = "Quote Requests"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['product_service', 'status']),
        ]

    def __str__(self):
        return f"Quote for {self.product_service.name} - {self.customer.email}"

class CompanyReview(models.Model):
    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='reviews'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Company Review"
        verbose_name_plural = "Company Reviews"
        unique_together = ['company', 'user']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'is_approved']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.rating} stars for {self.company.name} by {self.user.email}"

class Message(models.Model):
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='received_messages'
    )
    content = models.TextField()
    parent = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.CASCADE,
        related_name='replies'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender', 'receiver', 'is_read']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Message from {self.sender.email} to {self.receiver.email}"

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('QUOTE', 'Quote Update'),
        ('MESSAGE', 'New Message'),
        ('REVIEW', 'New Review'),
        ('SYSTEM', 'System Notification'),
    )

    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    message = models.TextField()
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES
    )
    related_quote = models.ForeignKey(
        QuoteRequest, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='notifications'
    )
    related_message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type']),
        ]

    def __str__(self):
        return f"Notification for {self.user.email}: {self.message}"