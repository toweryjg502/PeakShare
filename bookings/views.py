from django.contrib import messages
import logging
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import stripe
from django.conf import settings

from accounts.decorators import verified_required
from listings.models import Item

from .availability import is_available
from .forms import BlackoutDateForm, BookingRequestForm, ConditionPhotoForm, DisputeForm
from .models import BlackoutDate, Booking, BookingAlert, ConditionPhoto
from .stripe_payments import create_checkout_session, create_lender_transfer

logger = logging.getLogger(__name__)

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
    mine = Booking.objects.filter(renter=request.user).select_related(
        'item', 'item__owner'
    ).prefetch_related('condition_photos', 'condition_photos__uploaded_by')
    incoming = Booking.objects.filter(item__owner=request.user).select_related(
        'item', 'renter'
    ).prefetch_related('condition_photos', 'condition_photos__uploaded_by')
    def prepare_bookings(queryset):
        bookings = list(queryset)
        for booking in bookings:
            photos = list(booking.condition_photos.all())
            booking.pickup_photo = next(
                (photo for photo in photos if photo.stage == ConditionPhoto.Stage.PICKUP
                 and photo.uploaded_by_id == booking.renter_id), None
            )
            booking.return_photo = next(
                (photo for photo in photos if photo.stage == ConditionPhoto.Stage.RETURN
                 and photo.uploaded_by_id == booking.item.owner_id), None
            )
        return bookings

    return render(request, 'bookings/my_bookings.html', {
        'my_requests': prepare_bookings(mine.exclude(
            rental_status=Booking.RentalStatus.COMPLETED
        ).order_by('-start_date', '-id')),
        'past_requests': prepare_bookings(mine.filter(
            rental_status=Booking.RentalStatus.COMPLETED
        ).order_by('-updated_at', '-id')),
        'incoming': prepare_bookings(incoming.exclude(
            rental_status=Booking.RentalStatus.COMPLETED
        ).order_by('-start_date', '-id')),
        'past_incoming': prepare_bookings(incoming.filter(
            rental_status=Booking.RentalStatus.COMPLETED
        ).order_by('-updated_at', '-id')),
        'dispute_form': DisputeForm(),
    })


@verified_required
def booking_alert_list(request):
    alerts = BookingAlert.objects.filter(recipient=request.user).select_related(
        'booking', 'booking__item'
    ).order_by('-read_at__isnull', '-created_at', '-id')
    return render(request, 'bookings/alert_list.html', {'alerts': alerts})


@verified_required
def booking_alert_status(request):
    alerts = BookingAlert.objects.filter(recipient=request.user)
    latest = alerts.order_by('-id').values('id', 'message').first()
    return JsonResponse({
        'unread_count': alerts.filter(read_at__isnull=True).count(),
        'latest': latest,
    })


@verified_required
@require_POST
def booking_alert_open(request, alert_pk):
    alert = get_object_or_404(BookingAlert, pk=alert_pk, recipient=request.user)
    if alert.read_at is None:
        alert.read_at = timezone.now()
        alert.save(update_fields=['read_at'])
    return redirect(f"{reverse('my_bookings')}#booking-{alert.booking_id}")


def _booking_for_participant(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related('item', 'item__owner', 'renter'), pk=pk
    )
    if request.user.pk not in (booking.renter_id, booking.item.owner_id):
        raise Http404
    return booking


@verified_required
@require_POST
def booking_photo_upload(request, pk, stage):
    if stage not in (ConditionPhoto.Stage.PICKUP, ConditionPhoto.Stage.RETURN):
        raise Http404
    booking = _booking_for_participant(request, pk)
    required_status = (
        Booking.RentalStatus.READY if stage == ConditionPhoto.Stage.PICKUP
        else Booking.RentalStatus.PICKED_UP
    )
    if booking.rental_status != required_status:
        messages.error(request, 'Photos can only be added during the matching handoff stage.')
        return redirect('my_bookings')

    designated_uploader_id = (
        booking.renter_id if stage == ConditionPhoto.Stage.PICKUP
        else booking.item.owner_id
    )
    if request.user.pk != designated_uploader_id:
        messages.error(
            request,
            'The renter adds the pickup photo; the lender adds the return photo.',
        )
        return redirect('my_bookings')
    if ConditionPhoto.objects.filter(booking=booking, stage=stage).exists():
        messages.error(request, 'A photo has already been added for this handoff.')
        return redirect('my_bookings')

    form = ConditionPhotoForm(request.POST, request.FILES)
    if form.is_valid():
        photo = form.save(commit=False)
        photo.booking = booking
        photo.uploaded_by = request.user
        photo.stage = stage
        photo.save()
        recipient = (
            booking.item.owner if stage == ConditionPhoto.Stage.PICKUP
            else booking.renter
        )
        kind = (
            BookingAlert.Kind.PICKUP_PHOTO if stage == ConditionPhoto.Stage.PICKUP
            else BookingAlert.Kind.RETURN_PHOTO
        )
        uploader_name = request.user.get_full_name() or request.user.get_username()
        BookingAlert.objects.create(
            recipient=recipient,
            booking=booking,
            kind=kind,
            message=(
                f'{uploader_name} added the {stage} photo for {booking.item.title}. '
                f'Review it and confirm or flag an issue.'
            )[:320],
        )
        messages.success(request, f'{stage.title()} condition photo added.')
    else:
        messages.error(request, 'Choose a valid image file and try again.')
    return redirect('my_bookings')


def _complete_lender_transfer(booking_id, retry_processing=False):
    with transaction.atomic():
        booking = Booking.objects.select_for_update().select_related(
            'item', 'item__owner', 'renter'
        ).get(pk=booking_id)
        both_confirmed = (
            booking.return_renter_confirmed_at and booking.return_lender_confirmed_at
        )
        if booking.rental_status != Booking.RentalStatus.RETURNED or not both_confirmed:
            return False
        if booking.payout_status == Booking.PayoutStatus.TRANSFERRED:
            return True
        if (booking.payout_status == Booking.PayoutStatus.PROCESSING
                and not retry_processing):
            return False
        booking.payout_status = Booking.PayoutStatus.PROCESSING
        booking.save(update_fields=['payout_status', 'updated_at'])

    try:
        transfer = create_lender_transfer(booking)
    except (stripe.StripeError, ValueError):
        logger.exception('Lender transfer failed for booking %s', booking.pk)
        Booking.objects.filter(pk=booking.pk).update(
            payout_status=Booking.PayoutStatus.FAILED,
            updated_at=timezone.now(),
        )
        return False

    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(pk=booking.pk)
        booking.stripe_transfer_id = transfer.id
        booking.payout_status = Booking.PayoutStatus.TRANSFERRED
        booking.rental_status = Booking.RentalStatus.COMPLETED
        booking.save(update_fields=[
            'stripe_transfer_id', 'payout_status', 'rental_status', 'updated_at'
        ])
    return True


@verified_required
@require_POST
def booking_rental_action(request, pk, action):
    if action not in ('pickup', 'return', 'dispute', 'retry-payout'):
        raise Http404
    booking = _booking_for_participant(request, pk)
    is_lender = booking.item.owner_id == request.user.pk
    if action == 'retry-payout' and not is_lender:
        raise Http404

    dispute_form = DisputeForm(request.POST) if action == 'dispute' else None
    if dispute_form is not None and not dispute_form.is_valid():
        messages.error(request, 'Enter a short reason before flagging an issue.')
        return redirect('my_bookings')

    if action == 'retry-payout':
        if booking.rental_status != Booking.RentalStatus.RETURNED:
            messages.error(request, 'The item must be returned before a payout can be retried.')
        elif _complete_lender_transfer(booking.pk, retry_processing=True):
            messages.success(request, 'The lender transfer is complete.')
        else:
            messages.error(request, 'The transfer is still processing or failed again.')
        return redirect('my_bookings')

    should_release = False
    with transaction.atomic():
        booking = Booking.objects.select_for_update().select_related(
            'item', 'item__owner', 'renter'
        ).get(pk=booking.pk)
        is_lender = booking.item.owner_id == request.user.pk
        if action == 'dispute':
            if booking.rental_status in (
                Booking.RentalStatus.COMPLETED, Booking.RentalStatus.DISPUTED
            ) or booking.payout_status in (
                Booking.PayoutStatus.PROCESSING, Booking.PayoutStatus.TRANSFERRED
            ):
                messages.error(request, 'A dispute can no longer be opened for this booking.')
            else:
                booking.dispute_previous_status = booking.rental_status
                booking.rental_status = Booking.RentalStatus.DISPUTED
                booking.dispute_reason = dispute_form.cleaned_data['reason']
                booking.dispute_reported_by = request.user
                booking.disputed_at = timezone.now()
                booking.save(update_fields=[
                    'dispute_previous_status', 'rental_status', 'dispute_reason',
                    'dispute_reported_by', 'disputed_at', 'updated_at',
                ])
                other_party = booking.item.owner if request.user.pk == booking.renter_id else booking.renter
                reporter_name = request.user.get_full_name() or request.user.get_username()
                BookingAlert.objects.create(
                    recipient=other_party,
                    booking=booking,
                    kind=BookingAlert.Kind.DISPUTE,
                    message=(
                        f'{reporter_name} flagged an issue with {booking.item.title}. '
                        'The lender transfer is on hold.'
                    )[:320],
                )
                messages.success(request, 'Dispute flagged. The lender transfer is on hold.')
        else:
            stage_status, renter_field, lender_field, required_photo_stage = (
                (Booking.RentalStatus.READY, 'pickup_renter_confirmed_at',
                 'pickup_lender_confirmed_at', ConditionPhoto.Stage.PICKUP)
                if action == 'pickup' else
                (Booking.RentalStatus.PICKED_UP, 'return_renter_confirmed_at',
                 'return_lender_confirmed_at', ConditionPhoto.Stage.RETURN)
            )
            if booking.payment_status != Booking.PaymentStatus.PAID:
                messages.error(request, 'Payment must be confirmed before the handoff.')
            elif booking.rental_status != stage_status:
                messages.error(request, 'The booking is not at that handoff stage.')
            elif not ConditionPhoto.objects.filter(
                booking=booking,
                stage=required_photo_stage,
                uploaded_by=(booking.renter if action == 'pickup' else booking.item.owner),
            ).exists():
                messages.error(
                    request,
                    f'The {"renter" if action == "pickup" else "lender"} must add the '
                    f'{required_photo_stage} photo before either person can confirm.',
                )
            else:
                confirm_field = lender_field if is_lender else renter_field
                if getattr(booking, confirm_field):
                    messages.info(request, 'You already confirmed this step.')
                else:
                    setattr(booking, confirm_field, timezone.now())
                    update_fields = [confirm_field, 'updated_at']
                    if getattr(booking, lender_field if not is_lender else renter_field):
                        booking.rental_status = (
                            Booking.RentalStatus.PICKED_UP if action == 'pickup'
                            else Booking.RentalStatus.RETURNED
                        )
                        update_fields.append('rental_status')
                        should_release = action == 'return'
                    booking.save(update_fields=update_fields)
                    messages.success(
                        request,
                        'Pickup confirmed.' if action == 'pickup'
                        else 'Return confirmed.',
                    )

    if should_release:
        if _complete_lender_transfer(booking.pk):
            messages.success(
                request,
                'Return confirmed. 90% was transferred to the lender’s Stripe balance; '
                'PeakShare retains 10% before Stripe processing fees.'
            )
        else:
            messages.error(
                request,
                'Return is confirmed, but the lender transfer needs a retry. The booking is not completed yet.',
            )
    return redirect('my_bookings')


@verified_required
@require_POST
def booking_checkout(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related('item', 'item__owner'),
        pk=pk,
        renter=request.user,
    )
    if booking.status != Booking.Status.APPROVED:
        messages.error(request, 'Only approved bookings can be paid.')
        return redirect('my_bookings')
    if booking.payment_status == Booking.PaymentStatus.PAID:
        messages.info(request, 'This booking is already paid.')
        return redirect('my_bookings')
    if not booking.item.owner.stripe_account_id or not booking.item.owner.stripe_payouts_ready:
        messages.error(request, 'The lender must finish Stripe payout setup before you can pay.')
        return redirect('my_bookings')
    if not settings.STRIPE_SECRET_KEY:
        messages.error(request, 'Payments are not configured yet.')
        return redirect('my_bookings')

    try:
        with transaction.atomic():
            booking = Booking.objects.select_for_update().select_related(
                'item', 'item__owner'
            ).get(pk=booking.pk)
            if booking.status != Booking.Status.APPROVED:
                messages.error(request, 'This booking is no longer approved.')
                return redirect('my_bookings')

            stripe.api_key = settings.STRIPE_SECRET_KEY
            if booking.stripe_checkout_session_id:
                existing = stripe.checkout.Session.retrieve(
                    booking.stripe_checkout_session_id
                )
                if existing.status == 'open' and existing.url:
                    return redirect(existing.url)
                if existing.status == 'complete':
                    messages.info(request, 'Payment confirmation is still processing.')
                    return redirect('my_bookings')

            session = create_checkout_session(request, booking)
            booking.stripe_checkout_session_id = session.id
            booking.payment_status = Booking.PaymentStatus.PENDING
            booking.save(update_fields=[
                'stripe_checkout_session_id', 'payment_status', 'updated_at'
            ])
        return redirect(session.url)
    except stripe.StripeError:
        logger.exception('Could not create Checkout Session for booking %s', booking.pk)
        messages.error(request, 'We could not start checkout. Please try again.')
        return redirect('my_bookings')


@csrf_exempt
@require_POST
def stripe_webhook(request):
    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse('Webhook is not configured.', status=503)
    signature = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    try:
        event = stripe.Webhook.construct_event(
            request.body, signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponseBadRequest('Invalid webhook signature or payload.')

    event_type = event['type']
    if event_type not in {
        'checkout.session.completed',
        'checkout.session.async_payment_succeeded',
        'checkout.session.async_payment_failed',
        'checkout.session.expired',
    }:
        return HttpResponse(status=200)

    # StripeObject isn't a dict; convert its nested event data before using
    # dictionary helpers such as .get().
    session = event['data']['object'].to_dict()
    booking_id = (session.get('metadata') or {}).get('booking_id')
    if not booking_id:
        return HttpResponse(status=200)

    with transaction.atomic():
        try:
            booking = Booking.objects.select_for_update().get(pk=booking_id)
        except (Booking.DoesNotExist, ValueError, TypeError):
            return HttpResponse(status=200)
        # Ignore old/forged sessions after a newer checkout session was created.
        if booking.stripe_checkout_session_id != session.get('id'):
            return HttpResponse(status=200)

        payment_intent = session.get('payment_intent')
        if isinstance(payment_intent, dict):
            payment_intent = payment_intent.get('id')
        if payment_intent:
            booking.stripe_payment_intent_id = payment_intent

        if event_type in (
            'checkout.session.completed',
            'checkout.session.async_payment_succeeded',
        ) and session.get('payment_status') == 'paid':
            booking.payment_status = Booking.PaymentStatus.PAID
            if booking.status == Booking.Status.APPROVED:
                booking.rental_status = Booking.RentalStatus.READY
        elif event_type == 'checkout.session.async_payment_failed':
            booking.payment_status = Booking.PaymentStatus.FAILED
        elif event_type == 'checkout.session.expired' and booking.payment_status != Booking.PaymentStatus.PAID:
            booking.payment_status = Booking.PaymentStatus.UNPAID

        booking.save(update_fields=[
            'payment_status', 'rental_status', 'stripe_payment_intent_id', 'updated_at'
        ])
    return HttpResponse(status=200)


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
            elif booking.payment_status in (
                Booking.PaymentStatus.PENDING, Booking.PaymentStatus.PAID
            ):
                messages.error(
                    request,
                    'This booking has a payment in progress or completed. Contact support to cancel it.',
                )
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
