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

    class PaymentStatus(models.TextChoices):
        UNPAID = 'unpaid', 'Unpaid'
        PENDING = 'pending', 'Payment pending'
        PAID = 'paid', 'Paid'
        REFUNDING = 'refunding', 'Refund processing'
        FAILED = 'failed', 'Payment failed'
        REFUNDED = 'refunded', 'Refunded'

    class RentalStatus(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not started'
        READY = 'ready', 'Ready for pickup'
        PICKED_UP = 'picked_up', 'Picked up'
        RETURNED = 'returned', 'Returned'
        COMPLETED = 'completed', 'Completed'
        DISPUTED = 'disputed', 'Disputed'

    class PayoutStatus(models.TextChoices):
        NOT_DUE = 'not_due', 'Not due'
        PROCESSING = 'processing', 'Processing'
        TRANSFERRED = 'transferred', 'Transferred to lender Stripe balance'
        FAILED = 'failed', 'Transfer failed'

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
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    rental_status = models.CharField(
        max_length=12, choices=RentalStatus.choices, default=RentalStatus.NOT_STARTED
    )
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    stripe_refund_id = models.CharField(max_length=255, blank=True)
    stripe_transfer_id = models.CharField(max_length=255, blank=True)
    payout_status = models.CharField(
        max_length=12, choices=PayoutStatus.choices, default=PayoutStatus.NOT_DUE
    )
    pickup_renter_confirmed_at = models.DateTimeField(null=True, blank=True)
    pickup_lender_confirmed_at = models.DateTimeField(null=True, blank=True)
    return_renter_confirmed_at = models.DateTimeField(null=True, blank=True)
    return_lender_confirmed_at = models.DateTimeField(null=True, blank=True)
    dispute_previous_status = models.CharField(
        max_length=12, choices=RentalStatus.choices, blank=True
    )
    dispute_reason = models.CharField(max_length=500, blank=True)
    dispute_reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='reported_booking_disputes', null=True, blank=True,
    )
    disputed_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=500, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='cancelled_bookings', null=True, blank=True,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    agreement_accepted_at = models.DateTimeField(null=True, blank=True)
    agreement_version = models.CharField(max_length=30, blank=True)
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


class ConditionPhoto(models.Model):
    class Stage(models.TextChoices):
        PICKUP = 'pickup', 'Pickup'
        RETURN = 'return', 'Return'

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name='condition_photos'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='booking_condition_photos',
    )
    stage = models.CharField(max_length=6, choices=Stage.choices)
    image = models.ImageField(upload_to='bookings/condition/%Y/%m/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f'{self.booking}: {self.get_stage_display()} photo by {self.uploaded_by}'


class BookingAlert(models.Model):
    class Kind(models.TextChoices):
        PICKUP_PHOTO = 'pickup_photo', 'Pickup photo added'
        RETURN_PHOTO = 'return_photo', 'Return photo added'
        DISPUTE = 'dispute', 'Booking dispute filed'
        CANCELLATION = 'cancellation', 'Booking cancelled'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='booking_alerts',
    )
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name='alerts'
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    message = models.CharField(max_length=320)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['read_at', '-created_at', '-id']

    def __str__(self):
        return f'{self.get_kind_display()} for {self.recipient}'


class BookingReview(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='written_reviews'
    )
    reviewee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_reviews'
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['booking', 'reviewer'], name='one_review_per_booking_reviewer'),
            models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name='review_rating_1_to_5'),
        ]

    def __str__(self):
        return f'{self.rating}/5 review for booking {self.booking_id}'
