"""
The workflow engine.

This module is the single place that decides "where should this issue go
next" -- it never decides "what category is this issue" (that is the ML
classifier's job, in ml/classifier.py, and this module never imports or
calls into it). Views and other services must not implement any of this
logic themselves; they call these functions and translate the result (or
a raised exception) into an HTTP response.

Fixed status vocabulary (unchanged from Issue.STATUS_CHOICES -- no new
statuses are introduced):

    ready_for_review  All required documents supplied, waiting for the
                       assigned officer to begin. Nobody has started yet.
    in_progress        The assigned officer is actively handling it.
                       Ownership belongs to that officer.
    pending             ALWAYS means waiting for the student. Never means
                       waiting for an officer.
    resolved            The officer has completed the issue; the student
                       must review the outcome. Ownership still belongs to
                       the officer until the student responds.
    closed              The student confirmed the resolution. The
                       workflow has ended. Closed issues cannot be
                       modified except by system administrators.

STATUS_TRANSITIONS below is the status-level legality graph (is X -> Y
ever allowed, independent of category). Each public function additionally
enforces the category-specific routing rules (from
issues/workflow/definitions.py) and who is allowed to trigger it. A move
must pass both checks.

Reassignment convention: whenever an issue changes hands between two
different officers (forward_issue, send_back_issue), the new officer has
not started work yet, so the issue goes to 'ready_for_review' -- exactly
the same state a freshly created issue is in once its required documents
are complete. The new officer must explicitly call start_review() to move
to 'in_progress', mirroring the very first assignment. This is a
deliberate, uniform rule (not special-cased per category) that follows
directly from the fixed definition of 'ready_for_review' above.

Assignment ownership: this module is the only place in the codebase that
ever sets Issue.assigned_to -- perform_initial_assignment() for the first
officer, forward_issue()/send_back_issue() for every officer after that.
There is deliberately no second assignment mechanism (issue creation used
to assign via Category.department.assigned_officer directly; it no longer
does -- see issues/services/issue_service.py).
"""

from __future__ import annotations

from accounts.constants import ROLE_CHOICES, ROLE_ADMIN, ROLE_STUDENT
from issues.models import Issue, IssueActivity
from issues.workflow.definitions import get_workflow_definition
from issues.workflow.exceptions import (
    InvalidTransitionError,
    MissingExplanationError,
    NoOfficerAvailableError,
    UnauthorizedTransitionError,
    WorkflowNotConfiguredError,
)
from issues.workflow.roles import find_officer_for_role, get_role_for_user

_ROLE_LABELS = dict(ROLE_CHOICES)


def _role_label(role):
    if not role:
        return "Unassigned"
    return _ROLE_LABELS.get(role, role)


# --------------------------------------------------------------------------
# Status-level transition graph
# --------------------------------------------------------------------------

STATUS_TRANSITIONS = {
    "pending": frozenset({"ready_for_review"}),
    "ready_for_review": frozenset({"in_progress"}),
    "in_progress": frozenset({"ready_for_review", "pending", "resolved"}),
    "resolved": frozenset({"closed", "pending"}),
    "closed": frozenset(),
}


def validate_status_transition(current_status, new_status):
    """Pure status-graph check, independent of category/role/authorization.

    Rejects, among others, the three explicitly invalid examples from the
    workflow specification: Closed -> In Progress, Pending -> Closed, and
    Resolved -> Ready For Review (none of these appear as an allowed edge
    above).
    """
    allowed = STATUS_TRANSITIONS.get(current_status, frozenset())
    if new_status not in allowed:
        raise InvalidTransitionError(
            f"Cannot move an issue from "
            f"'{current_status}' to '{new_status}'."
        )


# --------------------------------------------------------------------------
# Authorization helpers
# --------------------------------------------------------------------------

def _is_admin(user):
    profile = getattr(user, "userprofile", None)
    return bool(profile and profile.role == ROLE_ADMIN)


def _require_not_closed_unless_admin(issue, user):
    if issue.status == "closed" and not _is_admin(user):
        raise InvalidTransitionError(
            "This issue is closed. Closed issues cannot be modified "
            "except by system administrators."
        )


def _require_assigned_officer(issue, user):
    """The acting user must be the officer currently holding the issue,
    or an admin."""
    if _is_admin(user):
        return
    if issue.assigned_to is not None and user == issue.assigned_to:
        return
    raise UnauthorizedTransitionError(
        "Only the officer currently assigned to this issue may perform "
        "this action."
    )


def _require_student(issue, user):
    """The acting user must be the student who raised the issue, or an
    admin."""
    if _is_admin(user):
        return
    if user == issue.student:
        return
    raise UnauthorizedTransitionError(
        "Only the student who raised this issue may perform this action."
    )


def _current_role(issue, definition):
    role = get_role_for_user(issue.assigned_to)
    if role is None or not definition.involves_role(role):
        raise InvalidTransitionError(
            "The officer currently assigned to this issue does not "
            f"belong to the '{issue.category.name}' workflow, so the "
            "next step cannot be determined."
        )
    return role


# --------------------------------------------------------------------------
# Public workflow operations
# --------------------------------------------------------------------------

def perform_initial_assignment(issue):
    """Assign the first officer to a freshly created issue.

    This is the initial-assignment counterpart to forward_issue() /
    send_back_issue(): it reads the category's WorkflowDefinition.starting_role
    (the same declarative data every other engine operation reads from
    issues/workflow/definitions.py -- nothing new is defined here) and
    resolves it to a User via the same find_officer_for_role() every
    forward/backward move uses. The engine is now the single place that
    ever sets Issue.assigned_to; issue creation itself (see
    issues/services/issue_service.py) no longer touches assignment at all.

    Deliberately does not raise for the two "nothing to assign" cases,
    matching how this behaved before the workflow engine owned it (an
    issue whose Category.department had no assigned_officer was still
    created, just left unassigned):

      - WorkflowNotConfiguredError: issue.category.name has no matching
        WorkflowDefinition. Should not happen for any of the 12 canonical
        categories in normal operation.
      - NoOfficerAvailableError: the starting role's officer couldn't be
        resolved (no staff hold that role yet, or, for a department-scoped
        starting role, the student's own department has nobody in that
        role).

    Both cases leave the issue created, with assigned_to still None, and
    record why via a system IssueActivity entry instead of silently doing
    nothing -- consistent with "never silently fail" everywhere else in
    this module. Any other exception (e.g. a role misclassified in neither
    CENTRAL_ROLES nor DEPARTMENT_SCOPED_ROLES) is a genuine configuration
    bug and is allowed to propagate.

    Returns the assigned User, or None if nothing could be assigned.
    """
    try:
        definition = get_workflow_definition(issue.category.name)
    except WorkflowNotConfiguredError as exc:
        IssueActivity.objects.create(
            issue=issue,
            action="Automatic Assignment Skipped",
            performed_by=None,
            is_system_action=True,
            notes=str(exc),
        )
        return None

    starting_role = definition.starting_role

    try:
        officer = find_officer_for_role(starting_role, issue)
    except NoOfficerAvailableError as exc:
        IssueActivity.objects.create(
            issue=issue,
            action="Automatic Assignment Skipped",
            performed_by=None,
            is_system_action=True,
            notes=str(exc),
        )
        return None

    issue.assigned_to = officer
    issue.save()

    IssueActivity.objects.create(
        issue=issue,
        action="Automatically Assigned",
        performed_by=None,
        is_system_action=True,
        notes=f"Assigned to {officer.username} ({_role_label(starting_role)}).",
    )

    return officer


def manual_assign_officer(issue, user, officer, notes=None):
    """Administrative extension point: assign an officer to an issue that
    automatic assignment (perform_initial_assignment) could not resolve on
    its own.

    This exists for exactly one situation -- a workflow exception, i.e. an
    issue whose assigned_to is still None because no one currently holds
    the category's starting role. It is deliberately NOT a general
    "reassign to anyone, anytime" tool: an issue that already has an
    assigned officer participating in its category's workflow must keep
    moving through forward_issue()/send_back_issue() (which validate the
    move against WorkflowDefinition), not through this function. That
    restriction is enforced below, not left to the caller's judgement.

    Restricted to administrators only -- this is exception handling, not a
    normal workflow transition a regular officer would ever perform, so it
    does not reuse _require_assigned_officer()/_require_student() (which
    both permit the acting officer/student, not just admins).

    Like perform_initial_assignment(), this never touches `status` --  a
    manually assigned issue is left in whatever status it already had
    (typically 'pending' or 'ready_for_review', exactly as an
    automatically assigned issue would be). The assigned officer must
    still explicitly call start_review() before doing anything else, and
    from that point on participates in the workflow exactly like any
    other assignment -- forward_issue(), send_back_issue(), resolve_issue()
    etc. all read the officer's UserProfile.role the same way regardless
    of whether perform_initial_assignment() or manual_assign_officer() put
    them there. There is no separate workflow path for a manually
    assigned issue.
    """
    if not _is_admin(user):
        raise UnauthorizedTransitionError(
            "Only a system administrator may manually assign an issue."
        )

    if issue.assigned_to is not None:
        raise InvalidTransitionError(
            "This issue is already assigned. Use forward/send-back to "
            "move it between officers instead of manual assignment."
        )

    profile = getattr(officer, "userprofile", None)
    if profile is None or profile.role == ROLE_STUDENT:
        raise InvalidTransitionError(
            "The selected user is not a staff member and cannot be "
            "assigned an issue."
        )

    issue.assigned_to = officer
    issue.save()

    IssueActivity.objects.create(
        issue=issue,
        action="Issue Manually Assigned",
        performed_by=user,
        notes=(
            f"Manually assigned to {officer.username} ({_role_label(profile.role)})."
            + (f" {notes}" if notes else "")
        ),
    )

    return {"status": issue.status, "assigned_to": officer.username}


def start_review(issue, user):
    """ready_for_review -> in_progress. The assigned officer begins work."""
    _require_not_closed_unless_admin(issue, user)
    _require_assigned_officer(issue, user)
    validate_status_transition(issue.status, "in_progress")

    issue.status = "in_progress"
    issue.save()

    IssueActivity.objects.create(
        issue=issue,
        action="Issue Review Started",
        performed_by=user,
        notes=(
            f"{issue.assigned_to.username} began working on this issue."
            if issue.assigned_to else None
        ),
    )

    return {
        "status": issue.status,
        "assigned_to": issue.assigned_to.username if issue.assigned_to else None,
    }


def forward_issue(issue, user, notes=None, target_role=None):
    """in_progress -> ready_for_review, reassigned to the next role in the
    issue's category workflow.

    `target_role` is required (and only used) when the category's
    workflow is dynamic (currently only "Other"): the current officer
    (always the HOD for "Other") picks any legitimate staff role as the
    destination. For every other, fixed-chain category, `target_role`
    must not be supplied -- the destination is determined entirely by the
    category's forward_chain.
    """
    _require_not_closed_unless_admin(issue, user)
    _require_assigned_officer(issue, user)
    validate_status_transition(issue.status, "ready_for_review")

    definition = get_workflow_definition(issue.category.name)
    current_role = _current_role(issue, definition)

    if definition.dynamic_forward:
        if not target_role:
            raise InvalidTransitionError(
                f"'{issue.category.name}' has no fixed forward chain; "
                "you must specify which role/office to forward this "
                "issue to."
            )
        valid_roles = {role for role, _ in ROLE_CHOICES if role not in (ROLE_STUDENT, ROLE_ADMIN)}
        if target_role not in valid_roles:
            raise InvalidTransitionError(f"'{target_role}' is not a recognised staff role.")
        if target_role == current_role:
            raise InvalidTransitionError(
                "Cannot forward an issue to the same role that currently holds it."
            )
        next_role = target_role
    else:
        if target_role:
            raise InvalidTransitionError(
                f"'{issue.category.name}' has a fixed forward chain; a "
                "target role must not be specified."
            )
        next_role = definition.next_role(current_role)
        if next_role is None:
            raise InvalidTransitionError(
                f"{_role_label(current_role)} is already the final stage "
                f"of the '{issue.category.name}' workflow. Resolve the "
                "issue instead of forwarding it."
            )

    next_officer = find_officer_for_role(next_role, issue)

    previous_role_label = _role_label(current_role)
    issue.assigned_to = next_officer
    issue.status = "ready_for_review"
    issue.save()

    IssueActivity.objects.create(
        issue=issue,
        action="Issue Forwarded",
        performed_by=user,
        notes=(
            f"Forwarded from {previous_role_label} to {_role_label(next_role)}."
            + (f" {notes}" if notes else "")
        ),
    )

    return {"status": issue.status, "assigned_to": next_officer.username}


def send_back_issue(issue, user, notes=None):
    """in_progress -> ready_for_review, reassigned to the previous role
    per this category's explicit backward transitions."""
    _require_not_closed_unless_admin(issue, user)
    _require_assigned_officer(issue, user)
    validate_status_transition(issue.status, "ready_for_review")

    definition = get_workflow_definition(issue.category.name)
    current_role = _current_role(issue, definition)

    target_role = definition.previous_role(current_role)
    if target_role is None:
        raise InvalidTransitionError(
            f"'{issue.category.name}' has no backward transition defined "
            f"from {_role_label(current_role)}."
        )

    target_officer = find_officer_for_role(target_role, issue)

    previous_role_label = _role_label(current_role)
    issue.assigned_to = target_officer
    issue.status = "ready_for_review"
    issue.save()

    IssueActivity.objects.create(
        issue=issue,
        action="Issue Returned",
        performed_by=user,
        notes=(
            f"Returned from {previous_role_label} to {_role_label(target_role)}."
            + (f" {notes}" if notes else "")
        ),
    )

    return {"status": issue.status, "assigned_to": target_officer.username}


def request_more_information(issue, user, notes):
    """in_progress -> pending. Ownership never changes.
    The issue waits for the student to provide additional information.
    """
    if not notes or not notes.strip():
        raise MissingExplanationError(
            "You must explain what information is needed from the student."
        )

    _require_not_closed_unless_admin(issue, user)
    _require_assigned_officer(issue, user)
    validate_status_transition(issue.status, "pending")

    issue.information_request = notes.strip()
    issue.student_information_response = None
    issue.status = "pending"
    issue.save()

    IssueActivity.objects.create(
        issue=issue,
        action="Additional Information Requested",
        performed_by=user,
        notes=notes.strip(),
    )

    return {
        "status": issue.status,
        "assigned_to": issue.assigned_to.username if issue.assigned_to else None,
        "information_request": issue.information_request,
    }

def submit_additional_information(issue, user, response):
    """pending -> ready_for_review. Only the issue's own student may
    submit the requested information. The assigned officer remains
    unchanged.
    """
    if not response or not response.strip():
        raise MissingExplanationError(
            "You must provide the requested information before submitting."
        )

    _require_not_closed_unless_admin(issue, user)
    _require_student(issue, user)
    validate_status_transition(issue.status, "ready_for_review")

    if not issue.information_request:
        raise InvalidTransitionError(
            "This issue does not have an outstanding information request."
        )

    issue.student_information_response = response.strip()
    issue.status = "ready_for_review"
    issue.save()

    IssueActivity.objects.create(
        issue=issue,
        action="Additional Information Submitted",
        performed_by=user,
        notes=response.strip(),
    )

    return {
        "status": issue.status,
        "assigned_to": issue.assigned_to.email if issue.assigned_to else None,
        "student_information_response": issue.student_information_response,
    }

def resolve_issue(issue, user, notes):
    """in_progress -> resolved. Only a final authority role for this
    category may resolve. Ownership does not change -- the officer keeps
    the issue until the student confirms or rejects the resolution."""
    if not notes or not notes.strip():
        raise MissingExplanationError(
            "Resolution notes are required before resolving an issue."
        )
    _require_not_closed_unless_admin(issue, user)
    _require_assigned_officer(issue, user)
    validate_status_transition(issue.status, "resolved")

    definition = get_workflow_definition(issue.category.name)
    current_role = _current_role(issue, definition)

    if not definition.is_final_authority(current_role):
        authorities = ", ".join(_role_label(r) for r in sorted(definition.final_authority_roles))
        raise InvalidTransitionError(
            f"{_role_label(current_role)} is not a final authority for "
            f"'{issue.category.name}' and cannot resolve this issue. "
            f"Final authority: {authorities}."
        )

    issue.status = "resolved"
    issue.resolution_notes = notes
    issue.save()

    IssueActivity.objects.create(
        issue=issue,
        action="Issue Resolved",
        performed_by=user,
        notes=notes,
    )

    return {"status": issue.status, "resolution_notes": issue.resolution_notes}


def confirm_resolution(issue, user):
    """resolved -> closed. Only the issue's own student (or an admin) may
    confirm. This ends the workflow."""
    _require_not_closed_unless_admin(issue, user)
    _require_student(issue, user)
    validate_status_transition(issue.status, "closed")

    issue.status = "closed"
    issue.save()

    IssueActivity.objects.create(
        issue=issue,
        action="Issue Closed",
        performed_by=user,
        notes="Student confirmed the resolution.",
    )

    return {"status": issue.status}


def reject_resolution(issue, user, explanation):
    """resolved -> pending, with a mandatory student explanation. The
    assigned officer stays exactly the same and the issue does not
    restart -- only the status changes. Optional supporting documents (if
    the student has any) are attached separately via the existing
    document upload endpoint; that endpoint's pending -> ready_for_review
    auto-transition (see issues/services/document_service.py) is what
    ultimately returns this issue to the officer, matching the same
    "student uploads -> Ready For Review -> officer picks up again"
    round trip used for additional-information requests."""
    if not explanation or not explanation.strip():
        raise MissingExplanationError(
            "You must explain why the resolution is not accepted before "
            "the issue can be reopened."
        )
    _require_not_closed_unless_admin(issue, user)
    _require_student(issue, user)
    validate_status_transition(issue.status, "pending")

    issue.status = "pending"
    issue.save()

    IssueActivity.objects.create(
        issue=issue,
        action="Student Rejected Resolution",
        performed_by=user,
        notes=explanation,
    )

    return {
        "status": issue.status,
        "assigned_to": issue.assigned_to.username if issue.assigned_to else None,
    }
