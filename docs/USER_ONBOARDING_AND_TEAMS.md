# User Onboarding, Company Members, Roles & Team Features

This document describes how users join BidsConnect, create or join companies, manage members and roles, and use **company tasks** and **tender conversations**.

---

## 1. User onboarding

### 1.1 Register

**Endpoint:** `POST /api/v1/accounts/users/`  
**Auth:** None (public registration).

**Request body (JSON):**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "phone_number": "255712345678",
  "first_name": "Jane",
  "last_name": "Doe",
  "invitation_token": ""
}
```

- **invitation_token** (optional): If the user was invited to a company, pass the token from the invitation email. On success, they are added to that company with the invited role and the invitation is marked accepted.
- **password**: Must satisfy Django validators (length, common-passwords check, etc.).

**Response:** User object (id, email, etc.) or 400 with validation errors.

### 1.2 Login (JWT)

**Endpoint:** `POST /api/v1/accounts/jwt/create/`  
**Auth:** None.

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

Use the **access** token in the `Authorization` header for all protected requests:
```http
Authorization: Bearer <access_token>
```

### 1.3 Onboarding flow (summary)

1. User **registers** (or is invited and registers with `invitation_token`).
2. User **logs in** and receives JWT.
3. User **creates a company** (`POST /accounts/companies/`) and becomes the **owner**.
4. Optionally, user **invites** other users to the company (see below) or **joins** via an invitation link.

---

## 2. Adding company members

Members are added in two ways: **invitation by email** (recommended) or **direct add** (existing user by ID).

### 2.1 Invite by email (recommended)

**Endpoint:** `POST /api/v1/accounts/companies/{company_pk}/invitations/`  
**Auth:** Required (company **owner** or **admin**).

**Request body:**
```json
{
  "invited_email": "newmember@example.com",
  "role": "user"
}
```

**Roles:** `owner` | `admin` | `manager` | `user` (see [Roles](#3-roles)).

- The system sends an email to **invited_email** with a link to accept the invitation.
- The link points to: `{SITE_URL}/.../invitations/accept/{token}/` (frontend can redirect to this or call the accept API with the token from the URL).

**Accepting an invitation**

**Endpoint:** `POST /api/v1/accounts/invitations/accept/{token}/`  
**Auth:** Required (logged-in user whose email matches the invitation).

- The logged-in user's email **must** match the invitation's **invited_email**; otherwise the API returns **403** with `{"detail": "This invitation was sent to a different email address."}`.
- If the company has already reached **MAX_COMPANY_USERS**, the API returns **400** with `{"detail": "Company user limit reached."}`.
- On success, a **CompanyUser** is created with the invited **role** and the invitation is marked accepted.
- Response: `{"detail": "Successfully joined {company name}."}`

**List / manage invitations**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/accounts/companies/{company_pk}/invitations/` | List invitations (pending, accepted) |
| GET/PUT/PATCH/DELETE | `.../invitations/{id}/` | Retrieve or update invitation (e.g. cancel) |

### 2.2 Direct add (existing user by ID)

**Endpoint:** `POST /api/v1/accounts/companies/{company_pk}/users/`  
**Auth:** Required (company **owner** or **admin**).

**Request body:**
```json
{
  "user": 123,
  "role": "manager"
}
```

- **user**: ID of an existing user (from `/accounts/users/` or registration).
- **role**: Same as above.

**Limits:** Total company users are capped (see `MAX_COMPANY_USERS` in `accounts/constants.py`; default 5). Invitations count toward the limit once accepted.

---

## 3. Roles

Roles are stored on **CompanyUser** and optionally on **CompanyInvitation** (for the role the user will get when they accept).

| Role     | Description | Typical permissions |
|----------|-------------|----------------------|
| **owner**  | Company creator; exactly one per company. | Full control; delete company; add/remove members; assign roles (with constraints). |
| **admin**  | Company administrator. | Add/remove members; invite; assign roles (except demoting owner); manage company resources (documents, offices, etc.). |
| **manager**| Team lead. | Often same as **user** in the API; can be used for future “task assigner” or approval flows. |
| **user**   | Standard member. | Access company data; create/edit bids for the company; participate in tender conversations and tasks assigned to them. |

**Assigning / changing roles**

- **Create:** Set `role` in `POST .../invitations/` or `POST .../users/`.
- **Update:** `PATCH /accounts/companies/{company_pk}/users/{id}/` with `{"role": "admin"}`.
- **Rules:** Only **owner** or **admin** can change roles. The **owner** role should not be removed from the last owner (enforced in logic/tests).

---

## 4. Company task handling and assigning

Company **tasks** let owners/admins assign work to members, optionally linked to a **tender** or **bid**.

### 4.1 Model (summary)

- **CompanyTask**: company, title, description, assignee (user), status, due_date, optional tender, optional bid, created_by, created_at, updated_at.
- **Status:** `todo` | `in_progress` | `done` | `cancelled`.

### 4.2 API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/accounts/companies/{company_pk}/tasks/` | List tasks for the company. Filter: `?status=`, `?assignee=`, `?tender=`, `?bid=`. |
| POST | `/accounts/companies/{company_pk}/tasks/` | Create task (title, optional description, assignee, tender, bid, due_date, status). |
| GET | `.../tasks/{id}/` | Task detail. |
| PUT/PATCH | `.../tasks/{id}/` | Update task. Owner/admin: any field. Assignee: only `status` and `due_date`. |
| DELETE | `.../tasks/{id}/` | Delete task (owner/admin only). |

**Permissions:** Company members can list/retrieve. Only **owner** or **admin** can create and delete. **Assignee** can PATCH only `status` and `due_date`.

---

## 5. Team messaging and conversation on tender

**Tender conversations** are one thread per **company** per **tender**. All company members who can access the tender can see and post messages (team chat for that tender).

### 5.1 Model (summary)

- **TenderConversation**: company (FK), tender (FK). Unique together (company, tender).
- **TenderMessage**: conversation (FK), sender (FK User), content (text), created_at.

### 5.2 API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tenders/conversations/?tender=<slug>` | List your company’s conversation(s) for the tender. |
| POST | `/tenders/conversations/` | Body: `{"tender_slug": "<tender_slug>"}`. Get or create your company’s conversation for this tender. |
| GET | `/tenders/conversations/{id}/` | Conversation detail. |
| GET | `/tenders/conversations/{id}/messages/` | List messages in the conversation. |
| POST | `/tenders/conversations/{id}/messages/` | Body: `{"content": "..."}`. Post a message (sender = current user). |

**Permissions:** Authenticated; user must be a member of the conversation’s company. Only that company’s members can list/post messages.

---

## 6. Quick reference

| Flow | Main endpoints |
|------|----------------|
| Register | `POST /accounts/users/` |
| Login | `POST /accounts/jwt/create/` |
| Create company | `POST /accounts/companies/` |
| Invite member | `POST /accounts/companies/{id}/invitations/` with `invited_email` + `role` |
| Accept invite | `POST /accounts/invitations/accept/{token}/` |
| List/update members | `GET/PATCH /accounts/companies/{id}/users/` |
| Assign role | `PATCH .../users/{id}/` with `role` |
| Company tasks | `GET/POST /accounts/companies/{id}/tasks/`, `PATCH .../tasks/{id}/` |
| Tender conversation | `GET/POST /api/v1/tenders/conversations/` (query `?tender=<slug>`, POST body `{"tender_slug": "<slug>"}`), `GET/POST .../conversations/<id>/messages/` |

For full API details see [API.md](API.md) and [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md).
