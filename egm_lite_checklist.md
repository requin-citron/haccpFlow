# EGM-Lite Checklist — Dashboard configurable et widget chiffre d'affaires

## Baseline

- Starting commit: `84a42f8e839487c5a443d9ab9e01a26a2a9e8789`.
- Pre-existing work: only `egm_lite_alternatives.md` is modified in the working
  tree. The dashboard shell and period picker are committed.
- No revenue widget or dashboard layout API exists in the baseline.

## Backend: Revenue Data

- [x] Add `DashboardRevenueRead` in
  [backend/app/schemas/dashboard.py](/home/klemou/Dev/haccpFlow/backend/app/schemas/dashboard.py)
  with `from`, `to`, `total_cents`, `cash_cents`, `cheque_cents`, `card_cents`,
  `cash_expenses_cents` and `closed_session_count`.
- [x] Add `dashboard_revenue()` in
  [backend/app/services/dashboard.py](/home/klemou/Dev/haccpFlow/backend/app/services/dashboard.py).
  Use closed, non-deleted sessions in the inclusive UTC date range.
  - Cash: `closing - opening + professional expenses + personal expenses`.
  - Cheque/card: `collected_amount_cents`.
  - Preserve negative cash results.
- [x] Expose `GET /api/v1/dashboard/revenue?from=YYYY-MM-DD&to=YYYY-MM-DD`
  to admin/operator and return `422 dashboard_range_invalid` when the bounds
  are reversed.

## Backend: Persistent Layout

- [x] Add `DashboardLayout` in
  [backend/app/models/dashboard_layout.py](/home/klemou/Dev/haccpFlow/backend/app/models/dashboard_layout.py):
  UUID primary key, unique `user_id` FK with `ON DELETE CASCADE`, JSONB
  `widgets`, and standard timestamps. Export it from `app.models`.
- [x] Create Alembic revision `0018_dashboard_layouts` with the table, unique
  user constraint/index and cascade FK. No tenant ID is hardcoded; the existing
  one-instance-per-client architecture remains unchanged.
- [x] Define backend-validated layout schemas in
  [backend/app/schemas/dashboard.py](/home/klemou/Dev/haccpFlow/backend/app/schemas/dashboard.py):
  - widget key is currently limited to `revenue`;
  - `column_start` is 1–12;
  - `width_columns` is 3–12;
  - `row_span` is 5–12 and defaults to 6;
  - `column_start + width_columns - 1 <= 12`;
  - widget keys are unique;
  - an empty widget list is valid and differs from “no saved layout”.
- [x] Implement per-user load and atomic upsert in
  [backend/app/services/dashboard.py](/home/klemou/Dev/haccpFlow/backend/app/services/dashboard.py).
  If no row exists, return the default layout containing revenue at
  `column_start = 1`, `width_columns = 12`. Once a user saves a layout, replace
  the complete JSONB list, including an empty list.
- [x] Add `GET /api/v1/dashboard/layout` and
  `PUT /api/v1/dashboard/layout` in
  [backend/app/api/v1/dashboard.py](/home/klemou/Dev/haccpFlow/backend/app/api/v1/dashboard.py).
  Both routes use the authenticated user and allow admin/operator roles.
- [x] Register the dashboard router in the v1 API and add the three dashboard
  paths to [backend/tests/test_openapi.py](/home/klemou/Dev/haccpFlow/backend/tests/test_openapi.py).

## Backend Tests

- [x] Add [backend/tests/test_dashboard_api.py](/home/klemou/Dev/haccpFlow/backend/tests/test_dashboard_api.py)
  covering:
  - cash revenue with both expense kinds added back;
  - cheque/card collected amounts;
  - inclusive dates, open/deleted-session exclusion and empty periods;
  - negative cash revenue;
  - invalid revenue ranges and invalid widget layouts;
  - default layout, save/reload, empty saved layout and per-user isolation;
  - role access and authentication.

## Frontend: Revenue Widget

- [x] Add `DashboardRevenue` and layout types to
  [frontend/src/lib/types.ts](/home/klemou/Dev/haccpFlow/frontend/src/lib/types.ts).
- [x] Add a server-side action in
  [frontend/src/actions/dashboard.ts](/home/klemou/Dev/haccpFlow/frontend/src/actions/dashboard.ts)
  that sends the full widget list with `PUT /api/v1/dashboard/layout` and
  revalidates `/`.
- [x] Add a reusable `revenue-widget.tsx` under
  `frontend/src/components/dashboard/` showing total, cash/cheque/card
  breakdown, cash expenses added back and closed-session count.
- [x] Update [frontend/src/app/(app)/page.tsx](</home/klemou/Dev/haccpFlow/frontend/src/app/(app)/page.tsx>)
  to load the authenticated layout and only fetch revenue data when the
  revenue widget is present.

## Frontend: Editable Grid

- [x] Add a client-side dashboard grid component with a 12-column desktop grid
  and full-width widgets on mobile.
- [x] Add a “Modifier le dashboard” mode with:
  - widget catalog containing the revenue widget;
  - add when absent, remove when present;
  - pointer-resize handles on all four sides, snapped to columns and rows;
  - removal control above the widget card, outside its sizing surface;
  - save on pointer release, add and remove.
- [x] Keep optimistic local layout state, show an actionable save error, and
  revert to the last saved layout if persistence fails.
- [x] Place the editable widget grid on the dashboard and update dashboard copy.
- [x] Add all required French/English labels to
  [frontend/src/lib/i18n.ts](/home/klemou/Dev/haccpFlow/frontend/src/lib/i18n.ts).
- [x] Add CSS needed for responsive grid placement and resize handles to
  [frontend/src/app/globals.css](/home/klemou/Dev/haccpFlow/frontend/src/app/globals.css),
  without adding a resize/grid dependency.

## Scenario and Documentation

- [x] Extend
  [scenario/check_frontend_pages.py](/home/klemou/Dev/haccpFlow/scenario/check_frontend_pages.py)
  to verify the dashboard widget renders, the edit-mode control exists and a
  custom period uses the revenue aggregate.
- [x] Document revenue rules and negative results in
  [doc/03-domaines-metier.md](/home/klemou/Dev/haccpFlow/doc/03-domaines-metier.md).
- [x] Document the three dashboard API routes, revenue response and layout
  payloads in [doc/04-api.md](/home/klemou/Dev/haccpFlow/doc/04-api.md).
- [x] Document `dashboard_layouts` and migration `0018` in
  [doc/05-base-de-donnees.md](/home/klemou/Dev/haccpFlow/doc/05-base-de-donnees.md).
- [x] Document edit mode, widget catalog, resizing, persistence and mobile
  behavior in [doc/06-frontend.md](/home/klemou/Dev/haccpFlow/doc/06-frontend.md).
- [x] Update roadmap, root README, scenario README and `doc/README.md` review
  date.

## Verification

- [x] Run targeted dashboard integration tests with PostgreSQL.
- [x] Run the complete backend suite.
- [x] Run Ruff formatting/checking and MyPy.
- [x] Run frontend TypeScript checks.
- [x] Render `/` for default and custom periods against local services.
- [x] Exercise layout GET/PUT for one user and confirm the configuration
  survives a backend restart.
- [x] Confirm `git diff --check` is clean.

## Risks and Edge Cases

- The opening float must never be counted as new revenue.
- Expenses are added back only for cash; cheque/card amounts are already gross.
- The default layout must not mutate the database during GET.
- Saving an empty list must remove all dashboard widgets persistently.
- Multi-device concurrent saves use last-write-wins semantics in this lot.
- Widget width and height apply on every viewport; all four resize handles are
  available on mobile.
- No new frontend dependency is introduced.

---

### 🔍 Assumption Lifecycle Legend:

- `[⚠️ UNVERIFIED]`: Siloed external contract. Requires indisputable evidence to verify.
- `[⏳ ACK]`: Acknowledged assumption. Factual evidence unavailable; risk accepted and opaque-box empirical test strictly scheduled.
