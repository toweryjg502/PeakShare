import re

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from django.http import HttpResponse
from django.test import override_settings
from django.urls import include, path

from .decorators import verified_required

from .forms import StudentRegistrationForm
from .models import CustomUser
from .tokens import email_verification_token


# ---------- Helpers ----------

def form_data(**overrides):
    data = {
        'username': 'testuser',
        'email': 'testuser@appstate.edu',
        'first_name': 'Test',
        'last_name': 'User',
        'phone_number': '',
        'password1': 'S3curePass!word42',
        'password2': 'S3curePass!word42',
    }
    data.update(overrides)
    return data


def make_user(**overrides):
    data = {
        'username': 'existing',
        'email': 'existing@appstate.edu',
        'password': 'S3curePass!word42',
    }
    data.update(overrides)
    return CustomUser.objects.create_user(**data)


def verification_path(user, token=None):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = token or email_verification_token.make_token(user)
    return reverse('verify_email', args=[uid, token])


def message_texts(response):
    return [str(m) for m in response.context['messages']]


# ---------- Your existing tests (unchanged) ----------

class RegistrationFormTests(TestCase):
    def test_accepts_appstate_email(self):
        form = StudentRegistrationForm(data=form_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_non_edu_email(self):
        form = StudentRegistrationForm(data=form_data(email='test@gmail.com'))
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_rejects_other_university_edu_email(self):
        form = StudentRegistrationForm(data=form_data(email='test@unc.edu'))
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_rejects_lookalike_domain(self):
        form = StudentRegistrationForm(data=form_data(email='test@notappstate.edu'))
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_email_is_lowercased(self):
        form = StudentRegistrationForm(data=form_data(email='TestUser@AppState.edu'))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['email'], 'testuser@appstate.edu')

    def test_rejects_duplicate_email_ignoring_case(self):
        CustomUser.objects.create_user(
            username='existing', email='taken@appstate.edu', password='S3curePass!word42'
        )
        form = StudentRegistrationForm(
            data=form_data(username='newuser', email='TAKEN@appstate.edu')
        )
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


class RegistrationViewTests(TestCase):
    def test_register_page_loads(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_valid_registration_creates_user_and_redirects_to_profile(self):
        response = self.client.post(reverse('register'), form_data())
        self.assertRedirects(response, reverse('profile'))
        self.assertTrue(CustomUser.objects.filter(email='testuser@appstate.edu').exists())

    def test_invalid_registration_creates_no_user(self):
        self.client.post(reverse('register'), form_data(email='test@gmail.com'))
        self.assertEqual(CustomUser.objects.count(), 0)

    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    # --- New: verification behavior at registration ---

    def test_new_user_starts_unverified(self):
        self.client.post(reverse('register'), form_data())
        user = CustomUser.objects.get(username='testuser')
        self.assertFalse(user.is_verified)

    def test_registration_sends_verification_email(self):
        self.client.post(reverse('register'), form_data())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['testuser@appstate.edu'])
        self.assertIn('/accounts/verify/', mail.outbox[0].body)

    def test_invalid_registration_sends_no_email(self):
        self.client.post(reverse('register'), form_data(email='test@gmail.com'))
        self.assertEqual(len(mail.outbox), 0)


# ---------- New tests ----------

class EmailVerificationTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_valid_link_verifies_user(self):
        response = self.client.get(verification_path(self.user), follow=True)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)
        self.assertIn('Email verified. Welcome to PeakShare!', message_texts(response))

    def test_link_from_real_email_works(self):
        """End to end: register, pull the link out of the email, click it."""
        self.client.post(reverse('register'), form_data())
        link = re.search(r'http://testserver(/accounts/verify/\S+)', mail.outbox[0].body)
        self.assertIsNotNone(link)
        self.client.get(link.group(1))
        self.assertTrue(CustomUser.objects.get(username='testuser').is_verified)

    def test_link_is_single_use(self):
        path = verification_path(self.user)
        self.client.get(path)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)

        # The token itself is now dead
        token = path.rstrip('/').split('/')[-1]
        self.assertFalse(email_verification_token.check_token(self.user, token))

        # Clicking again is harmless and says so
        response = self.client.get(path, follow=True)
        self.assertIn('This email is already verified.', message_texts(response))

    def test_bad_token_does_not_verify(self):
        response = self.client.get(
            verification_path(self.user, token='abc-notarealtoken'), follow=True
        )
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)
        self.assertIn('That verification link is invalid or has expired.', message_texts(response))

    def test_bad_user_id_does_not_verify(self):
        token = email_verification_token.make_token(self.user)
        response = self.client.get(
            reverse('verify_email', args=['!!!', token]), follow=True
        )
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)
        self.assertIn('That verification link is invalid or has expired.', message_texts(response))

    def test_token_for_one_user_does_not_verify_another(self):
        other = make_user(username='other', email='other@appstate.edu')
        token = email_verification_token.make_token(self.user)
        self.client.get(verification_path(other, token=token))
        other.refresh_from_db()
        self.assertFalse(other.is_verified)


class ResendVerificationTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_requires_login(self):
        response = self.client.post(reverse('resend_verification'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)
        self.assertEqual(len(mail.outbox), 0)

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('resend_verification'))
        self.assertEqual(response.status_code, 405)

    def test_unverified_user_gets_email(self):
        self.client.force_login(self.user)
        self.client.post(reverse('resend_verification'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_verified_user_gets_no_email(self):
        self.user.is_verified = True
        self.user.save()
        self.client.force_login(self.user)
        self.client.post(reverse('resend_verification'))
        self.assertEqual(len(mail.outbox), 0)

        # ---------- verified_required decorator ----------

@verified_required
def _protected_view(request):
    return HttpResponse('secret')


urlpatterns = [
    path('accounts/', include('accounts.urls')),
    path('listings/', include('listings.urls')),
    path('bookings/', include('bookings.urls')),
    path('verified-only/', _protected_view),
]


@override_settings(ROOT_URLCONF=__name__)
class VerifiedRequiredTests(TestCase):
    def test_anonymous_redirected_to_login(self):
        response = self.client.get('/verified-only/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_unverified_user_redirected_to_profile_with_message(self):
        user = make_user()
        self.client.force_login(user)
        response = self.client.get('/verified-only/', follow=True)
        self.assertRedirects(response, reverse('profile'))
        self.assertIn(
            'Please verify your @appstate.edu email before doing that.',
            message_texts(response),
        )

    def test_verified_user_gets_through(self):
        user = make_user(is_verified=True)
        self.client.force_login(user)
        response = self.client.get('/verified-only/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'secret')

    def test_verifying_unlocks_access(self):
        user = make_user()
        self.client.force_login(user)
        self.assertEqual(self.client.get('/verified-only/').status_code, 302)
        self.client.get(verification_path(user))
        self.assertEqual(self.client.get('/verified-only/').status_code, 200)