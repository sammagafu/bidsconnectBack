# BidsConnect System Flow

This document describes the main flows in BidsConnect: user and company setup, tender lifecycle, bid lifecycle, and how data moves between modules.

---

## 1. High-level system overview

```mermaid
flowchart TB
    subgraph Client
        FE[Frontend / Web App]
    end

    subgraph API["BidsConnect API (Django REST)"]
        AUTH[Auth: JWT / Djoser]
        ACCOUNTS[Accounts]
        TENDERS[Tenders]
        BIDS[Bids]
        MKT[Marketplace]
        LEGAL[Legal]
        AUTO[Automation]
        PAY[Payments]
    end

    subgraph Data
        DB[(Database)]
        MEDIA[Media / Static]
    end

    FE --> AUTH
    FE --> ACCOUNTS
    FE --> TENDERS
    FE --> BIDS
    FE --> MKT
    FE --> LEGAL
    FE --> AUTO
    FE --> PAY

    AUTH --> DB
    ACCOUNTS --> DB
    TENDERS --> DB
    BIDS --> DB
    MKT --> DB
    LEGAL --> DB
    AUTO --> DB
    PAY --> DB

    ACCOUNTS --> MEDIA
    BIDS --> MEDIA
```

---

## 2. User and company flow

```mermaid
sequenceDiagram
    participant U as User
    participant API as API
    participant DB as Database

    U->>API: POST /accounts/users/ (register)
    API->>DB: Create CustomUser
    API-->>U: User created

    U->>API: POST /accounts/jwt/create/ (login)
    API-->>U: access + refresh tokens

    U->>API: POST /accounts/companies/ (create company)
    API->>DB: Create Company (owner = user)
    API-->>U: Company created

    U->>API: POST .../companies/{id}/invitations/
    API->>DB: Create CompanyInvitation
    API->>API: Send email (accept link)
    API-->>U: Invitation sent

    Note over U,DB: Invitee
    U->>API: POST /accounts/invitations/accept/{token}/
    API->>DB: CompanyUser created, invitation accepted
    API-->>U: Success

    U->>API: POST .../companies/{id}/documents/
    API->>DB: CompanyDocument
    API->>DB: Store file (media)
    API-->>U: Document created
```

**Summary:**

1. User registers → logs in → gets JWT.
2. User creates a company (becomes owner).
3. Owner invites users → invitee accepts → becomes company user.
4. Company users upload documents (and manage offices, certifications, personnel, etc.).

---

## 3. Tender lifecycle flow

```mermaid
stateDiagram-v2
    [*] --> draft: Create tender
    draft --> pending: Submit / prepare
    pending --> published: Publish
    published --> under_evaluation: Close / evaluate
    under_evaluation --> awarded: Award
    awarded --> [*]

    draft --> draft: Edit
    pending --> draft: Edit (if allowed)
```

**Actors:**

- **Publishers** (e.g. agencies / admins): create tenders, set requirements, publish, award.
- **Bidders**: discover tenders, subscribe to categories, receive notifications.

**Flow:**

1. Create tender (draft) → add required documents, financial/experience/personnel requirements, schedule, technical specs.
2. Publish → status becomes published; subscribers (by category/subcategory/procurement process) get notified (email if enabled).
3. After deadline → status can move to under_evaluation.
4. Award → winner recorded; status awarded.

**Reference data:** Categories, subcategories, procurement processes, agencies are managed (often admin) and used when creating/subscribing to tenders.

---

## 4. Bid lifecycle flow

```mermaid
flowchart LR
    A[Draft] --> B[Submit]
    B --> C[Submitted]
    C --> D[Under evaluation]
    D --> E[Accepted / Rejected]

    subgraph Bidder
        A
    end
    subgraph System
        B
        C
        D
        E
    end
```

**Flow:**

1. **Create bid** (draft) — linked to tender and company.
2. **Add responses** — documents, financial, turnover, experience, personnel, office, source, litigation, schedule, technical.
3. **Submit** — `POST /bids/{id}/submit/` → status moves to submitted (validations: deadline, required data).
4. **Evaluation** — evaluators use bid evaluations and audit logs; status can move to under_evaluation, then accepted/rejected.

Bid is always tied to one **tender** and one **company** (and user).

---

## 5. Data flow: Tender → Notification → Bid

```mermaid
flowchart TB
    subgraph Tenders
        T[Tender]
        SUB[TenderSubscription]
        PREF[NotificationPreference]
        TN[TenderNotification]
    end

    subgraph Accounts
        U[User]
        C[Company]
    end

    subgraph Bids
        B[Bid]
    end

    U --> SUB
    T --> SUB
    U --> PREF
    T --> TN
    SUB --> TN
    T --> B
    C --> B

    T -- "published" --> TN
    PREF -- "email_notifications" --> TN
```

- **TenderSubscription**: user subscribes to categories/subcategories/procurement process; when a tender in that set is published, they can get a **TenderNotification**.
- **NotificationPreference**: per-user (e.g. email on/off, frequency for digest).
- **Bid**: references Tender and Company; created by users belonging to that company.

---

## 6. Marketplace flow (simplified)

```mermaid
flowchart LR
    CAT[Categories / Subcategories] --> PS[Products / Services]
    PS --> RFQ[RFQs]
    RFQ --> QUOTE[Quotes]
    PS --> REVIEW[Reviews]
    PS --> MSG[Messages]
```

- Sellers list **products/services** under **categories/subcategories**, with **price lists** and **product images**.
- Buyers create **RFQs** with **RFQ items**; sellers respond with **quotes** and **quote items**.
- **Reviews** and **messages** are tied to marketplace interactions.

---

## 7. Legal and automation flow

```mermaid
flowchart TB
    subgraph Legal
        POA_L[Power of Attorney]
    end

    subgraph Automation
        POA_A[Power of Attorney]
        TSD[Tender Securing Declaration]
        LH[Litigation History]
        CL[Cover Letter]
    end

    User --> POA_L
    User --> POA_A
    User --> TSD
    User --> LH
    User --> CL
    Tender --> TSD
    Bid --> CL
```

- **Legal** app: power-of-attorney and related legal documents (CRUD via API).
- **Automation** app: generated documents (power of attorney, tender securing declaration, litigation history, cover letter) — create/retrieve/update via API; typically used when preparing bids or complying with tender requirements.

---

## 8. Payments

- **Payment** is a generic model (content type + object id) so it can be linked to any entity (e.g. subscription, bid fee, marketplace order).
- **Flow**: client creates payment via `POST /api/v1/payments/` (user is set from JWT); list/retrieve are scoped to the current user.

---

## 9. Document expiry and webhook

```mermaid
sequenceDiagram
    participant Ext as External System / Cron
    participant API as API
    participant DB as Database
    participant Mail as Email

    Ext->>API: POST /accounts/webhooks/documents/expiry/
    Note over API: body: document_id or event=check_expiry
    API->>DB: Load CompanyDocument(s)
    alt document_id + expiring soon
        API->>Mail: Send email to company owner
    end
    API-->>Ext: processed_count, processed_ids
```

- **Company documents** have `expiry_date`; “expiring soon” is defined in the accounts app (e.g. within N days).
- **Webhook** can process a single document (and optionally send email) or list expiring documents (`event: "check_expiry"`).

---

## 10. Summary

| Flow | Entry | Main APIs | Outcome |
|------|--------|-----------|---------|
| User & company | Register, login | Accounts (users, companies, invitations, documents, …) | Company and team ready to tender/bid |
| Tender | Create draft | Tenders (categories, tenders, requirements, publish) | Published tender |
| Notifications | Subscribe + preferences | Tenders (subscriptions, notification-preferences) | Notifications when tenders published |
| Bid | Create draft | Bids (bids, documents, *-responses, submit) | Submitted bid |
| Evaluation | Evaluator | Bids (evaluations, audit-logs) | Accepted/rejected bid |
| Marketplace | List / browse | Marketplaces (categories, products, RFQs, quotes) | RFQs and quotes |
| Legal / automation | User action | Legal, Automation | Documents for compliance / bidding |
| Payments | User action | Payments | Payment record linked to user (and optional object) |
| Document expiry | Webhook / cron | Accounts webhook | Emails / list of expiring documents |

For detailed endpoint lists and request/response conventions, see [API.md](API.md).
