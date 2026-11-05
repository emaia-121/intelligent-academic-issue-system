# Department Architecture Review

This document reflects the department architecture currently implemented in the repository, not an ideal future state.

## Current model

The current `Department` model is defined in `backend/departments/models.py` and contains:

- `name` (`CharField`, unique)
- `description` (`TextField`, optional)
- `kind` (`academic` or `administrative`)
- `assigned_officer` (`ForeignKey(User)`, nullable, optional)

This model exists, but it is not the live routing authority for issue assignment.

## How departments are used today

### `Category.department`

`Category.department` is a real `ForeignKey` to `Department`. It is used as informational metadata and is displayed alongside categories. It is not used by the workflow engine to determine who should receive an issue.

### `Department.assigned_officer`

`Department.assigned_officer` exists in the schema, but the workflow engine does not read it. The current backend assignment logic is based on role resolution, not on a one-officer-per-department assumption.

### `UserProfile.department_name`

This is the field that actually matters for department-scoped routing. In `backend/accounts/models.py`, students and staff are assigned a free-text `department_name`. The workflow resolver uses this field for roles such as:

- `course_adviser`
- `hod`
- `department_admin`
- `dept_exam_officer`
- `lecturer`

The backend does not use `Category.department` for that lookup.

## Why this matters

The system moved away from a legacy department-driven assignment model. The live routing logic is structured around role workflow definitions, and the department-scoped roles are matched against the issue’s student’s academic department through `UserProfile.department_name`.

This means the real architecture is:

- category defines the workflow
- workflow defines starting role and forwarding path
- role resolution chooses the actual officer
- department-scoped roles additionally consider the student’s own department

The `Department` table is not the source of truth for workflow routing.

## Current department data architecture

The database-backed department catalogue contains workflow-oriented operational units such as:

- Bursary Office
- Department of Computer Science
- Exams and Records Unit
- ICT Unit
- Registry
- School Admin Office
- Student Affairs Office

This is not the older mock department catalogue. The project has already moved to a more operational department architecture and seeded the canonical categories accordingly.

## Relationship between academic departments and operational departments

There is a meaningful distinction in the current implementation:

- `Category.department` is a category’s administrative owner or operational association
- `UserProfile.department_name` is the person’s actual academic department or department affiliation
- role routing uses the latter for department-scoped roles

The project therefore does not treat the legacy mock “department catalogue” as the authoritative workflow structure.

## Key current limitations

### 1. `UserProfile.department_name` is a string field

This makes department-scoped routing dependent on exact text matching, which is weaker than a foreign-key-backed department reference.

### 2. The model and workflow logic are not fully aligned

The `Department` model and the live workflow routing do not share the same source of truth. The backend route logic is role-driven and not unquestionably coupled to the `Department` table.

### 3. The frontend cannot always prove department-specific availability

The admin dashboard’s “Unassigned Issues by Role” feature can determine system-wide role coverage using `GET /api/accounts/staff/directory/`, but it cannot always determine whether a specific department-scoped role is available inside that student’s department because the issue list shape does not expose the department context required for that exact check.

## Current status

The project’s department architecture is currently in a hybrid state:

- the `Department` model exists and is used as metadata and category ownership
- role-based workflow routing is the actual runtime authority
- the route logic still depends on `UserProfile.department_name`
- there is no fully authoritative real department API that drives all account and routing decisions today

This is a real limitation of the current implementation, and the documentation reflects it rather than treating the old mock department model as active truth.
