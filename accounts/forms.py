from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

ALLOWED_EMAIL_DOMAIN = '@appstate.edu'


class StudentRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        help_text="Must be your @appstate.edu email address."
    )
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        help_text="Optional contact number for gear handoffs."
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email.endswith(ALLOWED_EMAIL_DOMAIN):
            raise forms.ValidationError(
                "Registration is restricted to App State students and staff "
                "with an @appstate.edu email address."
            )
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email
