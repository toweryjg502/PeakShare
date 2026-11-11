from unittest.mock import patch

import stripe
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


def make_user(username='lender', verified=True, **extra):
    return User.objects.create_user(
        username=username,
        email=f'{username}@appstate.edu',
        password='pass12345',
        is_verified=verified,
        **extra,
    )


@patch('accounts.stripe_connect.create_onboarding_link')
@patch('accounts.stripe_connect.create_express_account')
class PayoutStartTests(TestCase):
    def setUp(self):
        self.url = reverse('payout_start')

    def test_get_not_allowed(self, mock_create, mock_link):
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_anonymous_goes_to_login(self, mock_create, mock_link):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)
        mock_create.assert_not_called()

    def test_unverified_user_blocked(self, mock_create, mock_link):
        self.client.force_login(make_user(verified=False))
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('profile'), fetch_redirect_response=False)
        mock_create.assert_not_called()
        mock_link.assert_not_called()

    def test_creates_account_and_redirects_to_stripe(self, mock_create, mock_link):
        user = make_user()
        mock_create.return_value = 'acct_test123'
        mock_link.return_value = 'https://connect.stripe.com/setup/e/test'
        self.client.force_login(user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'https://connect.stripe.com/setup/e/test')
        user.refresh_from_db()
        self.assertEqual(user.stripe_account_id, 'acct_test123')
        self.assertFalse(user.stripe_payouts_ready)
        mock_link.assert_called_once()
        self.assertEqual(mock_link.call_args.args[0], 'acct_test123')

    def test_reuses_existing_account(self, mock_create, mock_link):
        user = make_user(stripe_account_id='acct_existing')
        mock_link.return_value = 'https://connect.stripe.com/setup/e/again'
        self.client.force_login(user)

        response = self.client.post(self.url)

        self.assertEqual(response.url, 'https://connect.stripe.com/setup/e/again')
        mock_create.assert_not_called()

    def test_stripe_error_shows_message(self, mock_create, mock_link):
        user = make_user()
        mock_create.side_effect = stripe.StripeError('boom')
        self.client.force_login(user)

        response = self.client.post(self.url)

        self.assertRedirects(response, reverse('profile'), fetch_redirect_response=False)
        self.assertEqual(len(list(get_messages(response.wsgi_request))), 1)
        user.refresh_from_db()
        self.assertEqual(user.stripe_account_id, '')


@patch('accounts.stripe_connect.is_account_ready')
class PayoutReturnTests(TestCase):
    def setUp(self):
        self.url = reverse('payout_return')

    def test_marks_user_ready(self, mock_ready):
        user = make_user(stripe_account_id='acct_1')
        mock_ready.return_value = True
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertRedirects(response, reverse('profile'), fetch_redirect_response=False)
        user.refresh_from_db()
        self.assertTrue(user.stripe_payouts_ready)

    def test_not_ready_stays_false(self, mock_ready):
        user = make_user(stripe_account_id='acct_1')
        mock_ready.return_value = False
        self.client.force_login(user)

        self.client.get(self.url)

        user.refresh_from_db()
        self.assertFalse(user.stripe_payouts_ready)

    def test_no_account_skips_stripe(self, mock_ready):
        self.client.force_login(make_user())

        response = self.client.get(self.url)

        self.assertRedirects(response, reverse('profile'), fetch_redirect_response=False)
        mock_ready.assert_not_called()


@patch('accounts.stripe_connect.create_onboarding_link')
class PayoutRefreshTests(TestCase):
    def setUp(self):
        self.url = reverse('payout_refresh')

    def test_sends_fresh_link(self, mock_link):
        user = make_user(stripe_account_id='acct_1')
        mock_link.return_value = 'https://connect.stripe.com/setup/e/fresh'
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.url, 'https://connect.stripe.com/setup/e/fresh')

    def test_no_account_goes_to_profile(self, mock_link):
        self.client.force_login(make_user())

        response = self.client.get(self.url)

        self.assertRedirects(response, reverse('profile'), fetch_redirect_response=False)
        mock_link.assert_not_called()