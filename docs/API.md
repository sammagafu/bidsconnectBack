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
| GET/POST | `/accounts/companies/{company_pk}/tasks/` | Company tasks (assign to members; filter by status, assignee, tender, bid) |
| GET/PUT/PATCH/DELETE | `/accounts/companies/{company_pk}/tasks/{id}/` | Task CRUD |

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
| POST | `/accounts/invitations/accept/{token}/` | Yes | Accept invitation (see [Invitation accept](#invitation-accept) below) |
| POST | `/accounts/webhooks/documents/expiry/` | Webhook secret | Document expiry webhook (body: `document_id`, `event`). When `DOCUMENT_EXPIRY_WEBHOOK_SECRET` is set, send header `X-Webhook-Secret: <secret>` or `Authorization: Bearer <secret>`; otherwise **401** is returned. See [Document expiry webhook](#document-expiry-webhook). |

### Invitation accept

**POST** `/api/v1/accounts/invitations/accept/<token>/`  
**Auth:** Required (logged-in user).

- The logged-in user’s email **must** match the invitation’s `invited_email` (case-insensitive). If not, the API returns **403** with `{"detail": "This invitation was sent to a different email address."}`.
- If the company has already reached the maximum number of members (`MAX_COMPANY_USERS`), the API returns **400** with `{"detail": "Company user limit reached."}`.
- On success, a `CompanyUser` is created with the invited role and the invitation is marked accepted. Response: `{"detail": "Successfully joined {company name}."}`

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

**Create permission:** Only **staff** or users who are **owner** or **admin** of at least one company can create or update tenders. Other authenticated users get 403 on POST/PUT/PATCH.

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
| GET | `/tenders/tender-notifications/` | List tender notifications for the current user (via subscription). Each has `is_read`. |
| GET/PUT/PATCH | `/tenders/tender-notifications/{id}/` | Retrieve or update (e.g. PATCH `{"is_read": true}` to mark as read). User sees only their own. |
| GET | `/tenders/tender-status-history/` | Tender status history (read-only) |
| GET/POST | `/tenders/conversations/` | List/create tender conversation (team chat). Query: `?tender=<slug>`. Body: `{"tender_slug": "..."}` |
| GET | `/tenders/conversations/{id}/` | Conversation detail |
| GET/POST | `/tenders/conversations/{id}/messages/` | List/post messages in conversation |
| GET | `/tenders/pricing/` | List platform pricing (tender document fee, tender summary one-time). Auth required. |
| GET | `/tenders/pricing/{fee_type}/` | Retrieve one pricing config (e.g. `tender_document`, `tender_summary_one_time`). |
| PUT/PATCH | `/tenders/pricing/{fee_type}/` | Update pricing (staff only). Body: `amount`, `currency`, `cap`, `is_active`. |

---

## Bids (`/api/v1/bids/`)

**List scoping:** Non-staff users see only bids for **companies they belong to**. Staff see all bids. Optional filters: `?tender=`, `?status=`, `?company_id=` (further narrows to that company; user must be a member).

**Create:** `company_id` must be a company the user is a member of; otherwise validation returns 400. Only one bid per (tender, company); duplicate returns 400 with `{"detail": "Your company already has a bid for this tender."}`.

**Permissions:** Any **company member** of the bid’s company (or staff) can create, read, and update draft bids and nested resources (documents, responses). Submit is allowed for company members; evaluator actions remain staff-only.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/bids/` | List / create bids |
| GET/PUT/PATCH/DELETE | `/bids/{id}/` | Bid CRUD |
| POST | `/bids/{id}/submit/` | Submit bid |
| GET | `/bids/{id}/validate-submit/` | Pre-submit validation: returns `is_ready` and `errors` list |

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
| GET | `/notifications/` | Yes | Unified in-app notifications (tender + marketplace). Query: `?type=`, `?is_read=`, `?page=`, `?page_size=` |
| PATCH | `/notifications/{id}/` | Yes | Mark marketplace notification as read (body: `{"is_read": true}`). For **tender** notifications, use `PATCH /tenders/tender-notifications/{id}/` with `{"is_read": true}`. |
| GET | `/notifications/ping/` | No | App status |
| GET | `/analytics/` | Yes | Comprehensive dashboard: tenders, bids, marketplace, accounts, payments. Query: `?scope=platform\|company`, `?company_id=` (required if scope=company), `?period=30d` |
| GET | `/analytics/ping/` | No | App status |

**Analytics response (GET /analytics/):** `stats` contains `tenders` (total, by_status, optional recent_*_30d), `bids` (total, by_status, optional recent_submitted_30d), `marketplace` (products, rfq, quotes, reviews), `accounts` (companies_total/users_total or company_members), `payments` (total, by_status).

**Company scope:** When `scope=company` and `company_id` is provided, the user **must** be a member of that company; otherwise the API returns **403** with `{"detail": "You do not have access to this company."}`.

---

## Document expiry webhook

**POST** `/api/v1/accounts/webhooks/documents/expiry/`

**Authentication:** When the setting `DOCUMENT_EXPIRY_WEBHOOK_SECRET` is set (e.g. in production), the request **must** include one of:

- Header: `X-Webhook-Secret: <secret>`
- Header: `Authorization: Bearer <secret>`

If the secret is set and the header is missing or does not match, the API returns **401** with `{"detail": "Invalid or missing webhook secret."}`. When the secret is not set (e.g. dev), no header is required.

**Body (JSON):**

- `document_id` (optional) — UUID of company document to process; if expiring soon, owner gets email.
- `event` (optional) — `"check_expiry"` processes up to 100 documents expiring in the next 30 days.

**Response:**

```json
{
  "detail": "Webhook processed.",
  "processed_count": 1,
  "processed_ids": ["uuid", ...]
}
```

---

## Errors

- **401 Unauthorized** — Missing or invalid JWT; or invalid/missing webhook secret (document expiry webhook).
- **403 Forbidden** — Valid user but not allowed (e.g. not company owner, or invitation sent to another email).
- **404 Not Found** — Resource or URL not found.
- **400 Bad Request** — Validation errors; body usually includes field-level errors.

**Error response convention:** Use `detail` for a single message (e.g. `{"detail": "..."}`). Use `errors` for a list of validation messages when applicable (e.g. bid submit validation: `{"detail": "...", "errors": ["...", "..."]}`). Avoid mixing `error` and `detail` for the same case; prefer `detail`.

---

## Filtering

Where supported (e.g. tenders, subcategories), use query parameters such as:

- Tenders: `?status=published`, `?category=<slug>`, `?subcategory=<slug>`
- Subcategories: `?category=<slug>`

Filter backends: `django_filters.rest_framework.DjangoFilterBackend` is enabled; filter fields depend on each ViewSet.
