from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect


def verified_required(view_func):
    """Only let logged-in, email-verified users through.

    - Anonymous users are sent to the login page (and returned here afterward).
    - Logged-in but unverified users are sent to their profile with a message.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_verified:
            messages.error(
                request,
                "Please verify your @appstate.edu email before doing that.",
            )
            return redirect('profile')
        return view_func(request, *args, **kwargs)
    return wrapper