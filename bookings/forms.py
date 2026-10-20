from django import forms
from django.utils import timezone

from .availability import is_available
from .models import BlackoutDate, Booking

class BookingRequestForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ('start_date', 'end_date')
        widgets = {
            'start_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'end_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, item, **kwargs):
        super().__init__(*args, **kwargs)
        self.item = item

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        # If a date is missing or end < start, the field errors / model clean report it
        if not start or not end or end < start:
            return cleaned

        if start < timezone.localdate():
            raise forms.ValidationError("The start date can't be in the past.")
        if (end - start).days + 1 > Booking.MAX_DAYS:
            raise forms.ValidationError(
                f'Rentals are limited to {Booking.MAX_DAYS} days.'
            )
        if not is_available(self.item, start, end):
            raise forms.ValidationError(
                'Those dates are not available. Please pick different dates.'
            )
        return cleaned

class BlackoutDateForm(forms.ModelForm):
    class Meta:
        model = BlackoutDate
        fields = ('start_date', 'end_date', 'reason')
        widgets = {
            'start_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'end_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, item, **kwargs):
        super().__init__(*args, **kwargs)
        self.item = item

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        # Missing dates and end < start are reported elsewhere
        if not start or not end or end < start:
            return cleaned

        if start < timezone.localdate():
            raise forms.ValidationError("The start date can't be in the past.")
        if Booking.objects.filter(
            item=self.item,
            status=Booking.Status.APPROVED,
            start_date__lte=end,
            end_date__gte=start,
        ).exists():
            raise forms.ValidationError(
                'An approved booking already covers some of those dates. '
                'Cancel that booking first.'
            )
        return cleaned