# BidsConnect — Product Design Feature Suggestions

This document suggests product and UX features that would strengthen BidsConnect as a tender and bidding platform for Tanzania. Suggestions are grouped by impact and effort.

---

## 1. High impact, high value

### 1.1 Guided onboarding and checklist

**Problem:** New users may not know what to do first (create company, add documents, subscribe to categories).

**Suggestion:** Add an onboarding checklist or wizard that appears after registration:

- Step 1: Create or join a company  
- Step 2: Complete company profile (key activities, industry, documents)  
- Step 3: Subscribe to at least one tender category  
- Step 4: (Optional) Add personnel and experience for bidding  

Store progress (e.g. `UserOnboardingProgress` or flags on the user) and allow “Skip for now” with a way to reopen the checklist from the dashboard. API: `GET/PATCH /accounts/users/me/onboarding/` with `{ "step": "company_created", "completed_steps": [...] }`.

**UX:** Progress indicator in the app header or a dedicated “Get started” card on the dashboard until all steps are done.

---

### 1.2 Tender document fee and summary payment flow

**Problem:** Spec defines tender document fee (3,000 TZS non-member) and tender summary (50,000 TZS one-time), but payment is not integrated.

**Suggestion:**

- **Backend:** Extend the Payment model usage: when a user “purchases” a tender document or summary, create a Payment record with the right amount and link it to the tender (content_type + object_id). Add endpoints such as `POST /tenders/tenders/{slug}/purchase-document/` and `.../purchase-summary/` that create a payment and return a reference (and optionally a payment link when M-Pesa or another gateway is integrated).
- **Frontend:** Show “Get document — 3,000 TZS” and “Get summary — 50,000 TZS” with a clear pay-and-download flow. After payment, expose the document or summary (e.g. PDF) or mark the user as “has access” for that tender.

**UX:** Single, clear path: “Pay → Confirm → Access document/summary,” with receipt or confirmation.

---

### 1.3 Bid submission progress and pre-submit validation UI

**Problem:** Bidders need to meet many requirements (documents, financials, personnel, etc.). It’s easy to miss something before submit.

**Suggestion:**

- **Backend:** You already have `GET /bids/{id}/validate-submit/` returning `is_ready` and `errors`. Expose a lightweight “readiness” summary, e.g. “Documents 3/3, Financial 2/2, Personnel 1/1” (counts per requirement type).
- **Frontend:** A “Bid readiness” or “Submission checklist” panel on the bid page that:
  - Calls `validate-submit` (or a summary endpoint) and shows green/red per section.
  - Lists missing items with links to the right tab or form.
  - Disables or warns on “Submit” until `is_ready` is true, and shows the API `errors` list on submit failure.

**UX:** One screen that answers “What’s missing?” and “Am I ready to submit?” before the user clicks Submit.

---

### 1.4 Tender and bid deadline reminders

**Problem:** Users can miss submission deadlines or important tender dates.

**Suggestion:**

- **Backend:** Use notification preferences and a scheduled job (e.g. daily or twice daily) to find:
  - Tenders with submission_deadline in the next 3 days / 1 day for which the user has a draft bid or has subscribed.
  - Draft bids with tender submission_deadline in the next 1 day.
- Send email and/or in-app notifications: “Tender X closes in 24 hours,” “You have a draft bid for Y; deadline in 1 day.”
- Optional: allow users to set “Remind me N days before deadline” in notification preferences.

**UX:** Fewer missed opportunities and fewer abandoned drafts near the deadline.

---

## 2. Medium impact — collaboration and trust

### 2.1 Team tasks and assignment (expand)

**Problem:** You have company tasks and tender conversations; assigning and tracking “who does what” for a bid could be clearer.

**Suggestion:**

- Keep tasks linkable to tender and bid (already in place). Add filters and defaults: “Tasks for this bid,” “My assigned tasks.”
- Optional: simple status (e.g. “Not started / In progress / Done”) and due date on tasks, with optional in-app reminder or digest: “You have 2 tasks due this week.”
- **UX:** From a bid detail page, “Assign task” with assignee and due date; from “My tasks,” see all tasks across tenders/bids.

---

### 2.2 Organization / agency verification and trust

**Problem:** Bidders want to know that tenders are from real, legitimate organizations.

**Suggestion:**

- Add an “Verified” or “Verified organization” badge for agencies/organizations that have been vetted (e.g. by admin or a future verification workflow).
- In tender list and detail, show “Published by: [Agency name] ✓ Verified” when applicable.
- **Backend:** e.g. `AgencyDetails.is_verified` and `verification_date`; only staff can set them. Expose in API and docs.

**UX:** Trust signal on every tender card and detail page.

---

### 2.3 Post-award rating and feedback (tender quality)

**Problem:** Spec mentions “rating after tender completion”; bidders and the market would benefit from knowing how tenders were run.

**Suggestion:**

- After a tender is awarded, allow bidders (e.g. those who submitted a bid) to submit an optional rating (1–5) and short feedback (e.g. “Process was clear,” “Communication was slow”).
- **Backend:** Model `TenderAwardFeedback` (tender, user/company, rating, comment, created_at). Endpoint e.g. `POST /tenders/tenders/{slug}/feedback/` (one per company). Aggregate (average rating, count) on the tender or agency for display.
- **UX:** On awarded tender page: “Rate this tender” and “What others said” (anonymous or attributed by policy).

---

## 3. Lower effort, quick wins

### 3.1 Saved / favourite tenders

**Problem:** Users see many tenders; they may want to shortlist some without subscribing to the whole category.

**Suggestion:** “Save” or “Favourite” per tender: `POST /tenders/tenders/{slug}/save/` (toggle). Store e.g. `TenderSaved` (user, tender). List: `GET /tenders/saved/` or a `?saved=true` filter. **UX:** Heart or bookmark icon on tender cards; “Saved tenders” in the menu.

---

### 3.2 Tender and bid activity timeline

**Problem:** Hard to see “what changed” on a tender or bid over time.

**Suggestion:** You already have `TenderStatusHistory` and `BidAuditLog`. Expose them in a simple timeline API, e.g. `GET /tenders/tenders/{slug}/timeline/` and `GET /bids/{id}/timeline/` returning a list of events (date, status/action, optional user). **UX:** “Activity” or “History” tab on tender and bid detail pages.

---

### 3.3 Search and filters for tenders

**Problem:** Finding the right tenders among many is difficult.

**Suggestion:** Extend list filters: by date range (publication, deadline), value range if you store estimated value, location/region if you add it, and free-text search on title and reference_number. **Backend:** Use Django filter backends and `SearchFilter`; keep filters documented in API.md. **UX:** Filter bar and search box on the tender list.

---

### 3.4 Mobile-friendly and PWA

**Problem:** Many users may use phones to check tenders and deadlines.

**Suggestion:** Ensure the frontend is responsive; consider a simple PWA (manifest + service worker) so users can “Add to home screen” and get basic offline behavior (e.g. cached list of saved tenders). No backend change required if the API is already consumed by the same frontend.

---

## 4. Summary table

| Feature                         | Impact   | Effort   | Notes                                      |
|---------------------------------|----------|----------|--------------------------------------------|
| Guided onboarding checklist     | High     | Medium   | Reduces drop-off, clarifies first steps   |
| Tender document/summary payment | High     | High     | Unlocks revenue and spec compliance        |
| Bid readiness / validate UI     | High     | Low–Med  | Uses existing validate-submit API          |
| Deadline reminders              | High     | Medium   | Scheduled job + notifications              |
| Team tasks (expand)              | Medium   | Low      | Builds on existing tasks                    |
| Agency verification badge       | Medium   | Low      | Trust signal                                |
| Post-award rating               | Medium   | Medium   | Quality signal for the market               |
| Saved tenders                   | Medium   | Low      | Simple model + endpoint                     |
| Tender/bid timeline             | Medium   | Low      | Expose existing history/audit              |
| Search and filters              | Medium   | Low–Med  | Better discovery                            |
| Mobile / PWA                    | Medium   | Medium   | Frontend and optional PWA                   |

---

These suggestions align with the existing BidsConnect spec (BIDS_CONNECT_SPEC.md), system flows (SYSTEM_FLOW.md), and the current API. Prioritise by your roadmap (e.g. payment and onboarding first, then reminders and trust features).
