# Frontend Integration Audit

Inspection-only report. No files were modified to produce this document. Every finding below is grounded in the current state of the backend (`backend/issues`, `backend/accounts`, `backend/categories`, `backend/departments`, `backend/documents_app`, `backend/ml`) and frontend (`frontend/src`) as they exist in the repository today.

---

## Already Fully Integrated

- **Issue creation with ML classification.** `CreateIssue.tsx` submits only title + description, calls `POST /issues/create/`, and correctly branches on `status`: `created` (navigates straight to document upload), `confirmation_required` (renders "We think your issue is: X — Is this correct?" with Confirm/Reject), and `manual_selection_required` (renders the real category picker). Confidence values are never fetched or displayed. Rejecting a suggestion or hitting low confidence both route through `GET /api/categories/` (real, canonical categories) and never re-invoke the classifier. Matches `CreateIssueAPIView` exactly.
- **Document upload + completeness for a freshly created issue.** `UploadDocuments.tsx` consumes `required_documents` returned directly by `create_issue()` (via `location.state`), uploads through `POST /issues/:id/upload-document/`, and reflects `is_complete`/`missing_documents` from the real response.
- **Unassigned filter (Administrative Assignment Management, Feature 1).** `AllIssues.tsx`'s "Unassigned only" filter is a real server-side `?unassigned=true` call, isolating `assigned_to__isnull=True` exactly as `IssueListAPIView` implements it.
- **Dashboard "Unassigned Issues" stat (Feature 2).** `admin/Dashboard.tsx` sources this one card from a real `listIssues({ unassigned: true })` call.
- **Manual Assignment (Feature 3).** `IssueDetail.tsx`'s `ManualAssignPanel` is admin-gated (`user?.role === 'admin'`), only rendered when `issue.assigned_to` is null, sources officers from the real `GET /accounts/staff/directory/`, and posts to `POST /issues/:id/assign/`. Matches `manual_assign_officer()`/`IsSystemAdmin` exactly.
- **Assignment Status vs. workflow status (Feature 5).** `IssueDetail.tsx` renders a dedicated `AssignmentBadge` (Assigned/Unassigned) separate from `StatusBadge` (Pending/Under Review/etc.), and the "Assigned to" field on the detail page and `AllIssues` table both render an explicit "Unassigned" label instead of a blank dash or a silently-missing field (the `SerializerMethodField` fix on `assigned_to`).
- **Raw activity log completeness.** `ActivityTimeline.tsx` renders every `IssueActivity` record returned by the API verbatim (`action`, `notes`, actor, timestamp) with no allow-list or filtering — every backend-recorded action, including ones no other part of the UI has a dedicated affordance for (e.g. "Issue Forwarded", "Issue Returned", "Additional Information Requested", "Student Rejected Resolution"), is visible here. Automatic vs. manual assignment are visually distinguished (Bot icon for `is_system_action`, User icon otherwise).
- **Staff account creation (for the 6 legacy roles).** `StaffCreate.tsx` is wired to the real `POST /api/accounts/staff/`, correctly admin-gated, and correctly displays the generated temporary password once.
- **Student registration, login, forced password change.** All wired to real endpoints with no mock fallback.
- **Category-name accuracy in issue-facing views.** `AllIssues`, `MyIssues`, `AssignedIssues`, `IssueDetail`, and the ML submission flow's category picker all render category names exactly as returned by the backend (the real, canonical 12 names) — no client-side renaming or legacy label substitution occurs in these views.
- **Reports page numeric data.** `total_issues`, `open_issues`, the status breakdown chart, the submitted/resolved trend line, and the department open/resolved/avg-resolution-time table in `Reports.tsx` are all computed from the real `GET /api/issues/` response (see `api/mock/reports.ts` — despite the `mock` path, these three functions derive from real data; only `total_users`/`total_departments` are mock, see below).

---

## Missing Frontend Integrations

### 1. Forward / Send Back / Request More Information — no UI at all
- **Backend implementation:** `POST /issues/:id/forward/`, `POST /issues/:id/send-back/`, `POST /issues/:id/request-info/`, fully implemented in `workflow_service.forward_issue/send_back_issue/request_more_information`, each producing its own `IssueActivity` entry.
- **Frontend status:** Missing entirely. `frontend/src/api/issues.ts` has no functions calling any of these three endpoints. `IssueDetail.tsx`'s only action panel (`StatusUpdatePanel`) calls the legacy `PATCH /issues/:id/status/`, which only supports `in_progress`/`resolved`/`closed` — it structurally cannot express Forward, Send Back, or Request Info. An assigned officer has no way to move an issue to the next role, send it backward, or ask the student a question, anywhere in the UI.
- **Affected files:** `frontend/src/api/issues.ts` (no functions), `frontend/src/pages/issues/IssueDetail.tsx` (no buttons/panels).
- **Priority:** Critical (core workflow functionality).
- **Difficulty:** Medium — three new API functions, three new form panels (Send Back and Request Info are single-notes-field forms; Forward additionally needs a `target_role` picker only for the "Other" category, which is dynamic-forward).
- **Dependencies:** None; can be built directly against existing endpoints.

### 2. Student Confirm / Reject Resolution — no UI at all
- **Backend implementation:** `POST /issues/:id/confirm/` (`confirm_resolution`, resolved → closed, student/admin only) and `POST /issues/:id/reject/` (`reject_resolution`, resolved → pending, mandatory explanation, student/admin only).
- **Frontend status:** Missing entirely. No API client functions exist. `IssueDetail.tsx`'s `StatusUpdatePanel` is only rendered when `canManage` is true, and `canManage` explicitly excludes students (`roleGroup !== 'student' && ...`). A student viewing a `resolved` issue sees the read-only "Resolution Notes" card and nothing else — no way to confirm or reject anywhere in the product.
- **Affected files:** `frontend/src/api/issues.ts`, `frontend/src/pages/issues/IssueDetail.tsx`.
- **Priority:** Critical (core workflow functionality — the workflow cannot reach `closed` through the UI for any non-admin user).
- **Difficulty:** Low-Medium — two new API functions, one new panel gated on `isOwner && issue.status === 'resolved'`, with a mandatory explanation textarea for reject.
- **Dependencies:** None.

### 3. "Resolved → Closed" shown to officers who cannot perform it
- **Backend implementation:** `confirm_resolution` requires `_require_student` (student or admin only).
- **Frontend status:** `ALLOWED_STATUS_TRANSITIONS.resolved = ['closed']` is included in the same table `StatusUpdatePanel` uses for the assigned officer's dropdown. A non-admin officer viewing a resolved issue they own (`canManage === true`) sees "Closed" as a selectable status; submitting it will 403 from `_require_student`.
- **Affected files:** `frontend/src/types/index.ts` (`ALLOWED_STATUS_TRANSITIONS`), `frontend/src/pages/issues/IssueDetail.tsx` (`StatusUpdatePanel`).
- **Priority:** High (visible, reachable permission error; classified as a UI Inconsistency below as well).
- **Difficulty:** Low — remove `closed` from the officer-facing transition list once Confirm/Reject (#2) exists as the correct, student-facing path.
- **Dependencies:** #2 (student confirm/reject UI) should land first so "closed" remains reachable at all.

### 4. Extended staff roles cannot be created — 6 of 12 workflow roles are unreachable
- **Backend implementation:** `accounts.constants.ROLE_CHOICES` / `STAFF_ROLE_CHOICES` include 12 non-student roles: `course_adviser`, `hod`, `ict_officer`, `exams_officer`, `student_affairs_officer`, `admin`, plus `department_admin`, `lecturer`, `bursary`, `registry`, `school_admin_office`, `dept_exam_officer` — the last six were added specifically to support the 12-category workflow definitions (`issues/workflow/definitions.py`).
- **Frontend status:** `frontend/src/types/index.ts`'s `Role` type and `STAFF_ROLES` constant only contain the original 6 roles (5 staff roles + admin). `StaffCreate.tsx`'s role `<select>` is built from `STAFF_ROLES`, so an administrator has no way to create a Department Admin, Lecturer, Bursary, Registry, School Admin Office, or Department Examination Officer account anywhere in the UI. Every workflow definition that starts at or routes through one of these six roles (Transcript Request, School Fees Issue, Academic Clearance, Admission Issue, Certificate Collection, Examination Issue, Grade Dispute, Course Registration's registry step, etc.) can never resolve an officer automatically — `find_officer_for_role` will always raise `NoOfficerAvailableError`, and every such issue lands in "Unassigned" permanently until an admin manually assigns it (which itself requires the target user to already exist with that role — impossible without this fix).
- **Affected files:** `frontend/src/types/index.ts` (`Role`, `STAFF_ROLES`, `ROLE_LABELS`), `frontend/src/pages/admin/StaffCreate.tsx` (uses `STAFF_ROLES` for its dropdown, otherwise needs no change).
- **Priority:** Critical — this is the single highest-impact gap in the audit; it silently degrades 8 of the 12 category workflows to "always needs manual assignment."
- **Difficulty:** Low — add the 6 missing role literals/labels to `types/index.ts`; `StaffCreate.tsx` needs no logic changes since it already maps generically over `STAFF_ROLES`.
- **Dependencies:** None. Should be prioritized above almost everything else in this report.

### 5. Required documents are not reliably displayed for an existing issue
- **Backend implementation:** `Category.required_documents()` exists on the model, and `create_issue()` returns the full required-document list once, at creation time. Nothing else on the backend currently returns "what documents does this category require" — `IssueDetailSerializer` only exposes `documents` (documents actually uploaded, via `IssueDocumentSerializer`), not the required set, and the new `GET /api/categories/` (added for the ML picker) returns only `id`/`name`/`department`, no document list.
- **Frontend status:** `lib/documentChecklist.ts`'s `buildDocumentChecklist()` is the fallback used whenever the required-document list isn't available from `location.state` (i.e., every time an issue is opened from `My Issues`/`Assigned Issues`/`All Issues` rather than immediately after creation). It matches `issue.category` (one of the real 12 canonical names) against `listCategories()` from `api/mock/store.ts`, whose 5 seeded categories ("Hostel Room Maintenance", "Library Book Issuance", "Fee Payment Receipt", "Transport Facility", "Exam Result Discrepancy") never match any real category name. The match always fails and the function returns `[]`. **In practice, the "Documents" section on `IssueDetail.tsx` shows no required documents at all for any issue that wasn't just created in the current browser session.**
- **Affected files:** `frontend/src/lib/documentChecklist.ts`, `frontend/src/pages/issues/IssueDetail.tsx`, `frontend/src/pages/student/UploadDocuments.tsx` (same fallback path); backend: `issues/serializers.py` (`IssueDetailSerializer`) would need a `required_documents` field, or `categories/views.py`'s `CategoryListAPIView` would need to include each category's document list.
- **Priority:** High (directly affects the "Required Documents" and "Document Completeness" capabilities the backend already fully supports).
- **Difficulty:** Low on the frontend once a backend source of truth exists; the backend addition itself is small (one more serialized field or list endpoint).
- **Dependencies:** A small backend addition (expose required documents outside of creation-time) is a prerequisite — this cannot be fully fixed frontend-only.

### 6. Status-timeline timestamps use stale activity-action matchers
- **Backend implementation:** The real `IssueActivity.action` strings the workflow engine writes are `"Issue Review Started"`, `"Issue Resolved"`, and `"Issue Closed"` (see `workflow/service.py`).
- **Frontend status:** `lib/timeline.ts`'s `STEP_ORDER` matches those three steps against the regexes `/status changed to in progress/i`, `/status changed to resolved/i`, and `/status changed to closed/i` — action strings that do not exist anywhere in the current backend. The "In Progress", "Resolved", and "Closed" steps in the `StatusStepper` widget on `IssueDetail.tsx` will always show as reached (color/position is driven by `STATUS_RANK`, which is correct) but will never show a timestamp, because the timestamp lookup never matches.
- **Affected files:** `frontend/src/lib/timeline.ts`.
- **Priority:** Medium (cosmetic but consistently wrong — three timestamps permanently blank).
- **Difficulty:** Trivial — update the three regexes to match the real action strings.
- **Dependencies:** None.

### 7. No UI to forward an "Other"-category issue's dynamic target role
- **Backend implementation:** `forward_issue()` requires a `target_role` for the "Other" category (`dynamic_forward=True`) and validates it against every non-student/non-admin role in `ROLE_CHOICES`.
- **Frontend status:** N/A today because Forward has no UI at all (#1). Called out separately because it is not simply "add a Forward button" for this one category — it additionally needs a role picker, and should reuse the same role vocabulary gap noted in #4 (a role dropdown here would currently be missing the same 6 roles unless `types/index.ts` is fixed first).
- **Affected files:** Same as #1, plus depends on #4's role list being complete.
- **Priority:** Medium (only affects the "Other" category, but that category is explicitly part of the specification).
- **Difficulty:** Low, once #1 and #4 exist.
- **Dependencies:** #1, #4.

### 8. Staff directory / role picker not reused for staff-creation department input
- **Backend implementation:** `UserProfile.department_name` is a free-text field (not an FK), matched by exact/case-sensitive string in `workflow/roles.py`'s department-scoped officer lookup.
- **Frontend status:** `StaffCreate.tsx`'s "Department" field is a `<SelectField>` populated from `listDepartments()` (mock `api/mock/store.ts`, 5 seeded departments: "Hostel Administration", "ICT", "Bursary", "Exams & Records", "Transport"), not from any real department source. Since department-scoped role resolution in the workflow engine matches `department_name` by exact string against the student's own profile, a staff account created with a department name that doesn't exactly match a real student's department value will never be found by `find_officer_for_role`. There is no real backend department-listing endpoint to source this from today.
- **Affected files:** `frontend/src/pages/admin/StaffCreate.tsx`.
- **Priority:** Medium-High (directly affects whether department-scoped roles — Course Adviser, HOD, Department Admin, Dept Exam Officer, Lecturer — can ever be correctly matched).
- **Difficulty:** Low on the frontend (swap the data source) once a real department list exists; the department app currently has no real endpoint (`departments/views.py` is the empty Django scaffold) — see Remaining Mock Data.
- **Dependencies:** A real `GET /api/departments/`-equivalent endpoint (does not currently exist).

### 9. No live/derived notification count on the bell icon
- **Backend implementation:** N/A — no notifications endpoint exists; `Notifications.tsx` already derives a real activity feed client-side from `activity_history` across the student's own issues.
- **Frontend status:** `Topbar.tsx`'s bell icon is permanently inert (`title="No live notifications yet"`), even though the same data `Notifications.tsx` already fetches (real `IssueActivity` records) could drive an unread/recent-activity badge.
- **Affected files:** `frontend/src/components/layout/Topbar.tsx`.
- **Priority:** Low (polish).
- **Difficulty:** Low-Medium (needs a read/unread concept, which doesn't exist on the backend yet — could be approximated with a "since last visit" timestamp in local storage).
- **Dependencies:** None strictly, though a true "unread" concept would benefit from a backend flag.

---

## UI Inconsistencies

- **"Closed" offered to non-admin officers who cannot use it** (detailed in Missing Integration #3) — the officer-facing status dropdown presents a transition (`resolved → closed`) that will always be rejected by the backend (`UnauthorizedTransitionError` → 403) for anyone other than an admin, because only the student or an admin may confirm a resolution.
- **Status-timeline timestamps silently blank** (detailed in Missing Integration #6) — the stepper always shows the right steps as "reached," but never shows *when* the officer started review, resolved, or the student closed the issue, because the matching regexes reference action strings the backend no longer (or never did) produce.
- **Required documents silently disappear** (detailed in Missing Integration #5) — a student or officer re-opening an issue from a list view sees an empty "Documents" section (or, on `UploadDocuments.tsx`, an empty upload widget) even when the category genuinely requires documents, because the fallback checklist source (mock categories) can never match a real category name. This looks identical to "this category has no required documents," which is factually wrong for 11 of the 12 canonical categories.
- **No page/route ownership check on issue detail.** Neither the backend (`IssueDetailAPIView.get()` has no ownership or role scoping — any authenticated user can `GET /issues/:id/` for any issue) nor the frontend (`/student/issues/:id` and `/staff/issues/:id` routes render full issue content regardless of `isOwner`/`canManage`) restrict who can view a given issue's full description, documents, and activity notes. `isOwner`/`canManage` in `IssueDetail.tsx` only gate which *action panels* render, not whether the page's data renders at all. This is consistent front-to-back (neither layer restricts it), so it is not a frontend bug relative to the backend, but it is worth flagging: a student can view another student's issue (including personal notes in `resolution_notes`/activity notes) simply by knowing or guessing the numeric ID.
- **`IssueListAPIView` has no per-role scoping** — `GET /issues/` always returns every issue in the system to any authenticated user; "My Issues," "Assigned Issues," and dashboards all filter this same globally-open payload client-side by `student === user.email` / `assigned_to === user.email`. Again, consistent front-to-back, but means the network payload for a student's "My Issues" page contains every other student's issues too.
- **`AllIssues` page is available to every non-student, non-admin role**, not just supervisory ones — `RoleRoute allow={['staff']}` groups all 11 non-student non-admin roles into one "staff" bucket, so e.g. a Bursary officer sees the exact same "All Issues" (including the Unassigned filter) as an HOD. This mirrors the backend's equally-open `IssueListAPIView`, so it is consistent rather than a bug, but is worth noting since "All Issues" was originally described as being for staff needing visibility beyond their own queue.
- **Client-side-only upload restrictions.** `DocumentUploadWidget.tsx` enforces a 10MB size cap and an `.pdf,.jpg,.jpeg,.png` file-picker filter, but `issues/services/document_service.py::upload_document()` performs no size or extension validation at all. A direct API call (or a modified/compromised client) could upload any file type or size; the UI's restriction is cosmetic only, not backed by matching server-side enforcement.

---

## Remaining Mock Data

| Page | Mock source | Real data available? |
|---|---|---|
| `admin/Users.tsx` — "Add User" list/edit/activate/deactivate | `api/mock/store.ts` (`listUsers`/`saveUser`/`setUserActive`) | No general user-management endpoint exists (only staff-creation and staff-directory). Page has an explicit `Alert` disclosing this. |
| `admin/Departments.tsx` — full CRUD | `api/mock/store.ts` (`listDepartments`/`saveDepartment`) | No department endpoint exists (`departments/views.py` is the empty scaffold). Page has an explicit `Alert` disclosing this. |
| `admin/Categories.tsx` — full CRUD | `api/mock/store.ts` (`listCategories`/`saveCategory`), **5 legacy categories that do not match the real 12** | Partially — `GET /api/categories/` (real, read-only, id/name/department) exists now (added for the ML picker) but this page doesn't use it, and it has no document-list or write support. Page has an explicit `Alert` disclosing the mock status, but does not disclose that the category *names* shown no longer match the real database at all. |
| `admin/DocumentTypes.tsx` — full CRUD | `api/mock/store.ts` (`listDocumentTypes`/`saveDocumentType`) | No document-type endpoint exists (`documents_app/views.py` is the empty scaffold). Page has an explicit `Alert` disclosing this. |
| `admin/StaffCreate.tsx` — Department dropdown only (account creation itself is real) | `api/mock/store.ts` (`listDepartments`) | No, same as above. |
| `admin/Departments.tsx` (assigned-officer picker) / `admin/Categories.tsx` (staff list for future use) | `api/mock/store.ts` (`listUsers`) | Partially — `GET /accounts/staff/directory/` is real and already used elsewhere (`ManualAssignPanel`), but not reused here. |
| `admin/Dashboard.tsx` / `reports/Reports.tsx` — "Total Users" and "Departments"/"Total Categories" stat cards | `api/mock/store.ts` via `getAdminOverview()` (`total_users`, `total_departments`) | Partially — `total_issues`, `open_issues`, and the status/department/trend breakdowns in the same `getAdminOverview()`/`getIssueTrend()`/`getDepartmentSummaries()` are already real (derived from `listIssues()`); only the raw user/department counts fall back to the mock store. |
| `lib/documentChecklist.ts` (used by `IssueDetail.tsx` and `UploadDocuments.tsx` fallback path) | `api/mock/store.ts` (`listCategories`) | See Missing Integration #5 — effectively non-functional against real data today. |
| `profile/Profile.tsx` | Not mock, but structurally limited — only fields present in the login response render; department/matric/staff-ID/level show as "Not tracked" for a real session since no `/api/accounts/me/` endpoint exists. Explicitly disclosed via an `Alert`. | No `/me/` endpoint exists. |

---

## Remaining Legacy Behaviour

- **`ALLOWED_STATUS_TRANSITIONS` frontend table models a status-only view of the workflow that predates the workflow engine.** Its own comment says it "mirrors `issues.services.status_service.ALLOWED_TRANSITIONS` exactly," but that variable no longer exists — `status_service.py` was refactored to delegate to the workflow engine and now exposes a `_HANDLERS` dict covering only `in_progress`/`resolved`/`closed`. The frontend table happens to still list the same three destinations, but the underlying rationale it cites is stale, and — as covered above — it doesn't (and structurally can't) represent forward/send-back/request-info/reject, which are the workflow engine's other four transitions.
- **The legacy `PATCH /issues/:id/status/` endpoint is the only transition path wired into the frontend**, even though the backend has since grown five purpose-built workflow endpoints (`/start/`, `/forward/`, `/send-back/`, `/request-info/`, `/resolve/`, `/confirm/`, `/reject/` — `/start/` and `/resolve/` happen to also be reachable via the legacy endpoint's `in_progress`/`resolved` values, but the rest are not). The frontend was never updated to adopt the newer, more expressive endpoints.
- **`admin/Categories.tsx`'s seeded mock categories are a pre-category-alignment artifact** — they reflect an older, informal category vocabulary from before the `categories_category` table was migrated to the 12 canonical, ML-classifier-aligned names. The page's own copy ("keep them aligned with what's seeded in Django") is no longer true.
- **`Role`/`STAFF_ROLES` in `types/index.ts` predate the 12-category workflow rollout** — they were never extended when `accounts/constants.py` grew from 7 to 13 roles to support the new workflow definitions (see Missing Integration #4).

---

## Recommended Implementation Order

**Phase 1 — Core functionality (unblocks the workflow entirely):**
1. Add the 6 missing roles to `types/index.ts` (`Role`, `STAFF_ROLES`, `ROLE_LABELS`) — Missing Integration #4. Nothing else in the workflow can be meaningfully tested end-to-end without staff who hold these roles existing.
2. Build Forward / Send Back / Request Information UI + API client functions — Missing Integration #1.
3. Build Student Confirm / Reject Resolution UI + API client functions — Missing Integration #2.

**Phase 2 — Workflow correctness (fixes incorrect/misleading behavior once Phase 1 exists):**
4. Remove "Closed" from the officer-facing status dropdown now that Confirm/Reject has its own correct, student-facing path — Missing Integration #3.
5. Add the "Other" category's dynamic target-role picker to the new Forward UI — Missing Integration #7 (depends on #2 above from this list, i.e. Phase 1 item 2, and the completed role list from item 1).
6. Fix the status-timeline regex matchers to the real `IssueActivity.action` strings — Missing Integration #6.
7. Resolve required-documents display for existing issues — Missing Integration #5. Requires a small backend addition (expose required documents via `IssueDetailSerializer` or the categories endpoint) before the frontend fix is possible.

**Phase 3 — Administrative functionality:**
8. Source `StaffCreate.tsx`'s department field from a real department list once one exists — Missing Integration #8 (blocked on a backend department-listing endpoint that does not exist today).
9. Real category management (`admin/Categories.tsx`) — replace the 5 legacy mock categories with the real, canonical 12 (read is already possible via `GET /api/categories/`; write support does not exist on the backend yet).
10. Real department management (`admin/Departments.tsx`) and document-type management (`admin/DocumentTypes.tsx`) — both fully blocked on backend endpoints that don't exist yet.
11. Real general user management (`admin/Users.tsx`) — same, blocked on a backend endpoint.
12. Replace `total_users`/`total_departments` mock counts on `admin/Dashboard.tsx` and `Reports.tsx` once real user/department listing endpoints exist (naturally falls out of #10/#11).

**Phase 4 — UX improvements (already-supported-by-backend polish):**
13. Live/derived notification badge on the topbar bell, reusing the same activity data `Notifications.tsx` already fetches — Missing Integration #9.
14. Reuse the real staff directory (`GET /accounts/staff/directory/`) instead of the mock user list wherever a staff picker appears outside `ManualAssignPanel` (e.g. `admin/Departments.tsx`'s assigned-officer field).

**Phase 5 — Cosmetic polish:**
15. Match client-side document upload restrictions (file size/type) to whatever the backend actually enforces (currently nothing) — either add backend validation or clearly label the frontend restriction as a UX convenience, not a hard rule.
16. Add a documents-required preview to the ML confirm/manual-selection stages of `CreateIssue.tsx`, matching the preview the old mock-based flow used to show (would require the categories endpoint to also return each category's document list).

---

## Permissions Summary (Section 8)

| Action | Backend enforcement | Frontend representation |
|---|---|---|
| Manual assignment | `IsSystemAdmin` + `manual_assign_officer` admin check | Correctly hidden unless `user?.role === 'admin'` |
| Forward / Send Back / Resolve / Request Info | `_require_assigned_officer` (assigned officer or admin) | N/A — no UI exists yet (see Missing Integration #1) |
| Confirm / Reject Resolution | `_require_student` (issue's own student or admin) | N/A — no UI exists yet (see Missing Integration #2); the one place a transition *is* offered (`resolved → closed` in `StatusUpdatePanel`) is incorrectly shown to non-admin officers, who will always be rejected |
| View issue detail | No restriction at all (any authenticated user) | No restriction added on top — matches backend, but likely unintended from a privacy standpoint |
| List issues | No restriction at all (any authenticated user) | No restriction added on top — client-side filtering only, not real scoping |
| Staff account creation | `IsSystemAdmin` | Correctly hidden/route-guarded to `/admin/*` (`RoleRoute allow={['admin']}`) |
| Staff directory | `IsSystemAdmin` | Only ever called from within the admin-gated `ManualAssignPanel` |

No case was found where the frontend is *more* restrictive than the backend (i.e., hiding something a role is actually allowed to do). All identified gaps are either missing affordances (action not exposed at all) or affordances shown to users who will be rejected server-side.
