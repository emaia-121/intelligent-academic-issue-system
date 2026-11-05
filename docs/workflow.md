# Workflow Reference

This document reflects the workflow actually implemented in the repository today. The current system is not based on a category’s owning department alone; it is driven by the backend workflow engine in `backend/issues/workflow/definitions.py` and `backend/issues/workflow/service.py`.

## 1. Canonical workflow categories

The project currently defines the following 12 canonical issue categories:

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

These names are the ones used by both the workflow engine and the category alignment migration.

## 2. Status model and transitions

The actual status choices on `Issue` are:

- `pending`
- `ready_for_review`
- `in_progress`
- `resolved`
- `closed`

The backend enforces this transition graph:

| Current status | Allowed next statuses |
| --- | --- |
| `pending` | `ready_for_review` |
| `ready_for_review` | `in_progress` |
| `in_progress` | `ready_for_review`, `pending`, `resolved` |
| `resolved` | `closed`, `pending` |
| `closed` | none |

Invalid transitions are rejected by the workflow engine.

## 3. Workflow engine architecture

The workflow engine is declarative. A category does not have custom logic written in an if/else chain; it has a `WorkflowDefinition` object with:

- `starting_role`
- `forward_chain`
- `backward_transitions`
- `final_authority_roles`
- `required_documents`
- `dynamic_forward` (used for `Other`)

The engine resolves the next or previous officer using `find_officer_for_role()`, which uses:

- central-role lookup for institution-wide roles
- department-scoped lookup for academic department roles

The key point is that workflow behaviour is backend-owned and follows the category definition, not a collection of frontend rules.

## 4. Category-to-workflow summary

| Category | Starting role | Fixed flow | Final authority |
| --- | --- | --- | --- |
| Missing Result | Course Adviser | Course Adviser → Department Admin → HOD → Exams Officer | Course Adviser, Exams Officer |
| Grade Dispute | Course Adviser | Course Adviser → Lecturer | Course Adviser |
| Course Registration | Course Adviser | Course Adviser → Exams Officer | Course Adviser |
| Transcript Request | Department Admin | Department Admin → HOD → Exams Officer | Exams Officer |
| School Fees Issue | Bursary | Bursary | Bursary |
| Academic Clearance | Department Admin | Department Admin → HOD | Department Admin |
| Admission Issue | School Admin Office | School Admin Office | School Admin Office |
| Certificate Collection | Registry | Registry → Bursary | Bursary |
| Examination Issue | Department Examination Officer | Department Examination Officer → HOD → Exams Officer | Department Examination Officer, Exams Officer |
| Portal/System Issue | ICT Officer | ICT Officer | ICT Officer |
| Student Welfare | Student Affairs Officer | Student Affairs Officer | Student Affairs Officer |
| Other | HOD | Dynamic forward | HOD |

## 5. Assignment and routing rules

### Initial assignment

`perform_initial_assignment()` resolves the category’s `starting_role` and assigns the issue to an available officer if one exists. If no officer is available, the issue is created and left with `assigned_to = null`, and a system `IssueActivity` log explains why.

This is the only place where the issue is intentionally left unassigned in the normal workflow.

### Forwarding

`forward_issue()` reassigns the issue to the next role in the category’s fixed chain, or to a manually chosen `target_role` when the category is `Other`.

### Send-back

`send_back_issue()` moves the issue to a prior role via the category’s `backward_transitions` map.

### Final resolution

Only roles in the category’s `final_authority_roles` may resolve an issue. This is enforced in the backend.

## 6. Department-scoped vs central routing

The workflow engine distinguishes:

- `CENTRAL_ROLES`: institution-wide roles looked up without department scoping
- `DEPARTMENT_SCOPED_ROLES`: roles resolved against the issue’s student department

Examples:

- Central: ICT Officer, Exams Officer, Registry, Bursary, School Administration Office, Student Affairs Officer
- Department-scoped: Course Adviser, HOD, Department Admin, Department Examination Officer, Lecturer

The key implementation is in `backend/issues/workflow/roles.py` and not in the frontend.

## 7. Document flow

The document lifecycle is:

1. issue created with required documents determined by category
2. student uploads the required files
3. `check_issue_completeness()` compares required document names to uploaded `IssueDocument` rows
4. when all required documents are uploaded and the issue is pending, it is moved to `ready_for_review`
5. the workflow may then start with the assigned officer

This is currently the actual implementation in `backend/issues/services/document_service.py`.

## 8. Workflow action endpoints

These endpoints are active in the repository:

- `GET /api/issues/`
- `POST /api/issues/create/`
- `POST /api/issues/<id>/upload-document/`
- `POST /api/issues/<id>/start/`
- `POST /api/issues/<id>/forward/`
- `POST /api/issues/<id>/send-back/`
- `POST /api/issues/<id>/request-info/`
- `POST /api/issues/<id>/resolve/`
- `POST /api/issues/<id>/confirm/`
- `POST /api/issues/<id>/reject/`
- `POST /api/issues/<id>/assign/`

These actions are the real workflow API surface and are more accurate than the older generic status-only design.

## 9. Activity examples currently generated by the backend

The workflow engine creates entries such as:

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

The precise strings are not abstract placeholders; they are the actual action values written by the service code.

## 10. Important limitations

- The frontend uses `roleWorkloadConfig.ts` as a display mirror of backend workflow definitions, not as a backend source of truth.
- The `Department` model is not the live workflow routing authority.
- Department-scoped role lookup depends on `UserProfile.department_name`, which is a free-text field in the current implementation.
- There is no categories-by-role API endpoint; the frontend config is manually synchronized with the backend model.
- The issue list endpoint does not perform role-aware system aggregation; it is a broad fetch that dashboards filter client-side.

## 11. Current workflow summary

The actual operational flow is:

1. student creates an issue
2. backend predicts or resolves the category
3. backend runs the category’s workflow definition
4. backend assigns the issue to the starting role if an officer exists
5. student uploads required documents
6. issue becomes `ready_for_review` when complete
7. officer starts review and proceeds through the category workflow
8. the issue is forwarded, sent back, or resolved according to the backend workflow definition
9. student confirms or rejects the resolution as the final step before closure
