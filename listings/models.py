from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Item(models.Model):
    MAX_PHOTOS = 5

    class Condition(models.TextChoices):
        LIKE_NEW = 'like_new', 'Like new'
        GOOD = 'good', 'Good'
        FAIR = 'fair', 'Fair'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='items'
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='items'
    )
    title = models.CharField(max_length=100)
    description = models.TextField()
    daily_price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1.00'))],
    )
    condition = models.CharField(max_length=10, choices=Condition.choices)
    pickup_instructions = models.TextField(
        blank=True,
        help_text='Where and when the renter can pick up and drop off.',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} (${self.daily_price}/day)'


class ItemPhoto(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='items/%Y/%m/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f'Photo for {self.item.title}'