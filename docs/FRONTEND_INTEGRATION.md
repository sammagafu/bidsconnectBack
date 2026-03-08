# Frontend Integration Guide

This guide explains **how to consume the BidsConnect API from the frontend** and **what data to pass** for each request.

> **Note:** This project does not include AI/ML features. If you meant “API” (not “AI”), this document covers consuming the REST API from your frontend (React, Vue, etc.).

---

## 1. Base URL and CORS

- **Base URL:** `https://your-domain/api/v1/` (e.g. `http://localhost:8000/api/v1/` or `https://bidsconnect.co.tz/api/v1/`)
- **CORS:** The backend allows origins listed in `CORS_ALLOWED_ORIGINS` (e.g. `http://localhost:5173`, `https://bidsconnect.co.tz`). Use credentials if you send cookies: `credentials: 'include'`.

---

## 2. Authentication flow

### Step 1: Register (optional)

```http
POST /api/v1/accounts/users/
Content-Type: application/json
```

**Body (JSON):**

```json
{
  "email": "user@example.com",
  "password": "YourSecurePassword123!",
  "phone_number": "255712345678",
  "first_name": "John",
  "last_name": "Doe",
  "invitation_token": ""
}
```

- `invitation_token`: optional; if present and valid, the new user is added to the company and the invitation is marked accepted.
- `password`: must pass Django’s password validators (length, common passwords, etc.).

**Response:** User object (id, email, etc.) or 400 with validation errors.

---

### Step 2: Login (get JWT)

```http
POST /api/v1/accounts/jwt/create/
Content-Type: application/json
```

**Body (JSON):**

```json
{
  "email": "user@example.com",
  "password": "YourSecurePassword123!"
}
```

**Response:**

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

Store `access` (e.g. in memory or secure storage). Use it in the `Authorization` header for all protected requests.

---

### Step 3: Attach token to requests

For every authenticated request:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

Example (fetch):

```javascript
const token = getStoredAccessToken();
const res = await fetch(`${API_BASE}/accounts/companies/`, {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  credentials: 'include',
});
```

---

### Step 4: Refresh token (when access expires)

Access tokens expire (e.g. 5 minutes). When you get **401 Unauthorized**, call:

```http
POST /api/v1/accounts/jwt/refresh/
Content-Type: application/json
```

**Body (JSON):**

```json
{
  "refresh": "<your_refresh_token>"
}
```

**Response:**

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

Replace the stored access token with the new one and retry the failed request.

---

## 3. Example: API client (fetch)

```javascript
const API_BASE = 'http://localhost:8000/api/v1';

function getAccessToken() {
  return localStorage.getItem('access'); // or your store
}

async function api(endpoint, options = {}) {
  const token = getAccessToken();
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    credentials: 'include',
  });

  if (res.status === 401) {
    // Optionally: refresh token and retry
    const refreshed = await refreshToken();
    if (refreshed) return api(endpoint, options);
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw { status: res.status, ...data };
  return data;
}

// Login and store tokens
async function login(email, password) {
  const data = await api('/accounts/jwt/create/', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  localStorage.setItem('access', data.access);
  localStorage.setItem('refresh', data.refresh);
  return data;
}

// Example: list companies
const companies = await api('/accounts/companies/');
```

---

## 4. Example: API client (axios)

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    if (err.response?.status === 401) {
      const refresh = localStorage.getItem('refresh');
      if (refresh) {
        const { data } = await axios.post(
          'http://localhost:8000/api/v1/accounts/jwt/refresh/',
          { refresh },
          { headers: { 'Content-Type': 'application/json' } }
        );
        localStorage.setItem('access', data.access);
        err.config.headers.Authorization = `Bearer ${data.access}`;
        return api.request(err.config);
      }
    }
    return Promise.reject(err);
  }
);

// Usage
const { data } = await api.get('/accounts/companies/');
await api.post('/accounts/companies/', { name: 'My Company', ... });
```

---

## 5. What data to pass: key endpoints

### Register user

| Field | Type | Required | Notes |
|------|------|----------|-------|
| `email` | string | Yes | Valid email |
| `password` | string | Yes | Must pass validators |
| `phone_number` | string | Yes | e.g. 10–20 chars |
| `first_name` | string | No | |
| `last_name` | string | No | |
| `invitation_token` | string | No | If accepting an invite |

---

### Login (JWT create)

| Field | Type | Required |
|------|------|----------|
| `email` | string | Yes |
| `password` | string | Yes |

---

### Create company

```http
POST /api/v1/accounts/companies/
Authorization: Bearer <token>
Content-Type: application/json
```

**Body (JSON):** You can send a subset; backend sets `owner` from the current user.

```json
{
  "name": "Acme Ltd",
  "description": "We build things.",
  "industry": "Construction",
  "website": "https://acme.co.tz",
  "tax_id": "123-456",
  "registration_number": "REG-001",
  "founded_date": "2020-01-15",
  "country": "Tanzania",
  "key_activities": "Construction, civil works",
  "naics_code": "236220",
  "employee_count": 50,
  "parent_company": null
}
```

- `name` is required and must be unique.
- `logo`: use **multipart/form-data** if uploading a file (same URL).

---

### Create company document

```http
POST /api/v1/accounts/companies/{company_pk}/documents/
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Form fields:**

| Field | Type | Required | Notes |
|------|------|----------|-------|
| `name` | string | Yes | |
| `document_type` | string | Yes | One of: `Business License`, `BRELA`, `TIN`, `Tax Clearance`, `Bank Statement` |
| `category` | string | No | e.g. `legal`, `financial`, `operational`, `hr`, `marketing`, `other` |
| `file` | file | Yes | Allowed: `.pdf`, `.doc`, `.docx`; max size from backend |
| `expiry_date` | string | No | ISO date `YYYY-MM-DD` |
| `is_verified` | boolean | No | Default false |

**Example (FormData in JS):**

```javascript
const form = new FormData();
form.append('name', 'Tax Clearance 2024');
form.append('document_type', 'Tax Clearance');
form.append('category', 'financial');
form.append('file', fileInput.files[0]);
form.append('expiry_date', '2025-12-31');

await fetch(`${API_BASE}/accounts/companies/${companyId}/documents/`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: form,
});
```

---

### Create tender

```http
POST /api/v1/tenders/tenders/
Authorization: Bearer <token>
Content-Type: application/json
```

**Body (JSON):** Use IDs for relations; nested arrays are optional.

```json
{
  "title": "Supply of Office Equipment",
  "reference_number": "TND-2024-001",
  "description": "Full description here.",
  "address": "P.O. Box 123, Dar es Salaam",
  "phone_number": "+255 22 123 4567",
  "email": "tender@agency.go.tz",
  "category_id": 1,
  "subcategory_id": 2,
  "procurement_process_id": 1,
  "agency_id": 1,
  "tender_type_country": "National",
  "tender_type_sector": "Goods",
  "currency": "TZS",
  "tender_fees": "100000",
  "source_of_funds": "Government",
  "publication_date": "2024-06-01",
  "submission_deadline": "2024-07-15T17:00:00Z",
  "validity_period_days": 90,
  "completion_period_days": 60,
  "allow_alternative_delivery": false,
  "litigation_history_start": "2022-01-01",
  "litigation_history_end": "2024-01-01",
  "tender_document": null,
  "tender_securing_type": "Tender Security",
  "tender_security_percentage": 5,
  "tender_security_amount": null,
  "tender_security_currency": "TZS",
  "required_documents": [
    { "name": "Tax Certificate", "document_type": "Tax Clearance", "is_required": true }
  ],
  "financial_requirements": [],
  "turnover_requirements": [],
  "experience_requirements": [],
  "personnel_requirements": [],
  "schedule_items": [],
  "technical_specifications": []
}
```

- **Bid Security:** Two types — (1) `Tender Security` = amount or percentage; (2) `Tender Securing Declaration` = document. If `tender_securing_type` is `"Tender Security"`, provide either `tender_security_percentage` or `tender_security_amount`.
- **Tender contact:** Optional `address`, `phone_number`, `email`. **Participation fee:** `tender_fees` with `currency` (TZS or USD).
- For file uploads (e.g. tender document), use **multipart/form-data** and the same endpoint if the API supports it.

---

### Create bid

```http
POST /api/v1/bids/
Authorization: Bearer <token>
Content-Type: application/json
```

**Body (JSON):**

```json
{
  "tender_id": 1,
  "company_id": "uuid-of-your-company",
  "total_price": "5000000",
  "currency": "TZS",
  "proposed_completion_days": 45,
  "validity_complied": true,
  "completion_complied": true,
  "jv_partner": null,
  "jv_percentage": null,
  "bids_documents": [
    {
      "tender_document": 1,
      "company_document": 2,
      "description": "Attached tax clearance"
    }
  ],
  "bids_financial_responses": [
    {
      "financial_requirement": 1,
      "financial_statement": 3,
      "actual_value": "10000000",
      "jv_contribution": null,
      "notes": ""
    }
  ],
  "bids_turnover_responses": [],
  "bids_experience_responses": [],
  "bids_personnel_responses": [],
  "bids_office_responses": [],
  "bids_source_responses": [],
  "bids_litigation_responses": [],
  "bids_schedule_responses": [],
  "bids_technical_responses": []
}
```

- `tender_id`: ID of the tender.
- `company_id`: UUID of the company (must be one the user can bid for).
- At least one of `file`, `company_document`, or `company_certification` per document response if the API requires it (see BidDocumentSerializer).
- `jv_contribution`: if provided, must be between 0 and 100.

---

### Submit bid

```http
POST /api/v1/bids/{bid_id}/submit/
Authorization: Bearer <token>
Content-Type: application/json
```

**Body:** Empty `{}` or no body. The backend validates and changes status to submitted.

---

### Send company invitation

```http
POST /api/v1/accounts/companies/{company_pk}/invitations/
Authorization: Bearer <token>
Content-Type: application/json
```

**Body (JSON):**

```json
{
  "invited_email": "newuser@example.com",
  "role": "user"
}
```

- `role`: e.g. `owner`, `admin`, `manager`, `user`.

---

### Document expiry webhook (no auth)

```http
POST /api/v1/accounts/webhooks/documents/expiry/
Content-Type: application/json
```

**Body (JSON) – one or both:**

```json
{
  "document_id": "uuid-of-company-document",
  "event": "check_expiry"
}
```

- `document_id`: optional; process one document (and send email if expiring soon).
- `event`: optional; use `"check_expiry"` to list documents expiring in the next 30 days (up to 100).

**Response:**

```json
{
  "detail": "Webhook processed.",
  "processed_count": 1,
  "processed_ids": ["uuid1", "uuid2"]
}
```

---

### List/filter tenders

```http
GET /api/v1/tenders/tenders/?status=published&category=construction
Authorization: Bearer <token>
```

Query params (all optional): `status`, `category` (slug), `subcategory` (slug).

---

### Get current user (me)

```http
GET /api/v1/accounts/users/me/
Authorization: Bearer <token>
```

Returns user with nested companies (from CustomUserDetailSerializer).

---

## 6. File uploads summary

- **Company documents:** `POST /api/v1/accounts/companies/{company_pk}/documents/` with **multipart/form-data** (fields: `name`, `document_type`, `category`, `file`, `expiry_date`, `is_verified`).
- **Company logo:** use **multipart/form-data** on company create/update if the API accepts it.
- **Bid documents:** when the API expects a file, send **multipart/form-data** to the corresponding bid-document endpoint (e.g. `file` or `proof` in nested payloads; check serializer for exact field names).

Do **not** set `Content-Type: application/json` for requests that send `FormData`; the browser will set the boundary automatically.

---

## 7. Errors

- **400 Bad Request:** Validation errors; response body is an object, often `{ "field_name": ["error message"] }` or `{ "detail": "message" }`.
- **401 Unauthorized:** Missing or invalid token; refresh the token and retry.
- **403 Forbidden:** Authenticated but not allowed (e.g. not company owner).
- **404 Not Found:** Wrong URL or resource does not exist.
- **500 Server Error:** Backend error; check response body and logs.

Always check `res.ok` / `response.status` and parse the JSON body for error details before showing a message to the user.

---

For a full list of endpoints, see [API.md](API.md). For system flows, see [SYSTEM_FLOW.md](SYSTEM_FLOW.md).
