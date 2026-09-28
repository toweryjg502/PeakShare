from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class StudentRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True, 
        help_text="Must be a valid university email address (.edu)."
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
        email = self.cleaned_data.get('email', '').lower()
        if not email.endswith('.edu'):
            raise forms.ValidationError("Registration is restricted to verified campus students with a valid .edu email.")
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email