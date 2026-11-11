from decimal import Decimal, ROUND_HALF_UP

import stripe
from django.conf import settings
from django.urls import reverse


def create_checkout_session(request, booking):
    """Create a card-only Checkout Session for a booking's rental price.

    The payment is collected on the platform. A separate Connect transfer can
    be created after the rental is completed, allowing payout to be delayed.
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY
    amount = int(
        (booking.total_price * Decimal('100')).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP
        )
    )
    booking_ref = f'booking_{booking.pk}'
    return stripe.checkout.Session.create(
        mode='payment',
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': f'{booking.item.title} rental',
                    'description': f'{booking.start_date} to {booking.end_date}',
                },
                'unit_amount': amount,
            },
            'quantity': 1,
        }],
        client_reference_id=str(booking.pk),
        metadata={'booking_id': str(booking.pk)},
        payment_intent_data={
            'transfer_group': booking_ref,
            'metadata': {'booking_id': str(booking.pk)},
        },
        success_url=request.build_absolute_uri(reverse('my_bookings')),
        cancel_url=request.build_absolute_uri(reverse('my_bookings')),
    )


def create_lender_transfer(booking):
    """Transfer the lender's 90% share after both sides confirm the return."""
    if not booking.stripe_payment_intent_id:
        raise ValueError('This booking has no successful Stripe payment.')
    if not booking.item.owner.stripe_account_id:
        raise ValueError('The lender has no connected Stripe account.')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    payment_intent = stripe.PaymentIntent.retrieve(booking.stripe_payment_intent_id)
    charge_id = payment_intent.latest_charge
    if hasattr(charge_id, 'id'):
        charge_id = charge_id.id
    if not charge_id:
        raise ValueError('Stripe has not made the paid charge available for transfer.')

    cents = int(
        (booking.total_price * Decimal('90')).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP
        )
    )
    transfer = stripe.Transfer.create(
        amount=cents,
        currency='usd',
        destination=booking.item.owner.stripe_account_id,
        source_transaction=charge_id,
        transfer_group=f'booking_{booking.pk}',
        metadata={'booking_id': str(booking.pk)},
        idempotency_key=f'peakshare_booking_{booking.pk}_lender_transfer',
    )
    return transfer
