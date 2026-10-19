from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.http import require_POST

from .forms import StudentRegistrationForm
from .tokens import email_verification_token


def send_verification_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    link = request.build_absolute_uri(reverse('verify_email', args=[uid, token]))
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