# Role-Based Dashboards & Workspace Review

Inspection, design, and planning only. Nothing in this document has been implemented.

---

## Phase 1 — Repository Inspection

### 1. Current Dashboard Architecture

**Every dashboard/page implemented today:**

| Route | Component | Role |
|---|---|---|
| `/student/dashboard` | `pages/student/Dashboard.tsx` | student |
| `/staff/dashboard` | `pages/staff/Dashboard.tsx` | every non-student, non-admin role (one shared dashboard) |
| `/admin/dashboard` | `pages/admin/Dashboard.tsx` | admin |
| `/staff/reports`, `/admin/reports` | `pages/reports/Reports.tsx` (same component, mounted twice) | staff, admin |
| `/student/notifications` | `pages/student/Notifications.tsx` | student |

Supporting pages that dashboards link out to (not dashboards themselves, but part of the same workspace): `student/MyIssues`, `student/TrackStatus`, `student/CreateIssue`, `staff/AssignedIssues`, `staff/AllIssues`, `admin/Users`, `admin/StaffCreate`, `admin/Departments`, `admin/Categories`, `admin/DocumentTypes`, `issues/IssueDetail` (shared by all three roles via `/student/issues/:id` and `/staff/issues/:id`), `profile/Profile`.

**Routing structure** (`App.tsx`): a single `BrowserRouter` with three role-gated subtrees, each wrapped in `RoleRoute` (checks `roleGroup` — `'student' | 'staff' | 'admin'`, a 3-way collapse of the 13 real `Role` values) and then `AppShell`. There is no route-level distinction *within* "staff" — a Course Adviser, an ICT Officer, and a Bursary Officer all land on the exact same `/staff/dashboard` route and component today.

**Layout components**: `AppShell` (sidebar + topbar + routed `<Outlet/>`, mounted once per role group) → `Sidebar` (reads a `NAV_BY_ROLE: Record<RoleGroup, NavItem[]>` map — three fixed nav lists, one per `RoleGroup`, not per individual `Role`) → `Topbar`.

**Reusable cards/widgets already in `components/ui/`**: `StatCard` (icon + value + label, 6 color tones), `IssueCard` (title + ref + status badge, used in every dashboard's "recent/queue" list), `EmptyState`, `CardSkeleton`/`TableSkeleton`/`Skeleton`/`PageLoader`/`Spinner`, `DataTable` (generic, used by `AllIssues`), `Filters.tsx` (`SearchInput`, `SelectFilter`, `FilterBar`), `Pagination`, `StatusBadge`, `ActivityTimeline`, `StatusStepper`, `DocumentUploadWidget`, `Modal`, `Alert`, `PageHeader`, `FormField` primitives.

**Charts already available**: `recharts` is already a dependency, already used in `Reports.tsx` — a `LineChart` (submitted vs. resolved trend) and a `BarChart` (issues by status). No chart library needs to be added for dashboard work.

**Statistics currently displayed:**
- Student dashboard: Total Issues, Open/Under Review, In Progress, Resolved/Closed (all computed client-side from `listIssues()` filtered to `student === user.email`), plus a 5-item "Recent Issues" list.
- Staff dashboard (generic, all non-admin staff roles): Assigned to Me, Awaiting Review, In Progress, Resolved/Closed (computed from `listIssues()` filtered to `assigned_to === user.email`), plus a 6-item "Active Queue".
- Admin dashboard: Total Issues, Open Issues, Unassigned Issues (the one real server-filtered number, via `?unassigned=true`), Total Users, Departments (the last two from the **mock** store), plus Recent Issues and a static Quick Links list.
- Reports (shared staff/admin): Total Issues, Open Issues, Resolved/Closed, Categories in Use, a submitted-vs-resolved trend line, an issues-by-status bar chart, and a per-department table (open/resolved/avg resolution days).

**How data is fetched**: every dashboard calls `listIssues()` — `GET /api/issues/` — which returns **every issue in the system, unfiltered, unpaginated** (confirmed in `issues/views.py::IssueListAPIView.get`; the only server-side filter that exists at all is `?unassigned=true`). All role-scoping ("my issues," "assigned to me") happens client-side by comparing `issue.student`/`issue.assigned_to` against `user.email` after the full fetch. This is a real, working pattern today, but it does not scale past a small dataset and provides no true per-user query — worth flagging under Problems below.

**Role-aware or shared?** Partially. Layout (sidebar nav, route access) is role-*group*-aware (student/staff/admin, 3 buckets). Dashboard **content** is role-*group*-aware in the sense that student/staff/admin each get a different component — but within "staff" (11 distinct real roles), every role sees the identical dashboard, filtered only by `assigned_to === me`. Nothing today is aware that a Course Adviser's job is fundamentally different from a Bursary Officer's.

### 2. Role Detection

- **Where role comes from**: `UserProfile.role` on the backend (`accounts/models.py`), returned in the login response and cached client-side (`AuthContext` reads `getStoredProfile()`/`apiLogin()`, no `/me/` endpoint exists to re-fetch it).
- **Does the frontend group roles?** Yes — `roleGroup(role: Role): RoleGroup` in `types/index.ts` collapses all 13 roles to `'student' | 'staff' | 'admin'` (`student` → student, `admin` → admin, everything else → staff). This is the *only* grouping that exists; there is no intermediate grouping (e.g., "central" vs. "department-scoped", or "academic" vs. "administrative").
- **Do dashboards branch on role?** Only at the 3-way `RoleGroup` level, via which *component* mounts (`StudentDashboard`/`StaffDashboard`/`AdminDashboard`). No dashboard component itself branches further on the specific `Role` value.
- **Do separate layouts already exist?** Yes, at the `RoleGroup` level only: `Sidebar`'s `NAV_BY_ROLE` gives student/staff/admin three different nav lists. There is no per-`Role` layout or nav variant.

### 3. Existing API Support

| Existing endpoint | Current response | Can dashboards use it? | Needs modification? |
|---|---|---|---|
| `GET /api/issues/` | Every `Issue` (id, title, description, student, assigned_to, category, department, status, is_complete, resolution_notes, created_at), unpaginated, unfiltered by user | Yes — already the sole data source for all three existing dashboards | Not required for current scope; a `?assigned_to=me` / `?student=me` server-side filter would be an optional efficiency improvement, not a blocker |
| `GET /api/issues/?unassigned=true` | Same shape, `assigned_to__isnull=True` only | Yes — already powers the admin "Unassigned Issues" stat | No |
| `GET /api/issues/:id/` | Full `IssueDetail` — adds `documents`, `activity_history`, `updated_at`, `required_documents` | Yes — used today by `Notifications.tsx` (flattens every issue's `activity_history` into a feed) | No |
| `GET /api/accounts/staff/directory/` | Every non-student `UserProfile` (id, name, email, role, department_name) | Yes — the only real source for "how many officers hold role X" / per-role staff counts; currently admin-only (`IsSystemAdmin`) | No, if reused as-is for admin-only dashboard widgets. Would need broadening (or a narrower variant) if a non-admin dashboard ever needed staff counts, which nothing in this design requires |
| `GET /api/categories/` | 12 canonical categories with `department` name | Yes — already used by the ML manual-selection flow; a dashboard "categories in use" stat can derive from `listIssues()` client-side as `Reports.tsx` already does, so this isn't strictly needed for stats, only if a dashboard needs the full category list | No |
| `POST /api/issues/:id/assign/` etc. (workflow action endpoints) | Standard `{status, assigned_to}` results | Not dashboard reads, but relevant as the "useful shortcuts" a role-specific dashboard could deep-link into | No |
| — (no endpoint) | — | **No dashboard-stats/aggregation endpoint exists.** Every count on every dashboard today is computed client-side after a full unfiltered fetch. | This is a genuine architectural gap for a role-specific dashboard set (11 staff roles), addressed in the Gap Analysis below — not because today's pattern is broken, but because per-role widgets multiply the amount of client-side filtering needed from one `listIssues()` result |
| — (no endpoint) | — | **No endpoint exposes ML classification outcomes** (confidence tier / auto-created vs. confirmed vs. manually-selected). Confirmed: `Issue` model has no `predicted_category`/`confidence`/`classification_source` field — `predict_issue()`'s confidence score is used once, in-memory, at submission time, and never persisted. | Any "ML classification metrics" widget on the Admin Dashboard needs a new persisted field before it can show real data — flagged explicitly in the Gap Analysis, not assumed away |
| — (no endpoint) | — | **No accounts/users list endpoint** (admin "Total Users" stat is mock-sourced today via `api/mock/store.ts::listUsers()`) | Same for **no departments list endpoint** (admin "Departments" stat is mock-sourced); both are pre-existing, already-documented gaps from earlier phases, not introduced by this review |

### 4. Existing Components

| Component | Reuse for dashboards? |
|---|---|
| `StatCard` | Yes, directly — every stat tile in every proposed dashboard below reuses this exact component |
| `IssueCard` | Yes, directly — every "recent/queue/awaiting-you" list reuses this |
| `DataTable` + `Filters` (`SearchInput`/`SelectFilter`/`FilterBar`) + `Pagination` | Yes — any dashboard widget that needs a mini table (e.g., "issues by category" breakdown) reuses these rather than a new table component |
| `ActivityTimeline` | Yes — a "recent activity" dashboard widget can reuse this as-is (it already accepts any `IssueActivityRecord[]`) |
| `EmptyState`, `CardSkeleton`/`TableSkeleton`/`PageLoader` | Yes — every new widget should use the existing loading/empty patterns, not invent new ones |
| `StatusBadge` | Yes — used anywhere an issue status needs to render |
| `StatusStepper` | Reusable for a "progress summary" style widget on the student dashboard, though it currently expects a single issue's `TimelineStep[]` (from `lib/timeline.ts`) — fine for an issue-detail-style widget, not directly a multi-issue aggregate |
| Charts (`recharts` `LineChart`/`BarChart` as used in `Reports.tsx`) | Yes — the exact same chart setup can be embedded directly inside a dashboard rather than rebuilt |
| Role guards | **No dedicated component exists.** Role gating is done exactly two ways today: route-level (`RoleRoute` in `routes/ProtectedRoute.tsx`, gates by `RoleGroup`) and inline conditionals inside individual pages (e.g., `IssueDetail.tsx`'s `canManage`/`isOwner` checks). Per-role dashboard widgets will need the same inline-conditional pattern, keyed off `user.role` (the real `Role`, not just `RoleGroup`) — no new "role guard" abstraction needs to be invented, but note that today's `RoleRoute` only understands `RoleGroup`, not individual roles, so it cannot itself gate an individual widget by e.g. "Bursary only." |
| Notification cards | `Notifications.tsx`'s list-item markup (icon circle + action + issue ref + timestamp) is a reusable visual pattern but isn't extracted into its own component today — worth extracting if reused inside a dashboard widget rather than copy-pasted a third time |

### 5. Existing Reports

`Reports.tsx` (shared by `/staff/reports` and `/admin/reports`) already contains three visualizations, **all computed client-side from real `listIssues()` data** (per `api/mock/reports.ts`'s own header comment): a submitted-vs-resolved trend `LineChart`, an issues-by-status `BarChart`, and a per-department summary table (open/resolved/avg resolution days). All three are directly reusable *inside* dashboards instead of being rebuilt — e.g., the issues-by-status bar chart is a natural admin-dashboard widget, and the department summary table is a natural fit for any department-scoped staff role's dashboard. The only non-reusable numbers in that file are `total_users`/`total_departments`, which fall back to the mock store (pre-existing, documented gap, not something this task needs to fix to build dashboards — just something dashboards should avoid depending on for new widgets).

---

## Phase 2 — Dashboard Design Review

Architecture only — no components, no endpoints, no code below.

### Student Dashboard

Grounded entirely in data the backend already returns from `listIssues()`/`getIssue()`:

- **My open issues** — already shown today (Open/Under Review + In Progress stat cards); keep.
- **Issues awaiting my confirmation** — new, but backend-supported: any of my issues with `status === 'resolved'` is exactly the set the existing `ResolutionResponsePanel` (built in the Student Confirmation task) gates on. A dashboard widget just needs to filter my own `listIssues()` result to `status === 'resolved'` — no backend change.
- **Issues awaiting documents** — new, but backend-supported: `IssueDetail.required_documents` vs. `documents` (or simply `is_complete === false`, which the backend already computes and returns on the plain `Issue` shape from `listIssues()`) identifies exactly this set without an extra per-issue detail fetch.
- **Recently updated issues** — backend-supported via `updated_at` (present on `IssueDetail`, not on the plain list `Issue` shape — see Gap Analysis: either a per-issue detail fetch per dashboard load, or adding `updated_at` to the list serializer, is needed to sort by this cheaply).
- **Recent activity** — already built for the standalone Notifications page (flattening `activity_history` across all my issues); the same data can power a compact "recent activity" dashboard widget by reusing that existing fetch pattern.
- **Quick actions** — already present (Create Issue button in the header); could add "Upload Documents" / "Respond to Resolution" shortcuts that deep-link to issues actually in those states, using the same filters above.
- **Notifications** — the dashboard doesn't need to duplicate the full Notifications page; a "3 most recent" preview linking to `/student/notifications` is enough, matching the existing Recent Issues pattern.
- **Progress summary** — not a new concept: reusing `StatusStepper`/`lib/timeline.ts` per-issue is well-supported, but there's no backend-supported concept of a single aggregate "progress" number across all my issues; recommend not inventing one — a status-mix stat row (already what exists) is the honest representation.

No invented data: everything above is derivable from `listIssues()` + the existing per-issue detail shape. Nothing here requires a new endpoint.

### Staff Dashboard — Per Role

The backend has 11 distinct staff roles, each participating in a different subset of the 12 workflow definitions (`issues/workflow/definitions.py`, inspected directly). Below is what each role actually owns, not an assumption.

**Course Adviser** (department-scoped)
- Responsibilities / stages owned: starting role for Missing Result, Grade Dispute, Course Registration; final authority (resolves) for all three.
- Useful widgets: "Awaiting my action" (assigned to me, any status not resolved/closed), a small breakdown by these 3 categories, "sent back to me" count (HOD/Lecturer/Exams Officer can all send back to Course Adviser).
- Shortcuts: jump straight into Start Review / Resolve for the oldest item in queue.
- Statistics: assigned-to-me counts by status — fully supported today via `listIssues()` filtered client-side.
- Missing backend support: none for the above; only a bottleneck ("average time issues sit with me") would need `updated_at`/timestamps not currently on the list shape.

**HOD** (department-scoped)
- Responsibilities: mid-chain stage for Missing Result, Transcript Request, Examination Issue; starting/final role for "Other" (dynamic forward — HOD decides where "Other" issues actually go); final authority for Academic Clearance (after Department Admin sends back).
- Useful widgets: "Other-category issues needing routing" (since HOD alone chooses the forward destination for these), department escalation queue.
- Shortcuts: Forward-with-role-picker (already built in the Workflow Action UI) surfaced directly from the dashboard for "Other" issues.
- Missing backend support: none — `dynamic_forward` and `target_role` are already exposed via the existing `/forward/` endpoint.

**Department Admin** (department-scoped)
- Responsibilities: starting role for Transcript Request and Academic Clearance; final authority for Academic Clearance.
- Useful widgets: "Awaiting my action" queue split by these 2 categories.
- Missing backend support: none.

**Department Examination Officer** (department-scoped)
- Responsibilities: starting role + one of two final authorities for Examination Issue (shared with Exams Officer).
- Useful widgets: single-category queue (Examination Issue only) — the narrowest of any role, a good candidate for the simplest possible dashboard variant.
- Missing backend support: none.

**Lecturer** (department-scoped)
- Responsibilities: mid-chain stage for Grade Dispute only — never a final authority (always sends back to Course Adviser).
- Useful widgets: single-category queue; the dashboard should make clear this role can only "send back," never "resolve," to avoid a misleading Resolve shortcut — the existing `WorkflowActionsPanel`'s `ACTIONS_FOR_STATUS` map already encodes this correctly at the issue level, so a dashboard shortcut into an issue naturally won't offer Resolve.
- Missing backend support: none.

**ICT Officer** (central)
- Responsibilities: sole stage + final authority for Portal/System Issue.
- Useful widgets: single-category queue.
- Missing backend support: none.

**Exams Officer** (central)
- Responsibilities: final-stage/final-authority role for Missing Result and Examination Issue; final-stage-but-not-final-authority for Course Registration (must send back to Course Adviser, cannot resolve) and Transcript Request's sole final authority.
- Useful widgets: queue split across 4 categories; worth surfacing which items this role *can* resolve vs. must send back, since that varies by category — a genuinely useful, backend-supported distinction (`is_final_authority` is already computed server-side inside `workflow/service.py`, though not currently exposed as a per-issue flag in `IssueSerializer` — see Gap Analysis).
- Missing backend support: a per-issue "can I resolve this" flag would need to be added to the serializer to avoid re-deriving workflow rules in the frontend; not strictly required (the existing `WorkflowActionsPanel` already only shows Resolve when appropriate once the issue is opened), only relevant if the dashboard wants to show this ahead of opening the issue.

**Registry** (central)
- Responsibilities: starting role for Certificate Collection (forwards to Bursary; not itself a final authority for anything).
- Useful widgets: single-category, forward-only queue.
- Missing backend support: none.

**Bursary** (central)
- Responsibilities: sole stage + final authority for School Fees Issue; final stage + final authority for Certificate Collection (after Registry forwards).
- Useful widgets: queue split across 2 categories.
- Missing backend support: none.

**School Administration Office** (central)
- Responsibilities: sole stage + final authority for Admission Issue.
- Useful widgets: single-category queue.
- Missing backend support: none.

**Student Affairs Officer** (central)
- Responsibilities: sole stage + final authority for Student Welfare.
- Useful widgets: single-category queue.
- Missing backend support: none.

**Cross-cutting observation**: every role's "useful widgets" reduce to the same shape — a category-scoped slice of "assigned to me," plus role-appropriate shortcuts the existing `WorkflowActionsPanel` already knows how to render once an issue is opened. This means the *ideal* architecture is not 11 bespoke dashboard components, but one parametrized staff-dashboard component driven by a small per-role config (which categories this role cares about, and a label) — see the Recommended Architecture implied by the roadmap below. No backend change is required for any of the 11 roles' primary workload view; the only backend gaps identified are the optional "can resolve" flag (Exams Officer, and really any final-authority role) and timestamp-based bottleneck metrics.

### Admin Dashboard

**Does it reflect the new (workflow-engine-driven) architecture?** Partially.

- **Obsolete/misleading**: the "Departments" stat card (`overview.total_departments`) is sourced from the mock `Department` catalogue, not the real academic-department data now used for routing (per the recent Department Architecture Review) — it's a count of 5 fake mock rows, not a meaningful number today.
- **Missing widgets**: nothing currently shows *per-role* staff coverage (e.g., "0 Lecturers exist — Grade Dispute issues will never be assigned") even though `GET /api/accounts/staff/directory/` already has everything needed to compute it; nothing shows workflow bottlenecks (which category/role combination has the most issues stuck longest); nothing shows assignment-outcome metrics (% auto-assigned vs. manually assigned — `manual_assign_officer` vs. `perform_initial_assignment` both write the same `IssueActivity`-logged outcome, so this is derivable from existing activity data, just not aggregated anywhere yet).
- **Duplicate widgets**: none found — the admin dashboard and Reports page show overlapping but not identical numbers (dashboard: snapshot counts + recent issues + quick links; reports: trend + status breakdown + department table), which is reasonable separation, not duplication.
- **Statistics that should be added**: unassigned-by-role breakdown (which specific role has no available officer — directly explains *why* an issue is unassigned, using the same `CENTRAL_ROLES`/`DEPARTMENT_SCOPED_ROLES` distinction already in `workflow/definitions.py`), staff headcount by role (from the staff directory endpoint, already real data), manual-vs-automatic assignment ratio (derivable from `IssueActivity.action` strings, e.g. "Automatically Assigned" vs. "Manually Assigned" — needs confirming exact action text, not inventing new ones).
- **ML classification metrics**: **not currently possible** with real data — as established in Phase 1 §3, confidence/classification-source is never persisted on `Issue`, so any such widget would need a backend field added first; recommend explicitly deferring this widget rather than faking it.
- **System health metrics**: nothing resembling uptime/error-rate exists in this system (no such infrastructure), and none should be invented — out of scope for a student issue tracker at this stage.

---

## Phase 3 — Gap Analysis

| Feature | Status | Frontend/Backend | Priority | Difficulty | Reuse existing component? |
|---|---|---|---|---|---|
| Student: awaiting-confirmation widget | Missing | Frontend only (data already in `listIssues()`) | High | Trivial | `IssueCard`, `StatCard` |
| Student: awaiting-documents widget | Missing | Frontend only (`is_complete` already returned) | High | Trivial | `IssueCard`, `StatCard` |
| Student: recent activity widget | Missing | Frontend only (reuse `Notifications.tsx`'s fetch pattern) | Medium | Low | `ActivityTimeline` pattern |
| Per-role staff dashboard (11 roles) | Missing | Frontend only | High | Medium (one parametrized component + per-role config, not 11 components) | `StatCard`, `IssueCard`, `DataTable` |
| "Other"-category routing widget (HOD) | Missing | Frontend only | Medium | Low | Existing `ForwardForm` UI, surfaced earlier |
| Per-issue "can I resolve this" flag | Missing | Backend + frontend | Low | Low (one serializer field) | — |
| Admin: real department count | Partially implemented (mock-backed) | Requires both (see prior Department Architecture Review — postponed by design) | Low (already explicitly postponed) | — | — |
| Admin: staff headcount by role | Missing | Frontend only (`staff/directory/` already returns role) | Medium | Low | `StatCard` |
| Admin: unassigned-by-role breakdown | Missing | Frontend only, derived from `?unassigned=true` + staff directory role gaps | Medium | Medium | `DataTable` |
| Admin: manual-vs-automatic assignment ratio | Missing | Frontend only, derived from existing `IssueActivity.action` strings — needs verifying exact strings, not new backend logic | Low | Medium | `StatCard`/chart |
| Admin: ML classification metrics | Missing | Requires both (new persisted field + aggregation) | Low (explicitly out of reach without a schema change) | Medium | — |
| Dashboard-scoped stats endpoint (efficiency) | Not implemented | Backend only, optional | Low (today's client-side approach still works at current scale) | Medium | — |
| Reuse Reports charts inside dashboards | Not yet wired in | Frontend only | Medium | Trivial | `recharts` setup from `Reports.tsx` directly |

---

## Phase 4 — Implementation Plan

Ordered highest value to lowest value. Every task reuses existing services/serializers/components; none redesign the workflow engine, auth, or permissions; none duplicate an existing endpoint or introduce mock data.

**1. Student dashboard: add "Awaiting your confirmation" and "Awaiting documents" widgets**
- Goal: surface the two most actionable student states without opening every issue.
- Files likely affected: `pages/student/Dashboard.tsx` only.
- Backend changes required? No.
- Frontend changes required? Yes — filter the already-fetched `issues` array by `status === 'resolved'` and `is_complete === false`; render with existing `IssueCard`/`StatCard`.
- Risk: none — purely additive, reuses the exact fetch already in place.
- Dependencies: none.
- Estimated complexity: trivial.

**2. Build one parametrized staff dashboard driven by per-role category ownership**
- Goal: replace the single generic `StaffDashboard` with a component that reads the logged-in user's real `Role` (not just `RoleGroup`) and shows only the categories/stages that role actually owns, per the Phase 2 per-role table above.
- Files likely affected: `pages/staff/Dashboard.tsx` (rewritten), a new small config object (e.g. `lib/roleWorkloadConfig.ts`) mapping each `Role` to its owned category names — mirrors `WORKFLOW_DEFINITIONS` data already on the backend, so this config should be treated as a read-only projection of it, not a second source of truth invented independently (ideally documented as "derived from issues/workflow/definitions.py — keep in sync manually since there's no categories-by-role endpoint").
- Backend changes required? No.
- Frontend changes required? Yes — the dashboard component and the new config.
- Risk: low-medium — must stay in sync with `definitions.py` if categories/roles change; call out clearly in code comments (same pattern already used for `FORWARD_TARGET_ROLES` mirroring backend `valid_roles`).
- Dependencies: none (Task 1 not required first, but logically pairs well).
- Estimated complexity: medium.

**3. Admin dashboard: staff headcount by role**
- Goal: show how many accounts exist per role, directly surfacing "0 Lecturers" style coverage gaps.
- Files likely affected: `pages/admin/Dashboard.tsx`, reusing `GET /api/accounts/staff/directory/` (already admin-only, already returns `role`).
- Backend changes required? No.
- Frontend changes required? Yes — fetch staff directory, group by role client-side, render with `StatCard`/`DataTable`.
- Risk: none.
- Dependencies: none.
- Estimated complexity: low.

**4. Admin dashboard: unassigned-by-role breakdown**
- Goal: explain *why* issues are unassigned by cross-referencing `?unassigned=true` issues' categories against which role each needs (via the workflow definitions) and whether any staff member holds that role (via the staff directory).
- Files likely affected: `pages/admin/Dashboard.tsx`, possibly a small shared helper if the category→role mapping from Task 2's config is reused here too (recommended, to avoid a second copy).
- Backend changes required? No.
- Frontend changes required? Yes.
- Risk: low — purely a read/aggregation feature.
- Dependencies: benefits from Task 2's role/category config existing first.
- Estimated complexity: medium.

**5. Wire existing Reports charts into the Admin and per-role Staff dashboards**
- Goal: stop treating Reports as a separate destination for charts that are already computed from real data; surface the issues-by-status bar chart (admin) and a category-scoped version of it (staff) directly on the dashboard.
- Files likely affected: `pages/admin/Dashboard.tsx`, `pages/staff/Dashboard.tsx`, no changes to `Reports.tsx` itself or `api/mock/reports.ts`'s real-data functions (`getIssueTrend`, `getDepartmentSummaries` stay as the shared source).
- Backend changes required? No.
- Frontend changes required? Yes.
- Risk: none.
- Dependencies: none.
- Estimated complexity: low.

**6. Recent-activity widget on the student dashboard**
- Goal: a compact preview of the same real activity feed `Notifications.tsx` already builds, without duplicating that page in full.
- Files likely affected: `pages/student/Dashboard.tsx`, optionally extracting `Notifications.tsx`'s fetch-and-flatten logic into a small shared hook/helper if reused (recommended over copy-pasting it a second time).
- Backend changes required? No.
- Frontend changes required? Yes.
- Risk: low — the flatten-and-fetch-per-issue pattern already exists and is proven; performance is bounded by the same "no per-user filter on GET /api/issues/" limitation already present everywhere else.
- Dependencies: none.
- Estimated complexity: low.

**7. (Optional, lowest priority) Per-issue "can I resolve this" serializer flag**
- Goal: let a dashboard show, before opening an issue, whether the viewing officer could resolve it outright vs. only forward/send back — currently only computable inside `workflow/service.py` at action time.
- Files likely affected: `issues/serializers.py` (add one `SerializerMethodField` to `IssueSerializer`, reusing `WorkflowDefinition.is_final_authority()` — no new logic, just exposing an existing check).
- Backend changes required? Yes — additive only, one field, reuses existing workflow-engine logic rather than duplicating it.
- Frontend changes required? Yes — minor, to render the flag on relevant staff dashboard queues.
- Risk: low, but is the only task in this plan that touches the backend at all — should be reviewed carefully to confirm it truly adds nothing beyond exposing an existing computation.
- Dependencies: Task 2 (only meaningful once per-role dashboards exist to show it in).
- Estimated complexity: low.

**8. (Deferred, not recommended yet) ML classification metrics widget**
- Goal: show auto-classified vs. confirmed vs. manually-selected issue ratios on the admin dashboard.
- Why deferred: requires a genuinely new persisted field on `Issue` (or a new small model) to record classification outcome at creation time — the only task in this entire plan that isn't just "expose what already exists." Recommend treating this as a separate, explicitly-scoped future task (mirroring how the Department redesign was treated) rather than folding it into dashboard work.
- Estimated complexity: medium-high, backend-first.

Tasks 1–6 require no backend changes at all and can be built in any order with no interdependencies except the two noted (Task 4 benefits from Task 2's shared config; Task 7 is only useful after Task 2). Task 7 is the only backend touch in the plan, is strictly additive, and is optional. Task 8 is explicitly out of scope for now and flagged for separate future planning, consistent with how ML classification integration itself was originally scoped.
