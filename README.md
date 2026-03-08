# BidsConnect

**BidsConnect** is a tender and bidding platform backend for Tanzania. It connects organizations that publish tenders with suppliers who submit and manage bids, and supports company profiles, document management, marketplace, legal documents, and payments.

- **Domain:** [bidsconnect.co.tz](https://bidsconnect.co.tz)
- **API base:** `https://your-domain/api/v1/`

## Features

- **Accounts** — User registration, companies, invitations, documents, offices, certifications, financials, personnel, experience
- **Tenders** — Categories, agencies, procurement processes, tender CRUD, requirements, subscriptions, notifications, **tender digest** (daily/weekly email when you subscribe to a category)
- **Bids** — Bid submission and responses (financial, turnover, experience, personnel, documents, evaluations)
- **Marketplace** — Categories, products/services, RFQs, quotes, reviews, messages
- **Legal** — Power of attorney and related legal documents (Word/PDF export via python-docx and reportlab)
- **Automation** — Power of attorney, tender securing declaration, litigation history, cover letters
- **Payments** — Payment records (generic, linked to any content). *Note: Payment gateway (e.g. M-Pesa) is not integrated; status is recorded by the client. Integrate webhooks for production.*
- **Notifications & Analytics** — In-app notification list (tender notifications), basic analytics stats (tender/bid counts)

## Tech Stack

- **Django 4.2** + **Django REST Framework**
- **JWT** (Simple JWT) + **Djoser** for auth
- **SQLite** (default; configurable for PostgreSQL in production)
- **django-cors-headers**, **django-filter**

## Quick Start

### Prerequisites

- Python 3.10+
- pip

### Setup

```bash
# Clone and enter project
cd bidsconnect

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Optional: copy env example and set variables
cp .env.example .env

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

API: **http://127.0.0.1:8000/api/v1/**  
Admin: **http://127.0.0.1:8000/admin/**

### Environment Variables

Copy `.env.example` to `.env` and set as needed:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | (insecure default in code) |
| `DEBUG` | Debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated hosts | — |
| `DATABASE_URL` | DB URL (optional) | SQLite |
| `STATIC_ROOT` | Static files path | `BASE_DIR/staticfiles` |
| `MEDIA_ROOT` | Uploaded files path | `BASE_DIR/media` |
| `EMAIL_BACKEND` | Email backend | `console` (dev) |
| `DEFAULT_FROM_EMAIL` | Sender for emails | `noreply@bidsconnect.co.tz` |
| `SITE_URL` | Base URL for links (e.g. invitations) | — |

**Email in production:** Set `EMAIL_BACKEND` to `django.core.mail.backends.smtp.EmailBackend` and configure `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL`. See `.env.example` for an example.

See [docs/API.md](docs/API.md) for full API reference and [docs/SYSTEM_FLOW.md](docs/SYSTEM_FLOW.md) for system flows.

### Running tests

With the virtual environment activated and dependencies installed:

```bash
python manage.py test
```

To run specific test modules:

```bash
python manage.py test accounts.tests.test_invitation_accept accounts.tests.test_webhook_auth bids.tests.test_bid_scope_and_permissions
```

New tests cover: invitation accept (email match and company limit), document expiry webhook authentication, and bid list scoping by company membership.

## Documentation

| Document | Description |
|----------|-------------|
| [API Documentation](docs/API.md) | All API endpoints, auth, request/response details |
| [System Flow](docs/SYSTEM_FLOW.md) | User journeys, tender–bid flow, data flow diagrams |
| [BidsConnect Spec](docs/BIDS_CONNECT_SPEC.md) | Product requirements, tender/bid rules, fees, user journey |
| [User Onboarding & Teams](docs/USER_ONBOARDING_AND_TEAMS.md) | Onboarding, company members, roles, company tasks, tender conversations |
| [User Journeys](docs/USER_JOURNEYS.md) | Five flows: onboarding, team, applying for tender, marketplace advertising, RFQ (steps + API hints) |
| [Frontend Integration](docs/FRONTEND_INTEGRATION.md) | How to consume the API from the frontend, what data to pass, fetch/axios examples |
| [Product feature suggestions](docs/PRODUCT_FEATURE_SUGGESTIONS.md) | UX and product design ideas (onboarding, payments, reminders, trust, quick wins) |

## Authentication

The API uses **JWT**. Obtain tokens via Djoser:

```bash
# Register (optional, if open)
POST /api/v1/accounts/users/

# Login → returns access + refresh tokens
POST /api/v1/accounts/jwt/create/
Body: { "email": "user@example.com", "password": "..." }

# Use token in requests
Authorization: Bearer <access_token>
```

Refresh token:

```bash
POST /api/v1/accounts/jwt/refresh/
Body: { "refresh": "<refresh_token>" }
```

## Project Structure

```
bidsconnect/
├── bidsconnect/          # Project settings, urls, wsgi
├── accounts/             # Users, companies, documents, invitations
├── tenders/               # Tenders, categories, subscriptions, notifications
├── bids/                  # Bids and bid responses
├── marketplace/           # Products, RFQs, quotes
├── legal/                 # Legal documents (power of attorney)
├── automation/            # Generated documents (POA, declarations, cover letters)
├── payments/              # Payment records
├── notifications/         # (Placeholder)
├── analytics/             # (Placeholder)
├── docs/                  # API and system flow docs
├── manage.py
└── requirements.txt
```

## License

Proprietary — BidsConnect.
