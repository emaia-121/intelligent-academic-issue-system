# This module used to contain its own, independent status-transition
# table (ALLOWED_TRANSITIONS) and authorization logic, entirely separate
# from the workflow engine added in issues/workflow/. That would have left
# two different, inconsistent code paths capable of changing an issue's
# status -- in particular, the old logic let the assigned officer move an
# issue straight from "resolved" to "closed" themselves, which conflicts
# with the workflow specification's fixed status meanings ("closed" means
# the *student* confirmed the resolution; ownership stays with the officer
# until then).
#
# change_issue_status() is kept (same name, same signature, same calling
# convention from issues/views.py::StatusUpdateAPIView) so the existing
# `PATCH /issues/<id>/status/` endpoint keeps working, but it now delegates
# every status it handles to the workflow engine (issues/workflow/service.py)
# instead of re-implementing transition/authorization rules here. This is
# the "no workflow logic scattered across views/services" rule applied to
# this pre-existing entry point too, since leaving it as its own parallel
# implementation would not "strictly" support the workflow -- it would
# actively undermine it.
#
# New, more expressive workflow actions that don't fit this endpoint's
# simple {status, notes} shape (forwarding, backward routing, requesting
# more information, and student confirm/reject) are exposed through the
# new dedicated endpoints added to issues/views.py + issues/urls.py, which
# call issues/workflow/service.py directly.

from issues.workflow import service as workflow_service
from issues.workflow.exceptions import WorkflowError


_HANDLERS = {
    "in_progress": lambda issue, user, notes: workflow_service.start_review(issue, user),
    "resolved": lambda issue, user, notes: workflow_service.resolve_issue(issue, user, notes),
    "closed": lambda issue, user, notes: workflow_service.confirm_resolution(issue, user),
}


def change_issue_status(
    issue,
    user,
    new_status,
    notes=None
):
    handler = _HANDLERS.get(new_status)

    if handler is None:
        raise ValueError(
            f"'{new_status}' cannot be set through this endpoint. "
            f"Supported values here: {sorted(_HANDLERS)}. Forwarding, "
            f"sending an issue back, requesting more information, and "
            f"rejecting a resolution each have their own dedicated "
            f"endpoint."
        )

    try:
        result = handler(issue, user, notes)
    except WorkflowError as exc:
        # WorkflowError subclasses ValueError/PermissionError as
        # appropriate (see issues/workflow/exceptions.py), so this
        # re-raise keeps the existing `except PermissionError` /
        # `except ValueError` handling in issues/views.py working
        # unchanged.
        raise exc

    return {"status": result["status"]}
