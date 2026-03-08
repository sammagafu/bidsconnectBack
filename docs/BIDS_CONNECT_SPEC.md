# BidsConnect — Product & Tender Specification

This document captures product requirements, user journeys, and tender/bid rules for BidsConnect.

---

## 1. Problems & Features (Backlog)

| # | Item | Notes |
|---|------|--------|
| 1 | **Tender document fee** | Non-members / unregistered users pay **3,000 TZS** to get tender document. |
| 2 | **Tender showcasing** | Organization **rating after tender completion** (post-award feedback). |
| 3 | **Power of attorney & document certification** | **Lawyer part** of application (certification, verification). |
| 4 | **Teamwork** | **Assignment of tasks**, **progress monitoring**, and **chatbox**. **Internal design:** Tasks can be assigned to company users per tender/bid; progress tracked (e.g. completion % or checklist); chatbox per tender/bid or per company for real-time collaboration. Implementation TBD (e.g. WebSockets or polling, task model linked to bid/tender). |
| 5 | **Tender summary and updates** | **Premium** = free; **one-time** = **50,000 TZS**. |
| 6 | **Reminders for expiring documents** | User submits **expiry date** for documents; system sends reminders (existing: `DOCUMENT_EXPIRY_NOTIFICATION_DAYS` in accounts). |
| 7 | **Tender / procurement advertise** | **Company / manufacturer** linked with **procurement** with **verification**. |

---

## 2. Tender Aspect — Roles & Permissions

### Admin

- **Post, Delete, Update** tenders (on behalf of clients / organizations).
- **What is posted:** Date of issue, deadline, documents (similar to Nest).

### Organizations

- **Organizations** can post their own tenders (company admins / agency admins).

### Tenders visibility

- Tenders can be **opened** (created/edited) by **admin** and **company admins**.

---

## 3. Normal User Journey

```text
Login → See tenders → Request to apply → Approval → Tender submission → Finalized
```

### Tender submission steps (for bidder)

1. **Get a summary** for the tender.
2. **Sign** (e.g. agreement / declaration).
3. **See progress** (track submission status).

---

## 4. Bid Security (formerly “Bid bond”)

**Two types:**

1. **Tender Security** — amount **or** percentage (stored: `tender_security_amount`, `tender_security_percentage`, `tender_security_currency`).
2. **Tender Securing Declaration** — provided as a **document** (no cash amount).

Model: `Tender.tender_securing_type`, `tender_security_percentage`, `tender_security_amount`, `tender_security_currency`.

---

## 5. Bids — Status & Terminology

- **Submission** → status **submitted** (no “review” as a status).
- **Evaluation** → use **under_evaluation** (not “review”).
- **Audit** → use **BidAuditLog** (audit trail); “review” in UI/API should read as “audit” where appropriate.

Status flow: **draft → submitted → under_evaluation → accepted / rejected**.

---

## 6. Tenders — Data & Rules

- **Title**: Keep **title** in model; use **description** for full details (do not remove title).
- **Tender contact**: Use **address**, **phone number**, **email** (on `Tender` and/or agency).
- **Categories**: Tender **category** and **subcategory** (type and subcategory).
- **Tender participation fee**: In **TZS** or **USD** (field: `tender_fees`, `currency`).

---

## 7. Process Flowcharts & Workflows

- **Process flowcharts**: See [SYSTEM_FLOW.md](SYSTEM_FLOW.md) for tender lifecycle, bid lifecycle, and data flow.
- **Tender workflow**: Draft → Pending → Published → Evaluation → Awarded (see state diagram in SYSTEM_FLOW).
- **User journey map**: Login → See tenders → Request to apply → Approval → Tender submission (summary, sign, progress) → Finalized.

---

## 8. Constants (Implementation)

- **Tender document fee (non-member):** `tenders.constants.TENDER_DOCUMENT_FEE_NON_MEMBER_TZS` = 3,000 TZS.
- **Tender summary:** Premium free; one-time fee = `TENDER_SUMMARY_ONE_TIME_FEE_TZS` = 50,000 TZS.

See [API.md](API.md) for endpoints and [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md) for integration details.
