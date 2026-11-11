from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    is_verified = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    # Stripe Connect (lender payouts)
    stripe_account_id = models.CharField(max_length=255, blank=True)
    stripe_payouts_ready = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.email})"