# BidsConnect API Documentation

Base URL: **`/api/v1/`**

All authenticated endpoints expect:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

## Authentication (Djoser + JWT)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/accounts/users/` | No | Register new user |
| POST | `/api/v1/accounts/jwt/create/` | No | Login → `access`, `refresh` |
| POST | `/api/v1/accounts/jwt/refresh/` | No | Refresh access token |
| GET  | `/api/v1/accounts/users/me/` | Yes | Current user |
| PUT/PATCH | `/api/v1/accounts/users/me/` | Yes | Update current user |

---

## Accounts (`/api/v1/accounts/`)

All account endpoints (except auth above) are under `/api/v1/accounts/`. Nested company resources use `company_pk` (UUID).

### Users & companies

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/accounts/users/` | List / create user profiles |
| GET/PUT/PATCH | `/accounts/users/{id}/` | Retrieve / update user |
| GET/POST | `/accounts/companies/` | List / create companies |
| GET/PUT/PATCH/DELETE | `/accounts/companies/{id}/` | Company CRUD |
| GET/POST | `/accounts/companies/{company_pk}/users/` | Company users |
| GET/PUT/PATCH/DELETE | `/accounts/companies/{company_pk}/users/{id}/` | Company user CRUD |
| GET/POST | `/accounts/companies/{company_pk}/invitations/` | Invitations |
| GET/PUT/PATCH/DELETE | `/accounts/companies/{company_pk}/invitations/{id}/` | Invitation CRUD |

### Company resources (nested under `companies/{company_pk}/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `.../documents/` | Company documents |
| GET/PUT/PATCH/DELETE | `.../documents/{id}/` | Document CRUD |
| GET | `.../documents/export/` | **CSV export** of company documents |
| GET/POST | `.../offices/` | Offices |
| GET/POST | `.../certifications/` | Certifications |
| GET/POST | `.../sources-of-funds/` | Sources of funds |
| GET/POST | `.../annual-turnovers/` | Annual turnovers |
| GET/POST | `.../financial-statements/` | Financial statements |
| GET/POST | `.../litigations/` | Litigations |
| GET/POST | `.../personnel/` | Personnel |
| GET/POST | `.../experiences/` | Experiences |

### One-off endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/accounts/companies/{company_pk}/dashboard/` | Yes | Company dashboard summary |
| GET | `/accounts/companies/{company_pk}/documents/export/` | Yes (owner) | CSV export of documents |
| POST | `/accounts/invitations/accept/{token}/` | Yes | Accept invitation |
| POST | `/accounts/webhooks/documents/expiry/` | No | Document expiry webhook (body: `document_id`, `event`) |

### Audit logs

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/accounts/audit-logs/` | Admin | List audit logs |
| GET | `/accounts/audit-logs/{id}/` | Admin | Audit log detail |

---

## Tenders (`/api/v1/tenders/`)

### Reference data

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/tenders/categories/` | Categories (lookup by `slug`) |
| GET/POST | `/tenders/subcategories/` | Subcategories (filter: `?category=<slug>`) |
| GET | `/tenders/categories-with-subcategories/` | Categories with nested subcategories |
| GET/POST | `/tenders/procurement-processes/` | Procurement processes |
| GET/POST | `/tenders/agencies/` | Agencies |

### Tenders

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/tenders/tenders/` | List / create tenders (filter: `?status=`, `?category=`, `?subcategory=`) |
| GET/PUT/PATCH/DELETE | `/tenders/tenders/{slug}/` | Tender CRUD (slug) |
| POST | `/tenders/tenders/{slug}/publish/` | Publish tender |
| POST | `/tenders/tenders/{slug}/status/` | Update status |

### Tender nested (under tender slug)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/tenders/tenders/{slug}/required-documents/` | Required documents |
| GET/POST | `/tenders/tenders/{slug}/financial-requirements/` | Financial requirements |
| GET/POST | `/tenders/tenders/{slug}/turnover-requirements/` | Turnover requirements |
| GET/POST | `/tenders/tenders/{slug}/experience-requirements/` | Experience requirements |
| GET/POST | `/tenders/tenders/{slug}/personnel-requirements/` | Personnel requirements |
| GET/POST | `/tenders/tenders/{slug}/schedule-items/` | Schedule items |
| GET/POST | `/tenders/tenders/{slug}/technical-specifications/` | Technical specifications |
| POST | `/tenders/tenders/{slug}/award/` | Award action |

### Flat reference (optional)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/tenders/tender-documents/` | Tender required documents (flat) |
| GET/POST | `/tenders/tender-financials/` | Tender financial requirements |
| GET/POST | `/tenders/tender-turnovers/` | Turnover requirements |
| GET/POST | `/tenders/tender-experiences/` | Experience requirements |
| GET/POST | `/tenders/tender-personnel/` | Personnel requirements |
| GET/POST | `/tenders/tender-schedule-items/` | Schedule items |
| GET/POST | `/tenders/tender-technical-specs/` | Technical specs |
| GET/POST | `/tenders/subscriptions/` | Tender subscriptions |
| GET/PUT/PATCH | `/tenders/notification-preferences/` | Notification preferences |
| GET | `/tenders/tender-notifications/` | Tender notifications (read-only) |
| GET | `/tenders/tender-status-history/` | Tender status history (read-only) |

---

## Bids (`/api/v1/bids/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/bids/` | List / create bids |
| GET/PUT/PATCH/DELETE | `/bids/{id}/` | Bid CRUD |
| POST | `/bids/{id}/submit/` | Submit bid |

### Per-bid resources (`/bids/{bid_pk}/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `.../documents/` | Bid documents |
| GET/PUT/PATCH/DELETE | `.../documents/{id}/` | Bid document CRUD |
| GET/POST | `.../financial-responses/` | Financial responses |
| GET/POST | `.../turnover-responses/` | Turnover responses |
| GET/POST | `.../experience-responses/` | Experience responses |
| GET/POST | `.../personnel-responses/` | Personnel responses |
| GET/POST | `.../office-responses/` | Office responses |
| GET/POST | `.../source-responses/` | Source responses |
| GET/POST | `.../litigation-responses/` | Litigation responses |
| GET/POST | `.../schedule-responses/` | Schedule responses |
| GET/POST | `.../technical-responses/` | Technical responses |
| GET/POST | `.../evaluations/` | Evaluations |
| GET | `.../audit-logs/` | Bid audit logs (read-only) |
| GET | `.../audit-logs/{id}/` | Audit log detail |

---

## Marketplace (`/api/v1/marketplaces/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/marketplaces/categories-with-subcategories/` | Categories with subcategories |
| GET/POST | `/marketplaces/categories/` | Categories |
| GET/POST | `/marketplaces/subcategories/` | Subcategories |
| GET/POST | `/marketplaces/products-services/` | Products / services |
| GET/POST | `/marketplaces/product-images/` | Product images |
| GET/POST | `/marketplaces/prices/` | Price lists |
| GET/POST | `/marketplaces/rfqs/` | RFQs |
| GET/POST | `/marketplaces/rfq-items/` | RFQ items |
| GET/POST | `/marketplaces/quotes/` | Quotes |
| GET/POST | `/marketplaces/quote-items/` | Quote items |
| GET/POST | `/marketplaces/reviews/` | Company reviews |
| GET/POST | `/marketplaces/messages/` | Messages |
| GET/POST | `/marketplaces/notifications/` | Marketplace notifications |

---

## Legal (`/api/v1/legal-documents/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/legal-documents/power-of-attorney/` | Power of attorney CRUD |
| GET/PUT/PATCH/DELETE | `/legal-documents/power-of-attorney/{id}/` | Power of attorney detail |

---

## Automation (`/api/v1/automation/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/automation/power-of-attorney/` | Power of attorney (automation) |
| GET/PUT/PATCH/DELETE | `/automation/power-of-attorney/{uuid}/` | Detail |
| GET/POST | `/automation/tender-securing-declaration/` | Tender securing declaration |
| GET/PUT/PATCH/DELETE | `/automation/tender-securing-declaration/{uuid}/` | Detail |
| GET/POST | `/automation/litigation-history/` | Litigation history |
| GET/PUT/PATCH/DELETE | `/automation/litigation-history/{uuid}/` | Detail |
| GET/POST | `/automation/cover-letter/` | Cover letter |
| GET/PUT/PATCH/DELETE | `/automation/cover-letter/{uuid}/` | Detail |

---

## Payments (`/api/v1/payments/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET/POST | `/payments/` | Yes | List / create payments (user-scoped) |
| GET/PUT/PATCH/DELETE | `/payments/{id}/` | Yes | Payment CRUD |

---

## Notifications & Analytics

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/notifications/` | No | Placeholder — app status |
| GET | `/analytics/` | No | Placeholder — app status |

---

## Document expiry webhook

**POST** `/api/v1/accounts/webhooks/documents/expiry/`

Body (JSON):

- `document_id` (optional) — UUID of company document to process; if expiring soon, owner gets email.
- `event` (optional) — `"check_expiry"` returns up to 100 documents expiring in the next 30 days.

Response:

```json
{
  "detail": "Webhook processed.",
  "processed_count": 1,
  "processed_ids": ["uuid", ...]
}
```

---

## Errors

- **401 Unauthorized** — Missing or invalid JWT.
- **403 Forbidden** — Valid user but not allowed (e.g. not company owner).
- **404 Not Found** — Resource or URL not found.
- **400 Bad Request** — Validation errors; body usually includes field-level errors.

---

## Filtering

Where supported (e.g. tenders, subcategories), use query parameters such as:

- Tenders: `?status=published`, `?category=<slug>`, `?subcategory=<slug>`
- Subcategories: `?category=<slug>`

Filter backends: `django_filters.rest_framework.DjangoFilterBackend` is enabled; filter fields depend on each ViewSet.
