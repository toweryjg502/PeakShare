from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import verified_required
from listings.models import Item

from .availability import is_available
from .forms import BlackoutDateForm, BookingRequestForm
from .models import BlackoutDate, Booking

@verified_required
def booking_request(request, item_pk):
    item = get_object_or_404(Item, pk=item_pk, is_active=True)
    if item.owner_id == request.user.pk:
        messages.error(request, "You can't book your own listing.")
        return redirect('item_detail', pk=item.pk)

    if request.method == 'POST':
        form = BookingRequestForm(request.POST, item=item)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.item = item
            booking.renter = request.user
            booking.total_price = item.daily_price * booking.days
            booking.save()
            messages.success(
                request, 'Request sent! The lender will approve or decline it.'
            )
            return redirect('my_bookings')
    else:
        form = BookingRequestForm(item=item)
    return render(request, 'bookings/booking_form.html', {
        'form': form,
        'item': item,
        'max_days': Booking.MAX_DAYS,
    })


@verified_required
def my_bookings(request):
    mine = Booking.objects.filter(renter=request.user).select_related('item')
    incoming = Booking.objects.filter(item__owner=request.user).select_related(
        'item', 'renter'
    )
    return render(request, 'bookings/my_bookings.html', {
        'my_requests': mine,
        'incoming': incoming,
    })


@verified_required
@require_POST
def booking_action(request, pk, action):
    if action not in ('approve', 'decline', 'cancel'):
        raise Http404
    booking = get_object_or_404(Booking.objects.select_related('item'), pk=pk)
    is_owner = booking.item.owner_id == request.user.pk
    is_renter = booking.renter_id == request.user.pk
    # Strangers get a 404, and only the lender can approve or decline
    if not (is_owner or is_renter):
        raise Http404
    if action in ('approve', 'decline') and not is_owner:
        raise Http404

    with transaction.atomic():
        # Lock the item so two approvals can't race (enforced on PostgreSQL)
        Item.objects.select_for_update().get(pk=booking.item_id)
        booking.refresh_from_db()

        if action == 'approve':
            if booking.status != Booking.Status.PENDING:
                messages.error(request, 'That request is no longer pending.')
            elif not is_available(booking.item, booking.start_date, booking.end_date,
                                  exclude=booking):
                messages.error(
                    request, 'Those dates are no longer available. Decline this request.'
                )
            else:
                booking.status = Booking.Status.APPROVED
                booking.save(update_fields=['status', 'updated_at'])
                messages.success(request, 'Request approved.')

        elif action == 'decline':
            if booking.status != Booking.Status.PENDING:
                messages.error(request, 'That request is no longer pending.')
            else:
                booking.status = Booking.Status.DECLINED
                booking.save(update_fields=['status', 'updated_at'])
                messages.success(request, 'Request declined.')

        else:  # cancel
            if booking.status not in (Booking.Status.PENDING, Booking.Status.APPROVED):
                messages.error(request, "That booking can't be cancelled.")
            else:
                booking.status = Booking.Status.CANCELLED
                booking.save(update_fields=['status', 'updated_at'])
                messages.success(request, 'Booking cancelled.')

    return redirect('my_bookings')

@verified_required
def blackout_manage(request, item_pk):
    # Filtering by owner means other users get a 404
    item = get_object_or_404(Item, pk=item_pk, owner=request.user)
    if request.method == 'POST':
        form = BlackoutDateForm(request.POST, item=item)
        if form.is_valid():
            blackout = form.save(commit=False)
            blackout.item = item
            blackout.save()
            messages.success(request, 'Dates blocked.')
            return redirect('blackout_manage', item_pk=item.pk)
    else:
        form = BlackoutDateForm(item=item)
    upcoming = item.blackout_dates.filter(end_date__gte=timezone.localdate())
    return render(request, 'bookings/blackout_manage.html', {
        'item': item,
        'form': form,
        'blackouts': upcoming,
    })


@verified_required
@require_POST
def blackout_delete(request, pk):
    blackout = get_object_or_404(
        BlackoutDate, pk=pk, item__owner=request.user
    )
    item_pk = blackout.item_id
    blackout.delete()
    messages.success(request, 'Dates are available again.')
    return redirect('blackout_manage', item_pk=item_pk)