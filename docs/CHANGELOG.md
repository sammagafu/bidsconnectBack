## Changelog

### 2026-03-08 – Backend hardening & docs alignment

- **Invitation accept security**
  - `POST /api/v1/accounts/invitations/accept/{token}/` now enforces:
    - The logged-in user’s email must match the invitation’s `invited_email` (case-insensitive); otherwise returns **403** with `{"detail": "This invitation was sent to a different email address."}`.
    - Company member limit is respected; when `MAX_COMPANY_USERS` is reached, returns **400** with `{"detail": "Company user limit reached."}`.
  - Behavior documented in `docs/API.md` and `docs/USER_ONBOARDING_AND_TEAMS.md`.

- **Document expiry webhook authentication**
  - `POST /api/v1/accounts/webhooks/documents/expiry/` now supports an optional shared secret:
    - When `DOCUMENT_EXPIRY_WEBHOOK_SECRET` is set, the caller must send either `X-Webhook-Secret: <secret>` or `Authorization: Bearer <secret>`.
    - Invalid or missing secret returns **401** with `{"detail": "Invalid or missing webhook secret."}`.
  - Setting documented in `bidsconnect/settings.py`, `.env.example`, `docs/API.md`, and `docs/SYSTEM_FLOW.md`.

- **Tender creation permissions**
  - Only staff or users who are `owner` / `admin` of at least one company can create or update tenders.
  - Enforced via `CanCreateTender` in `tenders/views.py`, documented in `docs/API.md` and `docs/BIDS_CONNECT_SPEC.md`.

- **Bid scoping & duplicate prevention**
  - `/api/v1/bids/`:
    - Non-staff users now only see bids for companies they belong to; staff still see all bids.
    - `company_id` is restricted to companies where the user is a member; attempting to create a bid for another company returns **400**.
  - Creating a second bid for the same `(tender, company)` returns **400** with `{"detail": "Your company already has a bid for this tender."}` instead of a generic DB error.
  - Behavior documented in `docs/API.md` and `docs/FRONTEND_INTEGRATION.md`.

- **Bid submit validation response**
  - `POST /api/v1/bids/{id}/submit/` now returns on validation failure:
    - **400** with `{"detail": "<summary>", "errors": ["error1", "error2", ...]}`.
  - Frontend integration guide updated to show how to surface `errors` to users and how to use `GET /api/v1/bids/{id}/validate-submit/` for pre-submit checks.

- **Tender notifications read state**
  - `TenderNotification` model gained an `is_read` flag (default `false`) with migration `0002_tendernotification_is_read`.
  - API:
    - `GET /api/v1/tenders/tender-notifications/` lists notifications for the current user (via subscriptions).
    - `PATCH /api/v1/tenders/tender-notifications/{id}/` with `{"is_read": true}` marks a notification as read.
  - Unified notifications endpoint reflects `is_read` for tender notifications, documented in `docs/API.md` and `docs/FRONTEND_INTEGRATION.md`.

- **Analytics company scope authorization**
  - `GET /api/v1/analytics/?scope=company&company_id=...` now requires the user to be a member of that company.
  - Non-members receive **403** with `{"detail": "You do not have access to this company."}`.
  - Documented in `docs/API.md`.

- **Email notifications UI improvements (backend-driven)**
  - Tender notification (`tender_notification.html`) and digest (`tender_digest.html`) templates updated:
    - Consistent BidsConnect branding and more readable layout.
    - `SITE_URL` used to generate “View Tender” / “View All Tenders” buttons and per-tender links in digests.
  - `SITE_URL` usage clarified in `.env.example` and `README.md`.

- **Tests**
  - New backend tests added for:
    - Invitation accept email/limit logic.
    - Document expiry webhook secret handling.
    - Bid list scoping and company restrictions.
  - README updated with commands to run these tests.

