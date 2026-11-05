"""
Resolves "which User currently holds role R for this issue" -- the
question every forward/backward/dynamic-forward move in the workflow
engine needs answered before it can reassign an issue.

Two lookup strategies, chosen per role (see definitions.CENTRAL_ROLES /
DEPARTMENT_SCOPED_ROLES):

- Central roles (ICT Officer, Exams Officer, Bursary, Registry, School
  Admin Office, Student Affairs Officer) are looked up institution-wide:
  the first UserProfile with that role, since these offices are singular
  and not tied to any particular academic department.

- Department-scoped roles (Course Adviser, HOD, Department Admin,
  Department Examination Officer, Lecturer) only make sense relative to a
  specific academic department, so they are looked up scoped to the
  ISSUE'S STUDENT's own department (UserProfile.department_name) -- not
  issue.category.department. Those are different things in the existing
  data: Category.department identifies which office ultimately *owns*
  that category (e.g. "Missing Result" -> Exams and Records Unit in the
  current database), not the student's academic home department. A
  Course Adviser only supervises students from their own department, so
  scoping by Category.department would frequently try to find a Course
  Adviser inside an administrative unit like "Exams and Records Unit",
  where none would ever exist by design.

No new model or field was needed for this lookup: UserProfile.department_name
is an existing free-text field already populated for department-scoped
staff and students alike in the current database, so this uses only what
was already there.
"""

from __future__ import annotations

import random

from django.db.models import Count, Q

from typing import Optional

from accounts.models import UserProfile
from issues.workflow.definitions import CENTRAL_ROLES, DEPARTMENT_SCOPED_ROLES
from issues.workflow.exceptions import NoOfficerAvailableError, WorkflowError


def get_role_for_user(user) -> Optional[str]:
    """UserProfile.role for `user`, or None if they have no profile / are
    None (e.g. an unassigned issue)."""
    if user is None:
        return None
    profile = getattr(user, "userprofile", None)
    return profile.role if profile else None


def get_student_department_name(issue) -> Optional[str]:
    profile = getattr(issue.student, "userprofile", None)
    return profile.department_name if profile else None


def find_officer_for_role(role: str, issue):
    """Find an active officer for the workflow role.

    Officers are scoped by role and, where applicable, by the student's
    department. Among eligible active officers, the officer with the fewest
    active assigned issues is selected. If multiple officers have the same
    lowest workload, one is selected at random.

    Raises NoOfficerAvailableError if no active officer is eligible.
    """

    active_statuses = [
        "pending",
        "ready_for_review",
        "in_progress",
        "resolved",
    ]

    if role in CENTRAL_ROLES:
        profiles = list(
            UserProfile.objects
            .filter(
                role=role,
                user__is_active=True,
            )
            .select_related("user")
            .annotate(
                active_issue_count=Count(
                    "user__assigned_issues",
                    filter=Q(
                        user__assigned_issues__status__in=active_statuses
                    ),
                    distinct=True,
                )
            )
        )

        if not profiles:
            raise NoOfficerAvailableError(
                f"No active staff member currently holds the {role!r} role."
            )

    elif role in DEPARTMENT_SCOPED_ROLES:
        department_name = get_student_department_name(issue)

        if not department_name:
            raise NoOfficerAvailableError(
                f"Cannot route this issue to a {role!r}: the student's "
                f"department is not set on their profile."
            )

        profiles = list(
            UserProfile.objects
            .filter(
                role=role,
                department_name=department_name,
                user__is_active=True,
            )
            .select_related("user")
            .annotate(
                active_issue_count=Count(
                    "user__assigned_issues",
                    filter=Q(
                        user__assigned_issues__status__in=active_statuses
                    ),
                    distinct=True,
                )
            )
        )

        if not profiles:
            raise NoOfficerAvailableError(
                f"No active staff member holding the {role!r} role was found "
                f"in the {department_name!r} department."
            )

    else:
        raise WorkflowError(
            f"Role {role!r} is not classified as either a central or a "
            f"department-scoped role. Add it to CENTRAL_ROLES or "
            f"DEPARTMENT_SCOPED_ROLES in issues/workflow/definitions.py."
        )

    minimum_workload = min(
        profile.active_issue_count for profile in profiles
    )

    least_loaded = [
        profile
        for profile in profiles
        if profile.active_issue_count == minimum_workload
    ]

    selected_profile = random.choice(least_loaded)

    return selected_profile.user 