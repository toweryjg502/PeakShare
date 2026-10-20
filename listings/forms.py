from django import forms

from .models import Item

MAX_PHOTO_MB = 5


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """An image field that accepts several files and returns a list."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            if not data:
                # Nothing uploaded: let the normal "required" check fire
                return single_clean(None, initial)
            return [single_clean(d, initial) for d in data]
        return [single_clean(data, initial)]

class ItemForm(forms.ModelForm):
    photos = MultipleImageField(
        help_text=f'Upload 1 to {Item.MAX_PHOTOS} photos (hold Ctrl or Cmd to select several). '
                  f'The first one is the cover image.',
    )

    class Meta:
        model = Item
        fields = (
            'category', 'title', 'description', 'daily_price',
            'condition', 'pickup_instructions',
        )

    def clean_photos(self):
        photos = self.cleaned_data['photos']
        if len(photos) > Item.MAX_PHOTOS:
            raise forms.ValidationError(
                f'You can upload at most {Item.MAX_PHOTOS} photos.'
            )
        for photo in photos:
            if photo.size > MAX_PHOTO_MB * 1024 * 1024:
                raise forms.ValidationError(
                    f'Each photo must be under {MAX_PHOTO_MB} MB.'
                )
        return photos