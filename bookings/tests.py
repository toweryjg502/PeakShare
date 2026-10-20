from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser
from listings.models import Category, Item

from .availability import is_available
from .models import BlackoutDate, Booking

BASE = timezone.localdate() + timedelta(days=10)


def d(n):
    """A date n days after BASE (always in the future)."""
    return BASE + timedelta(days=n)


def make_user(username, verified=True):
    return CustomUser.objects.create_user(
        username=username, email=f'{username}@appstate.edu',
        password='S3curePass!word42', is_verified=verified,
    )


def make_item(owner, title='Ski set', **kwargs):
    category, _ = Category.objects.get_or_create(slug='skiing', defaults={'name': 'Skiing'})
    return Item.objects.create(
        owner=owner, category=category, title=title, description='Good gear.',
        daily_price=Decimal('15.00'), condition=Item.Condition.GOOD, **kwargs,
    )


def make_booking(item, renter, start, end, status=Booking.Status.APPROVED):
    days = (end - start).days + 1
    return Booking.objects.create(
        item=item, renter=renter, start_date=start, end_date=end,
        status=status, total_price=item.daily_price * days,
    )


class AvailabilityTests(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.renter = make_user('renter')
        self.item = make_item(self.owner)
        make_booking(self.item, self.renter, d(0), d(2))

    def test_exact_same_dates_conflict(self):
        self.assertFalse(is_available(self.item, d(0), d(2)))

    def test_overlap_on_last_day_conflicts(self):
        self.assertFalse(is_available(self.item, d(2), d(4)))

    def test_overlap_on_first_day_conflicts(self):
        self.assertFalse(is_available(self.item, d(-2), d(0)))

    def test_enclosing_range_conflicts(self):
        self.assertFalse(is_available(self.item, d(-1), d(5)))

    def test_day_after_is_free(self):
        self.assertTrue(is_available(self.item, d(3), d(5)))

    def test_day_before_is_free(self):
        self.assertTrue(is_available(self.item, d(-3), d(-1)))

    def test_pending_does_not_block(self):
        item = make_item(self.owner, title='Tent')
        make_booking(item, self.renter, d(0), d(2), Booking.Status.PENDING)
        self.assertTrue(is_available(item, d(0), d(2)))

    def test_declined_and_cancelled_do_not_block(self):
        for i, status in enumerate((Booking.Status.DECLINED, Booking.Status.CANCELLED)):
            item = make_item(self.owner, title=f'Gear {i}')
            make_booking(item, self.renter, d(0), d(2), status)
            self.assertTrue(is_available(item, d(0), d(2)))

    def test_blackout_blocks(self):
        item = make_item(self.owner, title='Tent')
        BlackoutDate.objects.create(item=item, start_date=d(10), end_date=d(12))
        self.assertFalse(is_available(item, d(11), d(11)))
        self.assertTrue(is_available(item, d(13), d(14)))

    def test_exclude_ignores_own_booking(self):
        booking = Booking.objects.get(item=self.item)
        self.assertTrue(is_available(self.item, d(0), d(2), exclude=booking))

    def test_other_items_unaffected(self):
        other = make_item(self.owner, title='Tent')
        self.assertTrue(is_available(other, d(0), d(2)))


class BookingRequestTests(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.renter = make_user('renter')
        self.item = make_item(self.owner)
        self.url = reverse('booking_request', args=[self.item.pk])

    def post(self, start, end):
        return self.client.post(
            self.url, {'start_date': start.isoformat(), 'end_date': end.isoformat()}
        )

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_unverified_user_redirected_to_profile(self):
        self.renter.is_verified = False
        self.renter.save()
        self.client.force_login(self.renter)
        self.assertRedirects(self.client.get(self.url), reverse('profile'))

    def test_owner_cannot_book_own_item(self):
        self.client.force_login(self.owner)
        response = self.post(d(0), d(2))
        self.assertRedirects(response, reverse('item_detail', args=[self.item.pk]))
        self.assertEqual(Booking.objects.count(), 0)

    def test_inactive_item_is_404(self):
        self.item.is_active = False
        self.item.save()
        self.client.force_login(self.renter)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_renter_sees_form(self):
        self.client.force_login(self.renter)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_creates_pending_booking_with_total_price(self):
        self.client.force_login(self.renter)
        response = self.post(d(0), d(2))
        self.assertRedirects(response, reverse('my_bookings'))
        booking = Booking.objects.get()
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual(booking.renter, self.renter)
        self.assertEqual(booking.item, self.item)
        self.assertEqual(booking.total_price, Decimal('45.00'))  # 3 days x $15

    def test_rejects_start_in_the_past(self):
        self.client.force_login(self.renter)
        today = timezone.localdate()
        response = self.post(today - timedelta(days=1), today)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Booking.objects.count(), 0)

    def test_rejects_end_before_start(self):
        self.client.force_login(self.renter)
        response = self.post(d(5), d(2))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Booking.objects.count(), 0)

    def test_rejects_too_long(self):
        self.client.force_login(self.renter)
        response = self.post(d(0), d(Booking.MAX_DAYS))  # MAX_DAYS + 1 days
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Booking.objects.count(), 0)

    def test_rejects_dates_overlapping_approved_booking(self):
        other = make_user('other')
        make_booking(self.item, other, d(1), d(3))
        self.client.force_login(self.renter)
        response = self.post(d(3), d(5))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Booking.objects.count(), 1)

    def test_rejects_blackout_dates(self):
        BlackoutDate.objects.create(item=self.item, start_date=d(1), end_date=d(3))
        self.client.force_login(self.renter)
        response = self.post(d(0), d(1))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Booking.objects.count(), 0)


class BookingActionTests(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.renter = make_user('renter')
        self.stranger = make_user('stranger')
        self.item = make_item(self.owner)
        self.booking = make_booking(
            self.item, self.renter, d(0), d(2), Booking.Status.PENDING
        )

    def url(self, action):
        return reverse('booking_action', args=[self.booking.pk, action])

    def status(self):
        self.booking.refresh_from_db()
        return self.booking.status

    def test_owner_approves(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url('approve'))
        self.assertRedirects(response, reverse('my_bookings'))
        self.assertEqual(self.status(), Booking.Status.APPROVED)

    def test_approve_fails_if_dates_now_taken(self):
        make_booking(self.item, self.stranger, d(1), d(3))  # approved, overlaps
        self.client.force_login(self.owner)
        self.client.post(self.url('approve'))
        self.assertEqual(self.status(), Booking.Status.PENDING)

    def test_owner_declines(self):
        self.client.force_login(self.owner)
        self.client.post(self.url('decline'))
        self.assertEqual(self.status(), Booking.Status.DECLINED)

    def test_renter_cannot_approve(self):
        self.client.force_login(self.renter)
        self.assertEqual(self.client.post(self.url('approve')).status_code, 404)
        self.assertEqual(self.status(), Booking.Status.PENDING)

    def test_stranger_gets_404(self):
        self.client.force_login(self.stranger)
        for action in ('approve', 'decline', 'cancel'):
            self.assertEqual(self.client.post(self.url(action)).status_code, 404)
        self.assertEqual(self.status(), Booking.Status.PENDING)

    def test_renter_cancels_pending(self):
        self.client.force_login(self.renter)
        self.client.post(self.url('cancel'))
        self.assertEqual(self.status(), Booking.Status.CANCELLED)

    def test_renter_cancels_approved(self):
        self.booking.status = Booking.Status.APPROVED
        self.booking.save()
        self.client.force_login(self.renter)
        self.client.post(self.url('cancel'))
        self.assertEqual(self.status(), Booking.Status.CANCELLED)

    def test_cannot_cancel_declined(self):
        self.booking.status = Booking.Status.DECLINED
        self.booking.save()
        self.client.force_login(self.renter)
        self.client.post(self.url('cancel'))
        self.assertEqual(self.status(), Booking.Status.DECLINED)

    def test_get_not_allowed(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url('approve')).status_code, 405)

    def test_anonymous_redirected_to_login(self):
        response = self.client.post(self.url('approve'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_unknown_action_is_404(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(self.url('explode')).status_code, 404)


class MyBookingsTests(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.renter = make_user('renter')
        self.item = make_item(self.owner, title='Ski set')
        make_booking(self.item, self.renter, d(0), d(2), Booking.Status.PENDING)

    def test_requires_login(self):
        response = self.client.get(reverse('my_bookings'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_shows_requests_for_both_roles(self):
        self.client.force_login(self.renter)
        self.assertContains(self.client.get(reverse('my_bookings')), 'Ski set')
        self.client.force_login(self.owner)
        response = self.client.get(reverse('my_bookings'))
        self.assertContains(response, 'requested by renter')
        self.assertContains(response, 'Approve')