import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('bookings', '0005_booking_agreement_and_reviews'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='payment_status',
            field=models.CharField(
                choices=[
                    ('unpaid', 'Unpaid'),
                    ('pending', 'Payment pending'),
                    ('paid', 'Paid'),
                    ('refunding', 'Refund processing'),
                    ('failed', 'Payment failed'),
                    ('refunded', 'Refunded'),
                ],
                default='unpaid',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='booking',
            name='stripe_refund_id',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='booking',
            name='cancellation_reason',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='booking',
            name='cancelled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='cancelled_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cancelled_bookings', to=settings.AUTH_USER_MODEL),
        ),
    ]
