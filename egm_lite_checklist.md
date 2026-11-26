# EGM-Lite Checklist — Widget chiffre d'affaires

## Baseline

- Starting commit: `a0f494d2b0d46c576660acefa86f828756ea8ddd`.
- Pre-existing work to preserve: dashboard shell, period picker, timeline,
  module/configuration docs and scenario updates already present in the working
  tree.
- This task intentionally reuses and extends the uncommitted dashboard page,
  labels, scenario and documentation; those pre-existing hunks must remain
  distinguishable from the revenue-widget changes during review.

## Implementation Tasks

- [ ] Add the dashboard revenue contract in
  [backend/app/schemas/dashboard.py](/home/klemou/Dev/haccpFlow/backend/app/schemas/dashboard.py):
  `from`, `to`, `total_cents`, `cash_cents`, `cheque_cents`, `card_cents`,
  `cash_expenses_cents` and `closed_session_count`.
- [ ] Implement the aggregation in
  [backend/app/services/dashboard.py](/home/klemou/Dev/haccpFlow/backend/app/services/dashboard.py).
  Count only closed, non-deleted sessions whose `session_date` is between the
  inclusive UTC bounds. Cash revenue is
  `closing - opening + professional expenses + personal expenses`. Cheque and
  card revenue use the collected amount. Keep the breakdown for the widget.
- [ ] Expose
  `GET /api/v1/dashboard/revenue?from=YYYY-MM-DD&to=YYYY-MM-DD` to admin and
  operator roles in
  [backend/app/api/v1/dashboard.py](/home/klemou/Dev/haccpFlow/backend/app/api/v1/dashboard.py),
  register it in the v1 router, and reject `from > to` with
  `422 dashboard_range_invalid`.
- [ ] Add focused integration tests in
  [backend/tests/test_dashboard_api.py](/home/klemou/Dev/haccpFlow/backend/tests/test_dashboard_api.py)
  for the cash formula, cheque/card totals, inclusive date filtering,
  excluding open and deleted sessions, empty periods, invalid ranges and role
  access.
- [ ] Add the new route to
  [backend/tests/test_openapi.py](/home/klemou/Dev/haccpFlow/backend/tests/test_openapi.py).
- [ ] Add `DashboardRevenue` to
  [frontend/src/lib/types.ts](/home/klemou/Dev/haccpFlow/frontend/src/lib/types.ts)
  and render a KPI widget above the timeline through a new
  `frontend/src/components/dashboard/revenue-widget.tsx`.
- [ ] Fetch the aggregate from
  [frontend/src/app/(app)/page.tsx](</home/klemou/Dev/haccpFlow/frontend/src/app/(app)/page.tsx>)
  using the active dashboard range. Display the total, cash/cheque/card
  subtotals, cash expenses added back and closed-session count.
- [ ] Update dashboard labels in
  [frontend/src/lib/i18n.ts](/home/klemou/Dev/haccpFlow/frontend/src/lib/i18n.ts)
  and change the timeline empty state so it no longer claims that no widget
  exists when the revenue KPI is visible.
- [ ] Extend
  [scenario/check_frontend_pages.py](/home/klemou/Dev/haccpFlow/scenario/check_frontend_pages.py)
  to verify that the revenue widget renders for the selected period.

## Documentation Tasks

- [ ] Document the revenue rule and negative-result behaviour in
  [doc/03-domaines-metier.md](/home/klemou/Dev/haccpFlow/doc/03-domaines-metier.md).
- [ ] Document the new route and response in
  [doc/04-api.md](/home/klemou/Dev/haccpFlow/doc/04-api.md).
- [ ] Document the widget, its formula and empty state in
  [doc/06-frontend.md](/home/klemou/Dev/haccpFlow/doc/06-frontend.md).
- [ ] Update the dashboard roadmap, root README, scenario README and
  `doc/README.md` review date.

## Verification Tasks

- [ ] Run targeted backend integration tests with PostgreSQL.
- [ ] Run the complete backend suite to detect route and documentation
  regressions.
- [ ] Run Ruff, formatting checks and MyPy.
- [ ] Run frontend TypeScript checks and render `/` against the local services
  for the default and custom periods.
- [ ] Confirm `git diff --check` is clean and inspect the final diff against the
  recorded baseline.

## Risks and Edge Cases

- The opening float must never be counted as new revenue.
- Cash expenses are added back only for `cash`; cheque/card amounts are already
  gross.
- A mathematically valid negative cash result is displayed rather than clamped.
- Historical sessions remain included if their register was later deactivated;
  only the session's own `deleted_at` excludes it.
- No database migration or new runtime dependency is expected.

---

### 🔍 Assumption Lifecycle Legend:

- `[⚠️ UNVERIFIED]`: Siloed external contract. Requires indisputable evidence to verify.
- `[⏳ ACK]`: Acknowledged assumption. Factual evidence unavailable; risk accepted and opaque-box empirical test strictly scheduled.
