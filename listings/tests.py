from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser

from .models import Category, Item

import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

class ListingBrowseTests(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='lender', email='lender@appstate.edu', password='S3curePass!word42'
        )
        self.skiing = Category.objects.create(name='Skiing', slug='skiing')
        self.camping = Category.objects.create(name='Camping', slug='camping')
        self.ski = self.make_item('Ski set', self.skiing)
        self.tent = self.make_item('Tent', self.camping)

    def make_item(self, title, category, **kwargs):
        return Item.objects.create(
            owner=self.owner,
            category=category,
            title=title,
            description='Good gear.',
            daily_price=Decimal('15.00'),
            condition=Item.Condition.GOOD,
            **kwargs,
        )

    def test_list_shows_active_items(self):
        response = self.client.get(reverse('item_list'))
        self.assertContains(response, 'Ski set')
        self.assertContains(response, 'Tent')

    def test_list_hides_inactive_items(self):
        self.make_item('Hidden bike', self.skiing, is_active=False)
        response = self.client.get(reverse('item_list'))
        self.assertNotContains(response, 'Hidden bike')

    def test_category_filter(self):
        response = self.client.get(reverse('item_list'), {'category': 'skiing'})
        self.assertContains(response, 'Ski set')
        self.assertNotContains(response, 'Tent')

    def test_unknown_category_is_404(self):
        response = self.client.get(reverse('item_list'), {'category': 'nope'})
        self.assertEqual(response.status_code, 404)

    def test_detail_page_loads(self):
        response = self.client.get(reverse('item_detail', args=[self.ski.pk]))
        self.assertContains(response, 'Ski set')

    def test_inactive_detail_hidden_from_others(self):
        hidden = self.make_item('Hidden bike', self.skiing, is_active=False)
        response = self.client.get(reverse('item_detail', args=[hidden.pk]))
        self.assertEqual(response.status_code, 404)

    def test_inactive_detail_visible_to_owner(self):
        hidden = self.make_item('Hidden bike', self.skiing, is_active=False)
        self.client.force_login(self.owner)
        response = self.client.get(reverse('item_detail', args=[hidden.pk]))
        self.assertEqual(response.status_code, 200)

        # ---------- Create listing ----------

TEMP_MEDIA = tempfile.mkdtemp()


def tearDownModule():
    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)


def make_image(name='photo.png'):
    buf = BytesIO()
    Image.new('RGB', (10, 10), 'red').save(buf, 'PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ItemCreateTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='lender', email='lender@appstate.edu',
            password='S3curePass!word42', is_verified=True,
        )
        self.category = Category.objects.create(name='Skiing', slug='skiing')
        self.url = reverse('item_create')

    def post_data(self, photos, **overrides):
        data = {
            'category': self.category.pk,
            'title': 'Ski set',
            'description': 'Good skis and boots.',
            'daily_price': '15.00',
            'condition': Item.Condition.GOOD,
            'pickup_instructions': 'Dorm lobby.',
            'photos': photos,
        }
        data.update(overrides)
        return data

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_unverified_user_redirected_to_profile(self):
        self.user.is_verified = False
        self.user.save()
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('profile'))

    def test_verified_user_sees_form(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_create_item_with_photos(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.url, self.post_data([make_image('a.png'), make_image('b.png')])
        )
        item = Item.objects.get(title='Ski set')
        self.assertRedirects(response, reverse('item_detail', args=[item.pk]))
        self.assertEqual(item.owner, self.user)
        self.assertEqual(item.photos.count(), 2)

    def test_at_least_one_photo_required(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.post_data([]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Item.objects.count(), 0)

    def test_too_many_photos_rejected(self):
        self.client.force_login(self.user)
        photos = [make_image(f'p{i}.png') for i in range(Item.MAX_PHOTOS + 1)]
        response = self.client.post(self.url, self.post_data(photos))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Item.objects.count(), 0)

    def test_non_image_rejected(self):
        self.client.force_login(self.user)
        fake = SimpleUploadedFile('notes.txt', b'not an image', content_type='text/plain')
        response = self.client.post(self.url, self.post_data([fake]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Item.objects.count(), 0)