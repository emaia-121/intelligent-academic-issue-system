"""
Declarative per-category workflow definitions.

This module is the single source of truth for "where should an issue of
category X go next" -- the question the workflow engine
(issues/workflow/service.py) answers. It intentionally contains no branching
business logic beyond simple lookups: every category's forward chain,
backward transitions, and final authority is data, not code, so adjusting a
category's routing never requires touching the engine itself, and there is
no giant if/else block anywhere mapping category -> destination.

IMPORTANT -- category name matching against the real database:
Categories here are keyed by the exact 12 category names given in the
project's workflow specification -- the same 12 names used to train the
ML classifier (ml/model_config.py) and the same 12 names now seeded as
the only rows in categories_category (see
categories/migrations/0005_align_to_canonical_categories.py, which
renamed/merged the database's earlier, informally-named rows into exactly
this vocabulary). The engine still deliberately does NOT try to guess or
fuzzy-match a Category row to one of these 12 definitions: if
issue.category.name has no exact entry here, engine functions raise
WorkflowNotConfiguredError rather than silently applying the wrong
workflow. That should not happen for any of the 12 canonical categories
in normal operation -- it's a safety net for if a category is ever
renamed again in the database without a matching change here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

from accounts.constants import (
    ROLE_COURSE_ADVISER,
    ROLE_HOD,
    ROLE_ICT_OFFICER,
    ROLE_EXAMS_OFFICER,
    ROLE_STUDENT_AFFAIRS_OFFICER,
    ROLE_DEPARTMENT_ADMIN,
    ROLE_LECTURER,
    ROLE_BURSARY,
    ROLE_REGISTRY,
    ROLE_SCHOOL_ADMIN_OFFICE,
    ROLE_DEPT_EXAM_OFFICER,
)


@dataclass(frozen=True)
class WorkflowDefinition:
    category_name: str
    starting_role: str
    forward_chain: Sequence[str]
    backward_transitions: Mapping[str, str]
    final_authority_roles: frozenset
    required_documents: Sequence[str]
    # True only for "Other": there is no fixed forward chain, the
    # first-receiving HOD chooses the forward destination at runtime.
    dynamic_forward: bool = False

    def next_role(self, current_role: str) -> Optional[str]:
        """Role that should receive the issue after `current_role` in this
        category's fixed forward chain, or None if `current_role` is
        already the last stage (the officer must resolve, not forward)."""
        if self.dynamic_forward:
            return None
        chain = list(self.forward_chain)
        try:
            index = chain.index(current_role)
        except ValueError:
            return None
        if index + 1 < len(chain):
            return chain[index + 1]
        return None

    def previous_role(self, current_role: str) -> Optional[str]:
        """Role that `current_role` may send the issue back to, per this
        category's explicit backward transitions -- or None if this
        category defines no backward transition from this role."""
        return self.backward_transitions.get(current_role)

    def is_final_authority(self, role: str) -> bool:
        return role in self.final_authority_roles

    def involves_role(self, role: str) -> bool:
        """Whether `role` is a legitimate participant anywhere in this
        category's workflow (used to sanity-check that an issue's current
        assignee actually belongs to this category's workflow before
        attempting to route it further)."""
        return (
            role in self.forward_chain
            or role in self.backward_transitions
            or role in self.backward_transitions.values()
            or role in self.final_authority_roles
            or role == self.starting_role
        )


WORKFLOW_DEFINITIONS = {

    "Missing Result": WorkflowDefinition(
        category_name="Missing Result",
        starting_role=ROLE_COURSE_ADVISER,
        forward_chain=(ROLE_COURSE_ADVISER, ROLE_DEPARTMENT_ADMIN, ROLE_HOD, ROLE_EXAMS_OFFICER),
        backward_transitions={ROLE_HOD: ROLE_COURSE_ADVISER},
        final_authority_roles=frozenset({ROLE_COURSE_ADVISER, ROLE_EXAMS_OFFICER}),
        required_documents=(
            "Course Registration Slip",
            "School Fees Receipt",
            "Result Printout (if available)",
        ),
    ),

    "Grade Dispute": WorkflowDefinition(
        category_name="Grade Dispute",
        starting_role=ROLE_COURSE_ADVISER,
        forward_chain=(ROLE_COURSE_ADVISER, ROLE_LECTURER),
        backward_transitions={ROLE_LECTURER: ROLE_COURSE_ADVISER},
        final_authority_roles=frozenset({ROLE_COURSE_ADVISER}),
        required_documents=(
            "Course Registration Slip",
            "School Fees Receipt",
            "Result Printout (if available)",
        ),
    ),

    "Course Registration": WorkflowDefinition(
        category_name="Course Registration",
        starting_role=ROLE_COURSE_ADVISER,
        forward_chain=(ROLE_COURSE_ADVISER, ROLE_EXAMS_OFFICER),
        backward_transitions={ROLE_EXAMS_OFFICER: ROLE_COURSE_ADVISER},
        final_authority_roles=frozenset({ROLE_COURSE_ADVISER}),
        required_documents=(
            "Course Form Printout",
            "School Fees Receipt",
        ),
    ),

    "Transcript Request": WorkflowDefinition(
        category_name="Transcript Request",
        starting_role=ROLE_DEPARTMENT_ADMIN,
        forward_chain=(ROLE_DEPARTMENT_ADMIN, ROLE_HOD, ROLE_EXAMS_OFFICER),
        backward_transitions={},
        final_authority_roles=frozenset({ROLE_EXAMS_OFFICER}),
        required_documents=(
            "Transcript Request Form Slip",
            "Transcript Request Letter",
            "Stamped Payment Receipt",
        ),
    ),

    "School Fees Issue": WorkflowDefinition(
        category_name="School Fees Issue",
        starting_role=ROLE_BURSARY,
        forward_chain=(ROLE_BURSARY,),
        backward_transitions={},
        final_authority_roles=frozenset({ROLE_BURSARY}),
        required_documents=(
            "Remita Payment Printout",
            "Error Message Printout",
            "Student ID Card",
        ),
    ),

    # Modelled as Department Admin -> HOD (forward chain) with HOD ->
    # Department Admin as the one backward transition. This deliberately
    # covers the spec's literal "Department Admin -> HOD -> Department
    # Admin" chain: once HOD sends it back to Department Admin (the
    # backward transition below), Department Admin -- who is also this
    # category's sole final authority -- resolves it. A forward chain
    # that lists "Department Admin" twice was avoided because
    # next_role()/previous_role() assume each role appears at most once in
    # forward_chain; backward_transitions + final_authority_roles already
    # expresses the identical routing without that ambiguity, and without
    # needing a new "current stage" field on Issue.
    "Academic Clearance": WorkflowDefinition(
        category_name="Academic Clearance",
        starting_role=ROLE_DEPARTMENT_ADMIN,
        forward_chain=(ROLE_DEPARTMENT_ADMIN, ROLE_HOD),
        backward_transitions={ROLE_HOD: ROLE_DEPARTMENT_ADMIN},
        final_authority_roles=frozenset({ROLE_DEPARTMENT_ADMIN}),
        required_documents=(
            "Clearance Form",
            "Academic Payment Receipts",
        ),
    ),

    "Admission Issue": WorkflowDefinition(
        category_name="Admission Issue",
        starting_role=ROLE_SCHOOL_ADMIN_OFFICE,
        forward_chain=(ROLE_SCHOOL_ADMIN_OFFICE,),
        backward_transitions={},
        final_authority_roles=frozenset({ROLE_SCHOOL_ADMIN_OFFICE}),
        required_documents=(
            "Admission Letter",
            "JAMB Result Printout",
            "WAEC/NECO Result Printout",
        ),
    ),

    "Certificate Collection": WorkflowDefinition(
        category_name="Certificate Collection",
        starting_role=ROLE_REGISTRY,
        forward_chain=(ROLE_REGISTRY, ROLE_BURSARY),
        backward_transitions={},
        final_authority_roles=frozenset({ROLE_BURSARY}),
        required_documents=(
            "Dues Payment Receipts",
            "Certificate Request Letter",
        ),
    ),

    "Examination Issue": WorkflowDefinition(
        category_name="Examination Issue",
        starting_role=ROLE_DEPT_EXAM_OFFICER,
        forward_chain=(ROLE_DEPT_EXAM_OFFICER, ROLE_HOD, ROLE_EXAMS_OFFICER),
        backward_transitions={
            ROLE_HOD: ROLE_DEPT_EXAM_OFFICER,
            ROLE_EXAMS_OFFICER: ROLE_DEPT_EXAM_OFFICER,
        },
        final_authority_roles=frozenset({ROLE_DEPT_EXAM_OFFICER, ROLE_EXAMS_OFFICER}),
        required_documents=(
            "Duly Addressed Letter",
            "Student ID Card",
        ),
    ),

    "Portal/System Issue": WorkflowDefinition(
        category_name="Portal/System Issue",
        starting_role=ROLE_ICT_OFFICER,
        forward_chain=(ROLE_ICT_OFFICER,),
        backward_transitions={},
        final_authority_roles=frozenset({ROLE_ICT_OFFICER}),
        required_documents=(
            "Error Message Printout",
            "Student Portal Login Details",
            "Student ID Card",
        ),
    ),

    "Student Welfare": WorkflowDefinition(
        category_name="Student Welfare",
        starting_role=ROLE_STUDENT_AFFAIRS_OFFICER,
        forward_chain=(ROLE_STUDENT_AFFAIRS_OFFICER,),
        backward_transitions={},
        final_authority_roles=frozenset({ROLE_STUDENT_AFFAIRS_OFFICER}),
        required_documents=(
            "School Fees Receipt",
            "Student ID Card",
            "Relevant Payment Receipt",
        ),
    ),

    # "Other" is intentionally dynamic: HOD is always the first receiver,
    # and may either resolve directly or forward to whatever office is
    # actually appropriate for the issue. There is no fixed forward_chain
    # to hardcode a destination into -- see service.forward_issue()'s
    # target_role handling, used only when dynamic_forward is True.
    "Other": WorkflowDefinition(
        category_name="Other",
        starting_role=ROLE_HOD,
        forward_chain=(),
        backward_transitions={},
        final_authority_roles=frozenset({ROLE_HOD}),
        required_documents=(),
        dynamic_forward=True,
    ),
}


# Roles resolved without reference to any particular department: looked up
# institution-wide via UserProfile.role alone.
CENTRAL_ROLES = frozenset({
    ROLE_ICT_OFFICER,
    ROLE_EXAMS_OFFICER,
    ROLE_BURSARY,
    ROLE_REGISTRY,
    ROLE_SCHOOL_ADMIN_OFFICE,
    ROLE_STUDENT_AFFAIRS_OFFICER,
})

# Roles that only make sense scoped to a specific academic department (a
# Course Adviser only supervises students from their own department, etc).
# Resolved via UserProfile.department_name -- see workflow/roles.py.
DEPARTMENT_SCOPED_ROLES = frozenset({
    ROLE_COURSE_ADVISER,
    ROLE_HOD,
    ROLE_DEPARTMENT_ADMIN,
    ROLE_DEPT_EXAM_OFFICER,
    ROLE_LECTURER,
})


def get_workflow_definition(category_name: str) -> WorkflowDefinition:
    """Look up the WorkflowDefinition for a category by name.

    Raises WorkflowNotConfiguredError (imported lazily to avoid a circular
    import with exceptions.py) if no exact match exists.
    """
    from issues.workflow.exceptions import WorkflowNotConfiguredError

    definition = WORKFLOW_DEFINITIONS.get(category_name)
    if definition is None:
        raise WorkflowNotConfiguredError(
            f"No workflow is configured for category {category_name!r}. "
            f"Configured categories: {sorted(WORKFLOW_DEFINITIONS)}."
        )
    return definition
