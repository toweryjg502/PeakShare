<div align="center">

# 🏔️ PeakShare

### Peer-to-peer outdoor gear rentals, built for the App State community

![Status](https://img.shields.io/badge/status-in%20development-orange?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![Stripe](https://img.shields.io/badge/Stripe-635BFF?style=for-the-badge&logo=stripe&logoColor=white)
![Neon](https://img.shields.io/badge/Neon-00E699?style=for-the-badge&logo=postgresql&logoColor=black)

[The Problem](#the-problem) · [Features](#key-features) · [Tech Stack](#tech-stack) · [Roadmap](#roadmap) · [Getting Started](#getting-started) · [Team](#team)

</div>

---

> [!NOTE]
> PeakShare is under active development as our Information Systems senior project at Appalachian State University (Fall 2026). See the [Roadmap](#roadmap) for current progress.

## The Problem

App State sits in the Blue Ridge Mountains, but outdoor recreation is expensive. A basic ski or snowboard rental at nearby Beech Mountain runs roughly **$50 to $65 per day**, and with lift tickets and other gear a single day can top **$150**. Many students skip the region's biggest draw because of cost.

Meanwhile, plenty of students own quality gear that sits unused in dorm closets and storage units. Generic marketplaces like Facebook Marketplace and Craigslist don't verify users, don't manage return schedules, and offer no protection against damaged or stolen gear.

## The Solution

PeakShare is a closed-loop marketplace where verified App State students, faculty, and staff rent gear from each other at accessible daily rates (for example, **$15 to $20 per day**). Lenders earn money from idle equipment, and renters get affordable access to the outdoors.

## Key Features

| | Feature | Description |
|---|---|---|
| 🔐 | **Campus-verified accounts** | Registration restricted to `appstate.edu` emails with single-use SMTP verification links |
| 📦 | **Item listings** | Photos, daily pricing, categories, and pickup and drop-off instructions |
| 🔎 | **Search and filters** | Browse by category, price range, and date availability |
| 📅 | **Availability calendar** | Lenders set blackout dates, and renters request start and end dates |
| 💳 | **Split payments** | Stripe Connect routes 90% to the lender and 10% to the platform, with deposit holds on high-value items |
| 📸 | **Photo verification** | Timestamped photos at handoff and return to reduce damage disputes |
| ⭐ | **Dual-sided reviews** | Renters and lenders rate each other from 1 to 5 stars |
| 📝 | **Digital liability waiver** | Required before checkout |
| 💲 | **Pricing suggestions** | Recommended rates based on retail value, condition, and category demand |
| 🛠️ | **Admin portal** | Django admin for dispute review and listing oversight |

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python, Django |
| **Database** | Neon (serverless PostgreSQL) |
| **Payments** | Stripe Connect API |
| **Authentication** | Custom SMTP email verification (`appstate.edu` only) |
| **Hosting (target)** | Free-tier services such as Render for the web app and Cloudinary for media |

The project is designed to run on open-source frameworks and free-tier cloud services, keeping the pre-launch operating budget at **$0**.

## Roadmap

We are building a focused MVP first and adding secondary features only after the core works.

**MVP core**
- [ ] `appstate.edu` email authentication
- [ ] Item listings by category
- [ ] Calendar-based booking
- [ ] Stripe split payments and deposit holds

**Next**
- [ ] Pre- and post-rental photo verification
- [ ] Digital liability waiver at checkout
- [ ] Dual-sided review system
- [ ] Dynamic pricing recommendations
- [ ] Search and filtering
- [ ] Admin dispute review

**Out of scope for now:** real-time chat, native push notifications, and machine-learning-based pricing.

### Launch Goals

Targets for the first 45 days after deployment:

| Metric | Target |
|---|---|
| Active listings | 50+ across at least 4 categories |
| Completed transactions | 30 |
| Successful rental rate | 95% without dispute escalation |

To avoid an empty marketplace at launch, we plan to seed 30+ listings by partnering with App State outdoor clubs and student organizations.

## Getting Started

```bash
# Clone the repository
git clone https://github.com/toweryjg502/PeakShare.git
cd PeakShare

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Set up the database
python manage.py migrate

# Create an admin account
python manage.py createsuperuser

# Run the development server
python manage.py runserver
```

You will also need environment variables for your Neon database connection, Stripe test keys, and email (SMTP) settings. **Never commit real keys or connection strings to the repository.**

<details>
<summary><b>Known risks and mitigations</b></summary>

<br>

| Risk | Mitigation |
|---|---|
| Injury liability | Mandatory waiver at checkout, and platform terms stating PeakShare is a listing broker only |
| Payment failures and disputes | Stripe Connect standard flows with webhook error handling, and authorization holds before handoff |
| Scope creep | Strict MVP-first development |
| Damaged, lost, or stolen gear | Timestamped photos, security deposit holds, and admin dispute review |
| Empty marketplace at launch | Pre-launch seeding with campus outdoor clubs |
| University SSO restrictions | Custom SMTP verification instead of Shibboleth/DUO integration |

</details>

## Team

| Name | Role |
|---|---|
| **Jared Towery** | Project Manager |
| **Max Phillips** | Developer |

Appalachian State University, Walker College of Business

---

<sub>PeakShare is a student project and is not officially affiliated with or endorsed by Appalachian State University. Terms of service and liability waiver language will be reviewed with legal counsel before any public release.</sub>
