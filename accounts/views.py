import stripe
import logging
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.http import require_POST

from . import stripe_connect
from .decorators import verified_required
from .forms import StudentRegistrationForm
from .tokens import email_verification_token

from django.conf import settings

logger = logging.getLogger(__name__)

def send_verification_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    link = request.build_absolute_uri(reverse('verify_email', args=[uid, token]))
    if settings.DEBUG:
        print(f"\nVERIFICATION LINK: {link}\n")
    send_mail(
        subject="Verify your PeakShare account",
        message=(
            f"Hi {user.first_name or user.username},\n\n"
            f"Confirm your App State email to activate your PeakShare account:\n\n"
            f"{link}\n\n"
            f"This link works once and expires in 3 days."
        ),
        from_email=None,  # uses DEFAULT_FROM_EMAIL
        recipient_list=[user.email],
    )


def register_view(request):
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()  # is_verified stays False
            send_verification_email(request, user)
            login(request, user)
            messages.info(request, "Account created! Check your @appstate.edu inbox for a verification link.")
            return redirect('profile')
    else:
        form = StudentRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


def verify_email_view(request, uidb64, token):
    User = get_user_model()
    try:
        user = User.objects.get(pk=urlsafe_base64_decode(uidb64).decode())
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None

    if user is not None and user.is_verified:
        messages.info(request, "This email is already verified.")
    elif user is not None and email_verification_token.check_token(user, token):
        user.is_verified = True
        user.save(update_fields=['is_verified'])
        messages.success(request, "Email verified. Welcome to PeakShare!")
    else:
        messages.error(request, "That verification link is invalid or has expired.")

    return redirect('profile' if request.user.is_authenticated else 'login')


@login_required
@require_POST
def resend_verification_view(request):
    if request.user.is_verified:
        messages.info(request, "Your email is already verified.")
    else:
        send_verification_email(request, request.user)
        messages.info(request, "Verification email sent. Check your inbox.")
    return redirect('profile')


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')


# ---------------------------------------------------------------------------
# Lender payout setup (Stripe Connect Express)
# ---------------------------------------------------------------------------

def _onboarding_redirect(request):
    """Send the lender to Stripe's hosted onboarding page."""
    user = request.user
    try:
        url = stripe_connect.create_onboarding_link(
            user.stripe_account_id,
            refresh_url=request.build_absolute_uri(reverse('payout_refresh')),
            return_url=request.build_absolute_uri(reverse('payout_return')),
        )
    except stripe.StripeError:
        logger.exception("Stripe Connect onboarding link creation failed")
        messages.error(request, "We couldn't reach Stripe. Please try again in a moment.")
        return redirect('profile')
    return redirect(url)


@verified_required
@require_POST
def payout_start_view(request):
    user = request.user
    if not user.stripe_account_id:
        try:
            user.stripe_account_id = stripe_connect.create_express_account(user)
        except stripe.StripeError:
            logger.exception("Stripe Connect Express account creation failed")
            user.stripe_account_id = ''
            messages.error(request, "We couldn't reach Stripe. Please try again in a moment.")
            return redirect('profile')
        user.save(update_fields=['stripe_account_id'])
    return _onboarding_redirect(request)


@verified_required
def payout_refresh_view(request):
    """Stripe sends people here when their onboarding link expired."""
    if not request.user.stripe_account_id:
        return redirect('profile')
    return _onboarding_redirect(request)


@verified_required
def payout_return_view(request):
    """Stripe sends people here when they leave onboarding (finished or not)."""
    user = request.user
    if not user.stripe_account_id:
        return redirect('profile')
    try:
        ready = stripe_connect.is_account_ready(user.stripe_account_id)
    except stripe.StripeError:
        messages.error(request, "We couldn't check your payout status. Please try again.")
        return redirect('profile')

    if ready != user.stripe_payouts_ready:
        user.stripe_payouts_ready = ready
        user.save(update_fields=['stripe_payouts_ready'])

    if ready:
        messages.success(request, "Payouts are set up. You can now receive payments for your listings.")
    else:
        messages.info(request, "Payout setup isn't finished yet. You can continue it from your profile.")
    return redirect('profile')
