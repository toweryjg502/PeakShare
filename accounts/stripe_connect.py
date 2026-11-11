import stripe
from django.conf import settings


def _configure():
    stripe.api_key = settings.STRIPE_SECRET_KEY


def create_express_account(user):
    """Create a Stripe Express account for a lender and return its ID."""
    _configure()
    account = stripe.Account.create(
        type='express',
        country='US',
        email=user.email,
        business_type='individual',
        capabilities={
            'card_payments': {'requested': True},
            'transfers': {'requested': True},
        },
        metadata={'peakshare_user_id': str(user.pk)},
    )
    return account.id


def create_onboarding_link(account_id, refresh_url, return_url):
    """Return a one-time Stripe-hosted onboarding URL for this account."""
    _configure()
    link = stripe.AccountLink.create(
        account=account_id,
        refresh_url=refresh_url,
        return_url=return_url,
        type='account_onboarding',
    )
    return link.url


def is_account_ready(account_id):
    """True when Stripe says this account can accept charges and receive payouts."""
    _configure()
    account = stripe.Account.retrieve(account_id)
    return bool(account.charges_enabled and account.payouts_enabled)