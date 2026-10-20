from .models import BlackoutDate, Booking


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