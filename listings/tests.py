from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser

from .models import Category, Item


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