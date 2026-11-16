import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('bookings', '0004_booking_dispute_previous_status_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='agreement_accepted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='agreement_version',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.CreateModel(
            name='BookingReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField()),
                ('comment', models.CharField(blank=True, max_length=1000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='bookings.booking')),
                ('reviewee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_reviews', to=settings.AUTH_USER_MODEL)),
                ('reviewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='written_reviews', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AddConstraint(
            model_name='bookingreview',
            constraint=models.UniqueConstraint(fields=('booking', 'reviewer'), name='one_review_per_booking_reviewer'),
        ),
        migrations.AddConstraint(
            model_name='bookingreview',
            constraint=models.CheckConstraint(condition=models.Q(('rating__gte', 1), ('rating__lte', 5)), name='review_rating_1_to_5'),
        ),
    ]
