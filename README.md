# EduTutor Pro — Modern Home Tuition & Online Tutoring Marketplace

A production-grade, full-featured **Home Tuition & Online Educator Marketplace** built entirely with **Python, Django, and Django Templates**. Inspired by the lead-discovery and matching workflows of leading home tuition portals (such as HomeTutorSite), EduTutor Pro delivers an original, modern user experience, a comprehensive multi-factor matching engine, atomic lead-unlocking economics, a configurable business commission engine, and a complete **Custom Business Administration Dashboard** that frees platform owners from relying on the default Django admin for everyday operations.

---

## Table of Contents
1. [Platform Architecture & Tech Stack](#platform-architecture--tech-stack)
2. [User Roles & Access Control](#user-roles--access-control)
3. [Key Modules & Feature Checklist](#key-modules--feature-checklist)
4. [Intelligent Tutor-Student Matching Engine](#intelligent-tutor-student-matching-engine)
5. [Lead Economics & Contact Privacy Architecture](#lead-economics--contact-privacy-architecture)
6. [Configurable Commission Rules Engine](#configurable-commission-rules-engine)
7. [Custom Business Administration Console](#custom-business-administration-console)
8. [Database Schema & Models](#database-schema--models)
9. [Pre-Seeded Accounts & Demo Credentials](#pre-seeded-accounts--demo-credentials)
10. [Local Quickstart & Setup Guide](#local-quickstart--setup-guide)
11. [PostgreSQL Production Database Setup](#postgresql-production-database-setup)
12. [Docker & Containerized Deployment](#docker--containerized-deployment)
13. [Payment Gateway & Webhook Integration](#payment-gateway--webhook-integration)
14. [REST API Documentation](#rest-api-documentation)
15. [Automated Testing Suite](#automated-testing-suite)
16. [Backup & Disaster Recovery](#backup--disaster-recovery)
17. [Feature Completion Report & Known Limitations](#feature-completion-report--known-limitations)

---

## 1. Platform Architecture & Tech Stack

- **Backend**: Python 3.12+ / 3.14, Django 5.1 / 6.1 LTS, Django ORM, PostgreSQL (with SQLite zero-config fallback)
- **Frontend Architecture**: 100% Server-Rendered Django Templates (MVT), Vanilla CSS Design System with dynamic CSS custom properties (`:root { --primary: ... }`), Lucide icon suite, responsive mobile-first grid
- **REST APIs**: Django REST Framework (DRF) v3.15+ exposing public and authenticated API endpoints with field-level contact masking
- **Background Tasks**: Celery & Redis ready for asynchronous notifications and lead match broadcasting
- **Static Assets & Media**: WhiteNoise for optimized static asset serving, Django Media storage for tutor verification credentials

```
Tutor-portal/
├── apps/
│   ├── accounts/         # Custom User, roles (Admin, Ops, Tutor, Parent, Student), referrals
│   ├── api/              # Django REST Framework serializers, viewsets, and endpoints
│   ├── billing/          # Commission engine, subscription plans, wallets, invoices, payments
│   ├── communication/    # In-platform messaging, conversations, notifications
│   ├── core/             # CompanySettings, ThemeSettings, announcements, audit logs
│   ├── custom_admin/     # 100% Custom Business Admin portal (KPIs, approvals, reports)
│   ├── engagements/      # Demo classes, tuition agreements, lessons, progress, reviews
│   ├── leads/            # Tuition requirements, matching engine, atomic unlock service
│   ├── parents/          # Parent profile, student profiles, requirement management
│   └── tutors/           # Tutor profile, subjects, weekly availability, document verification
├── config/               # Project settings, URL routing, WSGI/ASGI
├── templates/            # Unified template library across all portals
│   ├── accounts/
│   ├── billing/
│   ├── communication/
│   ├── core/
│   ├── custom_admin/
│   ├── engagements/
│   ├── leads/
│   ├── parents/
│   └── tutors/
├── static/               # CSS styles, design tokens, JavaScript helpers
├── tests/                # Comprehensive automated unit & integration test suites
└── docker-compose.yml    # Full multi-container stack (web, postgres, redis, celery)
```

---

## 2. User Roles & Access Control

The platform enforces strict backend role-based access control (RBAC):

1. **Super Administrator**: Complete platform governance, revenue model toggle, commission rule authoring, subscription plan builder, theme customizer, branding, financial ledger, and system audit logs.
2. **Operations Manager**: Verifies tutor credentials, reviews posted leads, assigns/reassigns tutors, monitors demo classes, and resolves customer complaints.
3. **Verified Tutor**: Manages subjects, hourly/monthly rates, service areas, and availability calendar. Browses leads, unlocks parent contact details atomically via credits, applies for tuitions, schedules demo sessions, tracks ongoing students, and submits lesson progress notes.
4. **Parent / Guardian**: Posts tuition requirements with board/curriculum/timing needs, reviews matched recommendations, invites tutors, schedules demo classes, confirms tuitions, pays tuition fees, logs demo attendance, and reviews tutors.
5. **Student**: Protected sub-profile managed by guardians with lesson schedules, study material links, and teacher progress reports.

---

## 3. Key Modules & Feature Checklist

| Module | Feature Set | Implementation Status |
|---|---|---|
| **Public Website** | Hero search, subject taxonomy, city filters, "How It Works", Pricing, Testimonials, Terms, Privacy | **Complete** |
| **Tutor Discovery** | Filter by subject, class, board, city, locality, teaching mode, gender, rating, fee | **Complete** |
| **Lead Posting** | Multi-step requirement posting, unique lead IDs (`TUT-XXXXXX`), protected address | **Complete** |
| **Intelligent Matching** | 6-factor weighted scoring algorithm with detailed match explanations | **Complete** |
| **Contact Privacy** | Contact details masked; atomic credit deduction prevents double spending | **Complete** |
| **Commission Engine** | Configurable Models A–F, rate %, fixed fee, min/max bounds, GST tax, invoices | **Complete** |
| **Subscription & Credits** | Credit packages (free, purchased, bonus), plans, renewal handling | **Complete** |
| **Demo Class Workflow** | Request, accept/reschedule, online meeting links, parent attendance signoff | **Complete** |
| **Tuition Engagement** | Confirmed agreement tracking, lesson schedules, attendance logs, student progress reports | **Complete** |
| **Reviews & Complaints** | Verified review submissions, parent complaint filing, operational resolution | **Complete** |
| **In-Platform Messaging** | Direct parent-tutor messaging conversations, unread notifications | **Complete** |
| **Custom Admin Portal** | Full business console, KPI dashboard, CSV exports, audit trails | **Complete** |
| **Dynamic Theming** | Live primary/secondary color palette configuration via CSS variables | **Complete** |
| **REST API** | Secure endpoints for mobile apps with automatic data privacy filtering | **Complete** |

---

## 4. Intelligent Tutor-Student Matching Engine

Located in `apps/leads/matching.py`, the matching engine evaluates active verified tutors against tuition requirements across 6 weighted dimensions:

1. **Subject Compatibility (Weight: 35%)**: Checks whether the tutor explicitly lists the requested subject(s) in their profile subjects.
2. **Location & Service Radius (Weight: 25%)**: Matches locality and ensures the student's area falls within the tutor's configured travel radius.
3. **Class & Curriculum Alignment (Weight: 20%)**: Compares student education level (e.g., Class 10 CBSE/ICSE) with tutor offerings.
4. **Teaching Mode Compatibility (Weight: 10%)**: Matches Home Tuition, Online Tuition, or Hybrid preferences.
5. **Budget Compatibility (Weight: 10%)**: Compares parent budget with tutor monthly rate expectations.
6. **Verification Quality Boost (+5% bonus)**: Verified tutors receive priority matching ranking.

### Generated Match Reasons
Each match produces human-readable explanation tags displayed in the parent portal and admin console:
- *"Specialized in Mathematics & Physics"*
- *"Based in Indiranagar within active service radius"*
- *"Teaches CBSE curriculum for Class 10"*
- *"Available during requested Evening slots"*

---

## 5. Lead Economics & Contact Privacy Architecture

To ensure student/parent privacy and prevent platform bypass:
- **Public & Directory Views**: Displays student grade, board, subjects, city, locality, budget, and learning goals. Sensitive fields (`parent_contact_name`, `contact_phone`, `contact_email`, `full_address`) are **never rendered in HTML or returned via public API responses**.
- **Atomic Contact Unlock (`apps/leads/services.py`)**:
  - Uses `select_for_update()` inside a `transaction.atomic()` block on `ContactCreditWallet`.
  - Verifies wallet balance (`free_credits + purchased_credits + bonus_credits >= credits_required`).
  - Deducts credits atomically and records an immutable `CreditTransaction`.
  - Prevents race conditions and double charges if duplicate requests occur.
  - Automatically sends notification to the parent informing them that a verified tutor has unlocked their requirement.

---

## 6. Configurable Commission Rules Engine

EduTutor Pro features a configurable business rules engine (`apps/billing/services.py`) that can be toggled on/off globally or configured dynamically from the **Custom Admin Console**:

### Supported Commission Models
- **Model A (No Commission)**: Tutors and parents settle payments directly; the platform earns revenue exclusively through subscription plans and contact credits.
- **Model B (One-Time Fixed Confirmation Fee)**: Charges a flat fee (e.g., ₹1,000) when a tuition agreement is confirmed.
- **Model C (First-Month Percentage)**: Calculates a percentage (e.g., 40%) of the first month's agreed tuition fee, with optional min/max caps and applicable GST.
- **Model D (Recurring Monthly Commission)**: Applies commission to eligible monthly tuition cycles.
- **Model E (Per-Session Commission)**: Calculates commission per verified lesson attendance.
- **Model F (Hybrid Model)**: Combines plan subscriptions, credit purchases, and confirmation commissions.

### Critical Integrity Guarantees
- Switching off commission never modifies or deletes historical commission records.
- When commission is generated, an official `Invoice` is created with unique invoice numbers (`INV-XXXXXX`) and line items.
- Duplicate prevention ensures idempotency: repeated confirmations or webhook retries will never generate duplicate commission records.

---

## 7. Custom Business Administration Console

Accessible at `/admin-portal/` (requires `SUPER_ADMIN` or `OPERATIONS` role). **Does not require or depend on Django Admin**:

- **Executive KPI Dashboard**: Live database metrics for Total Tutors, Pending Verifications, Active Parents, Open Leads, Scheduled Demos, Confirmed Tuitions, Commission Revenue, and Open Complaints.
- **Tutor Management (`/admin-portal/tutors/`)**: Review tutor bio, subjects, rate cards, and uploaded government ID / degree certificates. Approve, reject, or suspend tutor profiles with custom administrative notes.
- **Lead Oversight (`/admin-portal/leads/`)**: Filter by city, status, and subjects. Manually assign/reassign leads to specific tutors or trigger automated match generation.
- **Commission Rules Manager (`/admin-portal/commissions/`)**: Toggle global commission ON/OFF, create and edit tiered commission rules, view ledger of pending/settled commissions, issue waivers, or mark settlements.
- **Subscription Plans (`/admin-portal/subscriptions/`)**: Create, edit, and price subscription tiers with customizable credit allocations and featured badges.
- **Financial Ledger (`/admin-portal/financials/`)**: Audit all invoices, payments, credit purchases, and refund transactions.
- **Complaints & Dispute Resolution (`/admin-portal/complaints/`)**: Investigate disputes, communicate resolution decisions, and authorize tutor replacements or credit refunds.
- **Announcements Engine (`/admin-portal/announcements/`)**: Publish targeted announcements to tutors, parents, or specific cities.
- **Company Branding (`/admin-portal/branding/`)**: Configure platform name, support phone, email, WhatsApp, currency symbols, and legal terms without editing code.
- **Live Theme Customizer (`/admin-portal/theme/`)**: Configure Primary, Secondary, Background, Sidebar, and Text color hex codes, button radius, and typography styles. Changes apply globally across the platform instantaneously via CSS variables.
- **Business Reports & CSV Export (`/admin-portal/reports/`)**: Generate and download detailed CSV exports for Leads, Tutors, and Financial Revenue.
- **Audit Logs (`/admin-portal/audit-logs/`)**: Immutable trail of administrative actions, status changes, and rule modifications.

---

## 8. Database Schema & Models

```
accounts:
  User (AbstractUser: role, phone_number, city, locality, referral_code, referred_by)

core:
  CompanySettings (Singleton: company_name, support_email, currency, commission_enabled, etc.)
  ThemeSettings (Singleton: primary_color, secondary_color, border_radius, etc.)
  Announcement (title, target_role, target_city, is_published, expires_at)
  AuditLog (actor, action, target_model, object_id, details, ip_address, created_at)

tutors:
  TutorProfile (user, headline, bio, qualification, experience_years, teaching_mode, rates, status)
  TutorSubject (tutor, subject_name, classes_offered, curriculum, fee_per_month)
  TutorAvailability (tutor, day_of_week, slot [MORNING/AFTERNOON/EVENING/NIGHT], is_active)
  TutorDocument (tutor, document_type, document_name, document_file, status)

parents:
  ParentProfile (user, city, locality, address_line)
  StudentProfile (parent, student_name, grade_level, board_curriculum, school_name)

leads:
  TuitionRequirement (lead_id, parent, student, title, subjects, city, locality, status, contact_phone)
  TutorMatch (requirement, tutor, match_score, match_reasons, is_recommended_by_admin)
  LeadApplication (requirement, tutor, proposed_monthly_fee, cover_message, status)
  LeadUnlock (requirement, tutor, credits_spent, created_at)

billing:
  CommissionRule (rule_name, model_type, rate_percentage, min_commission, max_commission, tax_percentage)
  CommissionRecord (record_id, engagement, tutor, commission_amount, tax_amount, total_amount, status)
  SubscriptionPlan (name, price, duration_days, lead_credits_included, is_featured_badge)
  TutorSubscription (tutor, plan, start_date, end_date, amount_paid, status)
  ContactCreditWallet (tutor, free_credits, purchased_credits, bonus_credits)
  CreditTransaction (wallet, amount, transaction_type, balance_after, reference_note)
  Invoice (invoice_number, user, total_amount, status) & InvoiceLineItem
  Payment (payment_id, user, amount, gateway, status) & Refund

engagements:
  DemoClass (requirement, tutor, parent, scheduled_datetime, status, attendance_confirmed_by_parent)
  TuitionEngagement (requirement, tutor, parent, agreed_fee, start_date, status)
  LessonSchedule (engagement, day_of_week, start_time, end_time)
  LessonRecord (engagement, lesson_date, attendance_status, topics_covered, homework_assigned)
  StudentProgressReport (engagement, report_period, academic_improvement, tutor_remarks)
  Review (tutor, parent, rating, review_text, is_approved)
  Complaint (filed_by, against_user, subject, description, resolution_status)

communication:
  Conversation (participant_1, participant_2, updated_at)
  Message (conversation, sender, body, is_read, sent_at)
  Notification (recipient, title, message, link_url, is_read, created_at)
```

---

## 9. Pre-Seeded Accounts & Demo Credentials

To immediately evaluate all portals, the project comes pre-seeded with realistic records (`python manage.py seed_data`):

| Portal / Role | Username | Password | Notes / Context |
|---|---|---|---|
| **Super Admin** | `admin` | `admin123` | Complete business control & Custom Admin Portal |
| **Operations Manager** | `ops_manager` | `ops123` | Lead management, tutor verification approvals |
| **Tutor (Senior Math/Phys)** | `tutor_rajesh` | `tutor123` | Dr. Rajesh Nambiar (Verified, active tuitions, 10 credits) |
| **Tutor (English/Lang)** | `tutor_ananya` | `tutor123` | Ananya Sharma (Verified, ICSE/IGCSE specialist) |
| **Tutor (Chemistry)** | `tutor_vikram` | `tutor123` | Vikram Malhotra (Pending verification document) |
| **Parent (Class 10 CBSE)** | `parent_meena` | `parent123` | Meena Iyer (Posted requirements `TUT-874167`, active demo) |
| **Parent (Class 8 ICSE)** | `parent_sanjay` | `parent123` | Sanjay Gupta (Open requirement `TUT-874315`) |

---

## 10. Local Quickstart & Setup Guide

### Prerequisites
- Python 3.12 or newer
- Git

### 1. Clone & Set Up Virtual Environment
```bash
git clone <repository_url>
cd Tutor-portal

python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize Database & Apply Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Load Pre-Configured Demo Data
```bash
python manage.py seed_data
```

### 5. Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### 6. Start the Development Server
```bash
python manage.py runserver 127.0.0.1:8000
```
Open **`http://127.0.0.1:8000/`** in your browser.

---

## 11. PostgreSQL Production Database Setup

For production deployments using PostgreSQL:

1. Create the PostgreSQL database and user:
```sql
CREATE DATABASE edututor_db;
CREATE USER edututor_user WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE edututor_db TO edututor_user;
ALTER DATABASE edututor_db OWNER TO edututor_user;
```

2. Configure your environment variables in `.env`:
```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=edututor_db
DB_USER=edututor_user
DB_PASSWORD=your_secure_password
DB_HOST=127.0.0.1
DB_PORT=5432
```

3. Run migrations:
```bash
python manage.py migrate
```

---

## 12. Docker & Containerized Deployment

Run the complete multi-service stack (Django + Gunicorn, PostgreSQL, Redis, Celery Worker) with one command:

```bash
# Build and run containers in background
docker compose up --build -d

# Check running services
docker compose ps

# Seed demo data inside container
docker compose exec web python manage.py seed_data

# View logs
docker compose logs -f web
```

The application will be accessible at `http://localhost:8000`.

---

## 13. Payment Gateway & Webhook Integration

EduTutor Pro supports **Razorpay**, **Stripe**, and **UPI / Direct Bank Settlements**.

### Razorpay Configuration
Set in `.env`:
```env
PAYMENT_GATEWAY_PROVIDER=razorpay
RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxx
RAZORPAY_WEBHOOK_SECRET=xxxxxxxxxxxxxxx
```

Webhook listener handles `payment.captured` and `refund.processed` events atomically:
- Verifies HMAC-SHA256 signature against `RAZORPAY_WEBHOOK_SECRET`.
- Credits tutor wallet or marks invoice settled.
- Idempotency ensures duplicate webhook deliveries are safely skipped.

### Stripe Configuration
```env
PAYMENT_GATEWAY_PROVIDER=stripe
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxxxxxxxxx
STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxx
```

---

## 14. REST API Documentation

EduTutor Pro provides a complete Django REST Framework API under `/api/v1/`:

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/v1/tutors/` | `GET` | Public | List & search verified tutors (`?city=`, `?subject=`, `?mode=`) |
| `/api/v1/tutors/<id>/` | `GET` | Public | Detailed tutor profile, subjects, and availability slots |
| `/api/v1/leads/` | `GET` | Public | Open tuition requirements feed (**sensitive phone/address masked**) |
| `/api/v1/leads/<lead_id>/` | `GET` | Public / Tutor | Lead details (unmasked if unlocked by requesting tutor) |
| `/api/v1/leads/<lead_id>/unlock/` | `POST` | Tutor Auth | Atomically unlock lead contact details using credits |
| `/api/v1/leads/<lead_id>/matches/`| `GET` | Parent / Staff | Calculate/fetch matched tutors with weighted scores & reasons |
| `/api/v1/subscriptions/` | `GET` | Public | List active subscription packages and benefits |
| `/api/v1/company/` | `GET` | Public | Platform branding, tax rates, support details, and policy text |

---

## 15. Automated Testing Suite

The repository includes comprehensive automated tests covering all critical workflows:

```bash
python manage.py test tests
```

### Covered Test Cases:
1. `test_tutor_matching_engine`: Verifies 6-factor scoring, score threshold (>= 80), and match reason generation.
2. `test_contact_privacy_and_lead_unlock`: Validates that phone/address are hidden from public views, ensures atomic credit deduction, and verifies duplicate unlock prevention.
3. `test_commission_calculation_when_enabled`: Validates Model C (40% first month calculation + 18% GST + automatic invoice generation).
4. `test_commission_engine_when_disabled`: Confirms that Model A prevents any commission records from being created when the global toggle is OFF.
5. `test_demo_class_workflow`: Tests demo state progression, feedback submission, and parent attendance signoff.
6. `test_public_pages_and_custom_admin_access`: Ensures anonymous users are blocked from `/admin-portal/` and super admins have full dashboard access.
7. `test_rest_api_endpoints_and_privacy`: Validates DRF API endpoints and verifies that sensitive phone/address fields are not leaked in public responses.

---

## 16. Backup & Disaster Recovery

### Automated Database Backup (PostgreSQL)
Run daily via cron:
```bash
#!/bin/bash
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/var/backups/edututor"
mkdir -p $BACKUP_DIR

# Export database dump
pg_dump -U edututor_user -h localhost -d edututor_db -F c -b -v -f "$BACKUP_DIR/edututor_$TIMESTAMP.dump"

# Retain backups for 30 days
find $BACKUP_DIR -name "*.dump" -mtime +30 -exec rm {} \;
```

### Database Restore Command
```bash
pg_restore -U edututor_user -d edututor_db -v /var/backups/edututor/edututor_YYYYMMDD_HHMMSS.dump
```

---

## 17. Feature Completion Report & Known Limitations

### Feature Completion
- **Public Portal**: Conversion-focused landing page, tuition discovery, how it works, pricing, contact, terms, privacy.
- **Tutor Operations**: Multi-step onboarding, document verification, subject management, weekly availability matrix, lead discovery, atomic contact unlock, applications, demo classes, and lesson progress.
- **Parent Portal**: Guided tuition requirement creation, matched recommendations review, demo management, one-click tuition confirmation, and ongoing progress review.
- **Business Administration**: Complete custom dashboard with live KPIs, tutor verification, lead management, commission rule authoring, subscription plan builder, theme customizer, dynamic branding, CSV exports, and audit logging.
- **Security & Privacy**: Field-level contact privacy, CSRF protection, secure passwords, and atomic database transactions.

### Known Limitations & Production Recommendations
1. **Live SMS / WhatsApp Sending**: The codebase includes the SMS/WhatsApp service layer. For production SMS delivery, configure your Twilio or Gupshup API credentials in `.env`.
2. **Real-time WebSockets**: In-platform messaging currently operates over standard HTTP polling. For sub-second chat updates, Django Channels can be connected to the existing Redis instance.
3. **Map Geolocation**: Distance matching uses locality coordinates and service radii. For street-level distance calculation, supply a Google Maps or Mapbox API key in settings.
