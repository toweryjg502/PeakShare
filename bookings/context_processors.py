from .models import BookingAlert


def unread_booking_alert_count(request):
    if not request.user.is_authenticated:
        return {
            'unread_booking_alert_count': 0,
            'latest_booking_alert_id': 0,
        }
    alerts = BookingAlert.objects.filter(recipient=request.user)
    return {
        'unread_booking_alert_count': alerts.filter(read_at__isnull=True).count(),
        'latest_booking_alert_id': alerts.order_by('-id').values_list('id', flat=True).first() or 0,
    }
