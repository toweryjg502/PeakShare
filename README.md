# PeakShare 🏔️

**PeakShare** is a peer-to-peer (P2P) outdoor gear-sharing web application engineered specifically for Appalachian State University students, faculty, and staff in Boone, NC. PeakShare connects campus community members who need accessible outdoor equipment with verified lenders who have idle gear to share.

---

## 👥 Team & Project Information

* **Project Manager:** Jared Towery (`Toweryjg@appstate.edu`)
* **Team Member:** Max Phillips (`Phillipst1@appstate.edu`)
* **Institution:** Appalachian State University
* **Budget Target:** $0 Operating Cost (Pre-Revenue)

---

## 🚀 Key Features & Charter Requirements

* **Campus Email Authentication:** Restricts registration strictly to `@appstate.edu` domain emails using one-time SMTP verification links, leveraging university Duo MFA security indirectly.
* **Automated 90/10 Split Payments:** Integrates Stripe Connect to process checkout transactions, hold security deposit pre-authorizations, and automatically distribute 90% of rental earnings to lenders while retaining a 10% platform fee.
* **Dynamic Inventory & Booking:** Real-time search filtering, interactive availability calendars, condition tagging, and reservation logs managed via Django and PostgreSQL.
* **Pre/Post Photo Verification:** Required timestamped photo uploads hosted securely on Cloudinary at handoff and return to prevent and resolve damage disputes.
* **Digital Legal Liability Waivers:** Mandatory digital waiver acceptance and terms-of-use compliance enforced during checkout prior to transaction authorization.
* **Dual-Sided Review Module:** Public 1-to-5-star rating and written feedback system for both renters and lenders to maintain platform trust.
* **Dynamic Pricing Recommendation Tool:** Automated rate guidance calculating suggested daily prices based on item retail value, condition grade, and category demand.
* **Administrative Governance:** Django's built-in portal provides real-time oversight for platform disputes, user management, and transaction auditing.

---

## 🛠️ Tech Stack & Architecture

| Component | Technology / Provider | Cost |
| :--- | :--- | :--- |
| **Language & Framework** | Python 3.11+, Django | $0 (Open Source) |
| **Frontend** | HTML5, CSS3, JavaScript, Tailwind CSS | $0 |
| **Database** | Serverless PostgreSQL via **Neon** | $0 (Free Tier) |
| **File / Photo Storage** | **Cloudinary** | $0 (Free Tier) |
| **Payment Gateway** | **Stripe Connect** (Test Mode) | Pay-as-you-go / $0 in test mode |
| **Transactional Email** | **Resend** or **Brevo** (SMTP) | $0 (Free Tier) |
| **Hosting & Deployment** | **Render** (Web Service) | $0 (Free Tier) |
| **Version Control** | GitHub | $0 |

---

## ⚙️ Getting Started (Local Development)

### Prerequisites
* Python 3.10+ installed
* Git installed

### 1. Clone the Repository
```bash
git clone [https://github.com/toweryjg502/peakshare.git](https://github.com/toweryjg502/peakshare.git)
cd peakshare
