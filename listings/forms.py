from django import forms
from django.utils.html import format_html

from .models import Item, ItemPhoto

MAX_PHOTO_MB = 5


def validate_photo_sizes(photos):
    for photo in photos:
        if photo.size > MAX_PHOTO_MB * 1024 * 1024:
            raise forms.ValidationError(
                f'Each photo must be under {MAX_PHOTO_MB} MB.'
            )


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
        validate_photo_sizes(photos)
        return photos


class PhotoChoiceField(forms.ModelMultipleChoiceField):
    """Shows each existing photo as a thumbnail next to its checkbox."""

    def label_from_instance(self, photo):
        return format_html('<img src="{}" alt="" width="100">', photo.image.url)


class ItemEditForm(forms.ModelForm):
    new_photos = MultipleImageField(
        required=False,
        label='Add photos',
        help_text=f'A listing can have {Item.MAX_PHOTOS} photos in total.',
    )
    remove_photos = PhotoChoiceField(
        queryset=ItemPhoto.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Remove photos',
    )

    class Meta(ItemForm.Meta):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only this listing's own photos can be removed
        self.fields['remove_photos'].queryset = self.instance.photos.all()

    def clean_new_photos(self):
        photos = self.cleaned_data.get('new_photos') or []
        validate_photo_sizes(photos)
        return photos

    def clean(self):
        cleaned = super().clean()
        if 'new_photos' in cleaned and 'remove_photos' in cleaned:
            remaining = (
                self.instance.photos.count()
                - len(cleaned['remove_photos'])
                + len(cleaned['new_photos'])
            )
            if remaining < 1:
                raise forms.ValidationError('A listing needs at least one photo.')
            if remaining > Item.MAX_PHOTOS:
                raise forms.ValidationError(
                    f'A listing can have at most {Item.MAX_PHOTOS} photos. '
                    f'Remove some or upload fewer.'
                )
        return cleaned