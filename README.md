# Student Issue Management System

## Current system snapshot

This repository now implements a workflow-driven academic issue-routing system rather than a generic issue tracker with a simpler category-to-department assignment. The backend owns the routing decisions; the frontend presents the current role-aware views and dashboards but does not determine workflow behaviour.

The current implementation includes:

- Django REST API with Django auth, JWT, and custom profile roles
- 12 canonical issue categories and a workflow engine in `backend/issues/workflow/`
- Role-aware issue assignment and forwarding using workflow definitions
- Issue document requirements and completeness checking
- Issue activity/audit trails
- ML category prediction during issue creation, without persisting prediction confidence/metadata
- React + TypeScript frontend with student, staff, and admin route groups
- A single reusable staff dashboard driven by the authenticated user's real role

## Tech stack

- Python / Django / Django REST Framework
- SQLite for the current local database
- SimpleJWT for token-based auth
- React + TypeScript + Vite
- React Router for route protection and role-group routing

## Current architecture in one sentence

The system evolved from a generic issue-management concept into a role-based academic workflow engine where issue categories map to workflow definitions, each workflow has a starting role and fixed or dynamic forwarding rules, and the backend resolves the next officer by role and, where needed, by the student’s own department.

## Repository truth: current backend responsibilities

### Backend apps and real responsibilities

- `backend/accounts`: `UserProfile`, auth-related serializers, role constants, and staff directory logic
- `backend/issues`: issues, documents, workflow engine, serializers, views, and issue activity
- `backend/categories`: category catalogue and required-document relationships
- `backend/departments`: department model and admin metadata, but not the live workflow-routing authority
- `backend/ml`: ML classifier and model configuration
- `backend/student_issue_system`: project URL routing

### Real issue workflow model

Issues are created without a direct department-based assignment. Instead:

1. the issue is created with a `Category`
2. the workflow engine resolves the category’s `starting_role`
3. it finds a suitable officer via `find_officer_for_role()`
4. it logs the assignment via `IssueActivity`
5. issue status and workflow actions proceed through the category-specific route

This means the real assignment logic is backend-driven in `backend/issues/workflow/service.py` and `backend/issues/workflow/roles.py`, not in the frontend.

## Current role system

The system currently includes these real role values:

- `student`
- `course_adviser`
- `hod`
- `department_admin`
- `dept_exam_officer`
- `lecturer`
- `ict_officer`
- `exams_officer`
- `registry`
- `bursary`
- `school_admin_office`
- `student_affairs_officer`
- `admin`

Frontend route groups collapse these into three broad groups:

- `student`: student routes and dashboard
- `staff`: all non-student, non-admin roles share the staff route group
- `admin`: admin routes and dashboard

This is not the same as the real backend role values. The staff dashboard reads the actual `UserProfile.role` and applies a role-specific configuration to display the relevant workload.

## Current workflow engine

The current canonical workflow categories are:

- Missing Result
- Grade Dispute
- Course Registration
- Transcript Request
- School Fees Issue
- Academic Clearance
- Admission Issue
- Certificate Collection
- Examination Issue
- Portal/System Issue
- Student Welfare
- Other

These are backed by `WORKFLOW_DEFINITIONS` in `backend/issues/workflow/definitions.py`.

Role routing is split into:

- `CENTRAL_ROLES`: roles looked up institution-wide
- `DEPARTMENT_SCOPED_ROLES`: roles looked up against the student’s own `UserProfile.department_name`

Important routing facts:

- `starting_role` is the first role for each category
- `forward_chain` defines the fixed forward path for most categories
- `backward_transitions` define send-back behaviour
- `final_authority_roles` define who may resolve the issue
- `Other` is the only dynamic-forward category; the HOD decides the target role at runtime
- `assigned_to` is only left null during the initial assignment exception path when the workflow cannot resolve a starting officer
- forwarding and send-back do not intentionally clear `assigned_to`; they raise if the target officer cannot be resolved

## Document requirement and completeness logic

Document requirements are attached to categories via the `Category.documents` many-to-many field. The document service checks the issue’s required documents against uploaded `IssueDocument` rows and calculates:

- `is_complete`
- `missing_documents`
- transition to `ready_for_review` when the issue was previously `pending` and all required documents are now present

This is implemented in `backend/issues/services/document_service.py` and the `Issue` model in `backend/issues/models.py`.

## Issue activity/audit trail

`IssueActivity` records issue events, including:

- `Issue Created`
- `Automatically Assigned`
- `Issue Manually Assigned`
- `Document Uploaded`
- `Issue Review Started`
- `Issue Ready For Review`
- `Issue Forwarded`
- `Issue Sent Back`
- `Issue Resolved`
- `Issue Closed`
- other workflow-specific actions created by the engine

`is_system_action` distinguishes system-generated actions from user-triggered actions.

## Authentication and roles

The current app uses Django auth with a custom `UserProfile` linked 1:1 to the Django user.

Current auth flow in the repo:

- Student registration: `POST /api/accounts/register/`
- Staff creation: `POST /api/accounts/staff/`
- Login: `POST /api/accounts/login/`
- Token endpoints: `/api/token/` and `/api/token/refresh/` still exist in the Django project, but the application’s login flow is email-based via `EmailLoginView`
- `must_change_password` is stored on the profile and enforced by the frontend route guard until a password change is completed

## Frontend architecture

The frontend is React + TypeScript + Vite with role-group route protection.

Key structure:

- `frontend/src/App.tsx`: route tree and role-group gates
- `frontend/src/routes/ProtectedRoute.tsx`: authentication and role-group checks
- `frontend/src/components/layout/AppShell.tsx`: shell with sidebar and topbar
- `frontend/src/components/layout/Sidebar.tsx`: `NAV_BY_ROLE` for student/staff/admin
- `frontend/src/components/layout/Topbar.tsx`: top navigation and user info
- `frontend/src/pages/student/Dashboard.tsx`: student dashboard
- `frontend/src/pages/staff/Dashboard.tsx`: reusable role-aware staff dashboard
- `frontend/src/pages/admin/Dashboard.tsx`: admin overview with unassigned-by-role view
- `frontend/src/pages/reports/Reports.tsx`: shared reports view

The staff dashboard is intentionally not 11 duplicated components. It reads the actual user role and applies a configuration mirror from `frontend/src/lib/roleWorkloadConfig.ts`.

## Staff dashboard redesign

The implemented redesign is a single reusable staff dashboard that:

- reads the authenticated user’s real role
- identifies the workload relevant to that role
- filters assigned issues by the user’s email
- limits the visible category set using the frontend config
- displays role-specific workload information without having 11 separate screen components

The config is a projection of the backend workflow definitions and is intentionally not treated as the backend source of truth. It must stay synchronized with `issues/workflow/definitions.py` because there is no dedicated “categories by role” API endpoint.

## Admin dashboard changes

The admin dashboard includes an “Unassigned Issues by Role” section. It works by combining:

- `GET /api/issues/?unassigned=true`
- `GET /api/accounts/staff/directory/`
- `CATEGORY_STARTING_ROLE` from `frontend/src/lib/roleWorkloadConfig.ts`

This lets the frontend explain which workflow role should have received an unassigned issue, and whether staff exist for that role. The dashboard does not assign officers or route issues; it only displays the workflow state.

## Department architecture today

The current `Department` model exists, but it is not the live routing authority.

The actual routing logic uses `UserProfile.department_name` and role resolution, not `Department.assigned_officer` or `Category.department`.

The database-backed department catalogue has operational units such as:

- Bursary Office
- Department of Computer Science
- Exams and Records Unit
- ICT Unit
- Registry
- School Admin Office
- Student Affairs Office

This is different from the earlier generic mock department catalogue. The project moved away from treating old mock departments as authoritative routing data.

## ML classification status

The current ML implementation is real but limited:

- category prediction is used during issue creation
- high-confidence predictions can create the issue immediately
- medium-confidence predictions require confirmation
- low-confidence predictions require manual category selection
- the prediction is not persisted on the issue model as confidence, category source, or classification metadata
- no ML metrics endpoint is currently implemented from real persisted data

This must be distinguished from future ML analytics work.

## Backend/frontend data boundaries

The current data boundaries are important:

- Workflow routing and assignment are backend-driven.
- Frontend dashboards fetch issue data and do some client-side filtering and aggregation.
- The issue list endpoint returns a broad set of issues; there is no dedicated dashboard aggregation endpoint.
- The staff directory endpoint provides role availability data.
- Some admin and user dashboard statistics are computed client-side from these returned records.

This is workable for the repository’s current scale, but it is not a backend analytics system and it does not replace the workflow engine.

## Current scope and deferred work

### Implemented

- workflow-driven issue lifetime
- category-based required documents
- role-aware workflow routing and assignment
- issue activity logging
- role-aware staff dashboard redesign
- admin unassigned-by-role overview
- document completeness and ready-for-review transition

### Partially implemented

- department architecture and department data sources are still inconsistent between the model and the actual workflow lookup logic
- some dashboard statistics remain derived client-side from broad issue-fetch patterns

### Deferred / not implemented

- 11 separate staff dashboard components
- new backend dashboard statistics endpoints just for charts
- `can_resolve` enhancement on the issue serializer
- ML analytics metrics that require persisted classification metadata
- mock dashboard metrics presented as real data

## Architecture decisions / development pivots

The repo shows several real decisions that matter:

- moved away from generic mock department data as the routing authority
- introduced workflow-driven assignment in the backend
- introduced role-aware staff dashboards
- reused one parametrized staff dashboard instead of 11 duplicated dashboards
- kept workflow authority on the backend, not the frontend
- avoided creating unnecessary new dashboard endpoints for simple client-side calculations
- deferred ML analytics until classification metadata can be persisted
- skipped the optional `can_resolve` backend enhancement

## Documentation note

This README reflects the implementation that exists in the repository today. Older documentation that described a simpler department-based or mock-driven architecture is not treated as authoritative unless it matches the current code.

```json
{
  "success": false,
  "message": "You do not have permission to update this issue.",
  "errors": null
}
```

### Validation Error

```json
{
  "success": false,
  "message": "Validation failed.",
  "errors": {
    "status": [
      "This field is required."
    ]
  }
}
```

## Project Structure

The backend is organized into the following major apps:

- `accounts/` – user and profile management
- `issues/` – issue lifecycle, documents, status updates, activities, and API views
- `categories/` – issue categories and their required documents
- `departments/` – departments and their assigned officers
- `documents_app/` – reusable document definitions used by issue submissions

### Responsibilities

- `models/` define the database schema for users, issues, documents, categories, departments, and activity history.
- `serializers/` validate incoming request data and shape outgoing API responses.
- `services/` contain the core business logic for issue creation, document uploads, completeness checks, and status transitions.
- `views/` expose the API endpoints and coordinate request handling.
- `utils/` provide common response helpers for successful and error responses.

## Current Backend Workflow

The end-to-end backend workflow is as follows:

Student Login
↓
Create Issue
↓
Automatic Department Routing
↓
Upload Required Documents
↓
Completeness Check
↓
Ready For Review
↓
Assigned Officer Reviews
↓
Status Updates
↓
Activity History Recorded

## Future Work

The following features are planned for future development and are not part of the current implementation:

- Frontend implementation
- Machine Learning issue classification
- TF-IDF feature extraction
- Naive Bayes classifier
- Confidence threshold
- Rule-based fallback classification
- Notifications
- Search and filtering
- Analytics dashboard

## Code Quality

This documentation reflects the current backend implementation and replaces the earlier placeholder-style project information. The backend uses a service-oriented structure, consistent API response formatting, and explicit status workflow handling to keep the system maintainable and easy to extend.
