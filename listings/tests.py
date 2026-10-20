from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser

from .models import Category, Item, ItemPhoto

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

        # ---------- Edit and hide listings ----------

def make_listing(owner, category, title='Ski set', **kwargs):
    return Item.objects.create(
        owner=owner,
        category=category,
        title=title,
        description='Good gear.',
        daily_price=Decimal('15.00'),
        condition=Item.Condition.GOOD,
        **kwargs,
    )


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ItemEditTests(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='lender', email='lender@appstate.edu',
            password='S3curePass!word42', is_verified=True,
        )
        self.other = CustomUser.objects.create_user(
            username='other', email='other@appstate.edu',
            password='S3curePass!word42', is_verified=True,
        )
        self.category = Category.objects.create(name='Skiing', slug='skiing')
        self.item = make_listing(self.owner, self.category)
        self.photo1 = ItemPhoto.objects.create(item=self.item, image=make_image('a.png'))
        self.photo2 = ItemPhoto.objects.create(item=self.item, image=make_image('b.png'))
        self.url = reverse('item_edit', args=[self.item.pk])

    def post_data(self, **overrides):
        data = {
            'category': self.category.pk,
            'title': 'Ski set',
            'description': 'Good gear.',
            'daily_price': '15.00',
            'condition': Item.Condition.GOOD,
            'pickup_instructions': '',
        }
        data.update(overrides)
        return data

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_unverified_owner_redirected_to_profile(self):
        self.owner.is_verified = False
        self.owner.save()
        self.client.force_login(self.owner)
        self.assertRedirects(self.client.get(self.url), reverse('profile'))

    def test_non_owner_gets_404_on_get(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_non_owner_cannot_change_listing(self):
        self.client.force_login(self.other)
        response = self.client.post(self.url, self.post_data(title='Hacked'))
        self.assertEqual(response.status_code, 404)
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, 'Ski set')

    def test_owner_sees_form(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_owner_can_update_details(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, self.post_data(title='Better skis'))
        self.assertRedirects(response, reverse('item_detail', args=[self.item.pk]))
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, 'Better skis')

    def test_owner_can_add_photo(self):
        self.client.force_login(self.owner)
        self.client.post(self.url, self.post_data(new_photos=[make_image('c.png')]))
        self.assertEqual(self.item.photos.count(), 3)

    def test_owner_can_remove_photo(self):
        self.client.force_login(self.owner)
        self.client.post(self.url, self.post_data(remove_photos=[self.photo1.pk]))
        self.assertEqual(self.item.photos.count(), 1)
        self.assertFalse(ItemPhoto.objects.filter(pk=self.photo1.pk).exists())

    def test_cannot_remove_every_photo(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            self.url, self.post_data(remove_photos=[self.photo1.pk, self.photo2.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.item.photos.count(), 2)

    def test_cannot_exceed_photo_limit(self):
        self.client.force_login(self.owner)
        extra = [make_image(f'x{i}.png') for i in range(Item.MAX_PHOTOS)]
        response = self.client.post(self.url, self.post_data(new_photos=extra))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.item.photos.count(), 2)

    def test_cannot_remove_another_listings_photo(self):
        other_item = make_listing(self.other, self.category, title='Tent')
        other_photo = ItemPhoto.objects.create(item=other_item, image=make_image('o.png'))
        self.client.force_login(self.owner)
        response = self.client.post(self.url, self.post_data(remove_photos=[other_photo.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ItemPhoto.objects.filter(pk=other_photo.pk).exists())


class ItemToggleTests(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='lender', email='lender@appstate.edu',
            password='S3curePass!word42', is_verified=True,
        )
        self.other = CustomUser.objects.create_user(
            username='other', email='other@appstate.edu',
            password='S3curePass!word42', is_verified=True,
        )
        category = Category.objects.create(name='Skiing', slug='skiing')
        self.item = make_listing(self.owner, category)
        self.url = reverse('item_toggle_active', args=[self.item.pk])

    def test_owner_can_hide_listing(self):
        self.client.force_login(self.owner)
        self.client.post(self.url)
        self.item.refresh_from_db()
        self.assertFalse(self.item.is_active)

    def test_owner_can_show_listing_again(self):
        self.item.is_active = False
        self.item.save()
        self.client.force_login(self.owner)
        self.client.post(self.url)
        self.item.refresh_from_db()
        self.assertTrue(self.item.is_active)

    def test_non_owner_gets_404_and_nothing_changes(self):
        self.client.force_login(self.other)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 404)
        self.item.refresh_from_db()
        self.assertTrue(self.item.is_active)

    def test_get_not_allowed(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_anonymous_redirected_to_login(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)