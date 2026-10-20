from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Booking(models.Model):
    MAX_DAYS = 14

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        DECLINED = 'declined', 'Declined'
        CANCELLED = 'cancelled', 'Cancelled'

    item = models.ForeignKey(
        'listings.Item', on_delete=models.PROTECT, related_name='bookings'
    )
    renter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings'
    )
    start_date = models.DateField()
    end_date = models.DateField(help_text='Last day you will have the item (inclusive).')
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    total_price = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', '-id']

    def __str__(self):
        return f'{self.item.title}: {self.start_date} to {self.end_date} ({self.status})'

    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError('The end date cannot be before the start date.')


class BlackoutDate(models.Model):
    """A date range when the lender is not available."""

    item = models.ForeignKey(
        'listings.Item', on_delete=models.CASCADE, related_name='blackout_dates'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['start_date']

    def __str__(self):
        return f'{self.item.title}: unavailable {self.start_date} to {self.end_date}'

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError('The end date cannot be before the start date.')