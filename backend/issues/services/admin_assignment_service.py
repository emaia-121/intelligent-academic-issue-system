"""
Administrative Assignment Management.

This is the service layer behind the admin-only "manually assign this
issue" feature. It exists specifically to manage workflow *exceptions* --
issues the workflow engine's own automatic assignment
(issues.workflow.service.perform_initial_assignment) could not resolve an
officer for, and left with assigned_to = None.

It is NOT a second assignment mechanism. It resolves the two IDs a view
hands it (which Issue, which User) into real model instances, then
delegates the actual state change to
issues.workflow.service.manual_assign_officer() -- the one function in the
codebase (alongside perform_initial_assignment, forward_issue, and
send_back_issue, all in that same module) allowed to write
Issue.assigned_to. This mirrors the same split already used by
issues.services.issue_service.create_issue(): resolve IDs here, delegate
the actual assignment decision/write to the workflow engine.
"""

from django.contrib.auth.models import User

from issues.models import Issue
from issues.workflow import service as workflow_service


def manually_assign_issue(issue_id, admin_user, officer_id, notes=None):
    try:
        issue = Issue.objects.select_related(
            "category", "student", "assigned_to"
        ).get(id=issue_id)
    except Issue.DoesNotExist:
        raise ValueError("Issue not found.")

    try:
        officer = User.objects.get(id=officer_id)
    except User.DoesNotExist:
        raise ValueError("Selected officer not found.")

    result = workflow_service.manual_assign_officer(
        issue,
        admin_user,
        officer,
        notes=notes,
    )

    return {
        "issue_id": issue.id,
        "status": result["status"],
        "assigned_to": result["assigned_to"],
    }
