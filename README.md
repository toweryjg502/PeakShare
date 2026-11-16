<div align="center">

# 🏔️ PeakShare

### Peer-to-peer outdoor gear rentals for the App State community

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![Status](https://img.shields.io/badge/status-early%20development-orange?style=for-the-badge)

[About](#about) · [Features](#features) · [Tech stack](#tech-stack) · [Get started](#get-started) · [Stripe testing](#test-stripe-checkout) · [Roadmap](#roadmap) · [Team](#team)

</div>

---

> PeakShare is an early-development Information Systems senior project at Appalachian State University. The app is intended for App State students, faculty, and staff. It is not affiliated with or endorsed by Appalachian State University.

## About

Outdoor recreation in the Blue Ridge Mountains can be expensive, while useful gear often sits unused in closets and storage units. PeakShare is a campus-focused marketplace concept that helps community members rent outdoor equipment from one another.

Lenders can list gear and set availability. Renters can browse listings, request dates, and pay through a Stripe test-mode checkout flow. The project is being developed as an MVP and is not ready for public, live-payment use.

## Features

- **Campus accounts:** registration restricted to `@appstate.edu` email addresses, with single-use verification links.
- **Gear listings:** categories, descriptions, daily prices, condition, pickup instructions, and listing photos.
- **Browse and search:** filter by keyword, category, condition, price range, and availability dates; sort by newest, price, or title.
- **Booking and availability:** date requests, lender approval, blackout dates, and conflict checks.
- **Stripe Connect test flow:** lender onboarding, card checkout, webhook payment updates, and lender transfers after both sides confirm return.
- **Rental handoff records:** renter pickup photos and lender return photos are required before both sides can confirm each handoff.
- **Dispute reporting:** participants can flag an issue; the transfer is held for admin review.
- **Reviews:** renter and lender can review each other after a completed rental.
- **Price guidance:** listing forms suggest a starting price using active listings in the category and the item condition. The lender sets the final price.
- **Admin:** Django admin pages for listings, bookings, condition photos, alerts, reviews, and disputes.
- **Rental terms acknowledgment:** booking requests record acceptance of the displayed rental terms. This is not a legal liability waiver.

## Tech stack

| Area | Technology |
|---|---|
| Application | Python, Django |
| Local database | SQLite |
| Hosted database option | PostgreSQL through `DATABASE_URL` (for example, Neon) |
| Payments | Stripe Checkout and Connect |
| Images | Django file storage and Pillow |
| Configuration | Environment variables loaded from a local `.env` file |

## Get started

### Requirements

- Python compatible with the pinned dependencies in `requirements.txt`
- Git
- A Stripe account and Stripe CLI only if you want to try checkout

### Install and run

```bash
git clone https://github.com/toweryjg502/PeakShare.git
cd PeakShare

python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
python -m pip install -r requirements.txt
```

Create a fresh Django secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Create a `.env` file in the project root and add the generated value:

```dotenv
SECRET_KEY='paste-your-new-secret-key-here'
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

Apply database migrations and start Django:

```bash
python manage.py migrate
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) to browse, or [http://127.0.0.1:8000/accounts/register/](http://127.0.0.1:8000/accounts/register/) to create an account. In local development, verification email is printed in the Django terminal.

To create a Django admin account, run `python manage.py createsuperuser` and visit [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/).

The app uses a local SQLite database unless `DATABASE_URL` is set. A new local database does not include accounts or records from another computer. Keep `.env` and any database credentials private; `.env` is excluded from Git.

## Test Stripe checkout

Stripe checkout is optional for running the site. Use test-mode credentials only while developing.

1. Add your Stripe test keys to the project-root `.env`:

   ```dotenv
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_PUBLISHABLE_KEY=pk_test_...
   ```

2. Install the [Stripe CLI](https://docs.stripe.com/stripe-cli) and authenticate:

   ```bash
   stripe login
   ```

3. Start a local webhook listener in a second terminal:

   ```bash
   stripe listen --events checkout.session.completed,checkout.session.async_payment_succeeded,checkout.session.async_payment_failed,checkout.session.expired --forward-to 127.0.0.1:8000/bookings/stripe/webhook/
   ```

4. Copy the `whsec_...` value printed by the CLI into `.env` as `STRIPE_WEBHOOK_SECRET`, then restart Django.
5. Use two verified accounts. The lender must finish Stripe Connect payout setup. The lender approves a booking; the renter selects **Pay now**.
6. Use a Stripe test card such as `4242 4242 4242 4242`, with any future expiry and any three-digit CVC.

The current test flow charges the rental amount at checkout. After pickup and return are confirmed by both participants, the app attempts to transfer 90% of the rental amount to the lender's Stripe balance; the platform retains 10% before Stripe processing fees. The transfer is held if a participant flags a dispute. Test payouts and checkout do not mean the flow is ready for live payments.

**Security deposits are not implemented.** The app also does not yet provide complete refund, cancellation, or dispute-resolution workflows. Do not use live payment keys or accept real payments until payment handling and the applicable marketplace terms have been reviewed and completed.

## Roadmap

### Built

- Campus email-restricted registration and single-use verification
- Listings, listing photos, and category browsing
- Booking requests, availability calendars, and blackout dates
- Search, filters, and sorting
- Stripe test checkout, Connect onboarding, webhook payment updates, and delayed lender transfer
- Pickup and return photo records with two-party confirmation
- Dispute flagging and admin review
- Dual-sided reviews and category-based price suggestions

### Remaining before a public launch

- Decide whether to require security deposits, which listings need them, and how holds or refunds will work
- Prepare and review a proper liability waiver and marketplace terms; the current acknowledgment is basic rental guidance only
- Complete payment cancellation, refund, failed-transfer, and dispute-resolution processes
- Configure production email, media storage, hosting, domain, and deployment security settings
- Seed listings and test the full renter/lender journey with the campus community

### Out of scope for the current MVP

Real-time chat, native push notifications, and machine-learning-based pricing.

## Team

| Name | Role |
|---|---|
| Jared Towery | Project Manager |
| Max Phillips | Developer |

Appalachian State University · Walker College of Business · Fall 2026

---

<sub>PeakShare is a student project and is not officially affiliated with or endorsed by Appalachian State University. Listing, rental, payment, and liability terms require review before public launch.</sub>
