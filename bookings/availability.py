from .models import BlackoutDate, Booking
from django.utils import timezone

def is_available(item, start, end, exclude=None):
    """True if the item is free for every day from start to end (inclusive).

    Only approved bookings and blackout dates block. `exclude` lets a booking
    ignore itself when it is being approved.
    """
    booked = Booking.objects.filter(
        item=item,
        status=Booking.Status.APPROVED,
        start_date__lte=end,
        end_date__gte=start,
    )
    if exclude is not None:
        booked = booked.exclude(pk=exclude.pk)
    blacked_out = BlackoutDate.objects.filter(
        item=item, start_date__lte=end, end_date__gte=start
    )
    return not booked.exists() and not blacked_out.exists()

def unavailable_ranges(item):
    """Upcoming approved bookings and blackout dates, soonest first.

    Returns dicts with start, end, and kind ('booked' or 'blocked'). It never
    includes who booked or why a date is blocked.
    """
    today = timezone.localdate()
    ranges = [
        {'start': b.start_date, 'end': b.end_date, 'kind': 'booked'}
        for b in Booking.objects.filter(
            item=item, status=Booking.Status.APPROVED, end_date__gte=today
        )
    ]
    ranges += [
        {'start': b.start_date, 'end': b.end_date, 'kind': 'blocked'}
        for b in BlackoutDate.objects.filter(item=item, end_date__gte=today)
    ]
    return sorted(ranges, key=lambda r: (r['start'], r['end']))