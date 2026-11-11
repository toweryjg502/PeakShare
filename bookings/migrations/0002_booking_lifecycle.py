from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='payment_status',
            field=models.CharField(
                choices=[
                    ('unpaid', 'Unpaid'),
                    ('pending', 'Payment pending'),
                    ('paid', 'Paid'),
                    ('failed', 'Payment failed'),
                    ('refunded', 'Refunded'),
                ],
                default='unpaid',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='booking',
            name='rental_status',
            field=models.CharField(
                choices=[
                    ('not_started', 'Not started'),
                    ('ready', 'Ready for pickup'),
                    ('picked_up', 'Picked up'),
                    ('returned', 'Returned'),
                    ('completed', 'Completed'),
                    ('disputed', 'Disputed'),
                ],
                default='not_started',
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name='booking',
            name='stripe_checkout_session_id',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='booking',
            name='stripe_payment_intent_id',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
