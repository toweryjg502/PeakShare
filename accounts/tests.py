from django.test import TestCase
from django.urls import reverse

from .forms import StudentRegistrationForm
from .models import CustomUser


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