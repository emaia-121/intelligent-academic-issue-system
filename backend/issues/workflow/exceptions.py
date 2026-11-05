"""
Exception hierarchy for the workflow engine (issues/workflow/).

Mirrors the pattern already used by ml/classifier.py elsewhere in this
project: a common base exception plus specific, catchable subclasses, so
callers (views, tests) can decide how to respond to each failure mode
instead of catching a bare Exception. Each subclass also inherits from the
closest built-in exception type so existing exception-handling code (e.g.
`except ValueError` / `except PermissionError` blocks already present in
issues/views.py) keeps working without modification.
"""


class WorkflowError(Exception):
    """Base class for every workflow-engine-raised error."""


class WorkflowNotConfiguredError(WorkflowError, LookupError):
    """Raised when an issue's category has no matching WorkflowDefinition
    in issues/workflow/definitions.py. This happens when
    issue.category.name does not exactly match one of the 12 canonical
    category names from the workflow specification -- the engine never
    guesses or falls back to a default workflow."""


class InvalidTransitionError(WorkflowError, ValueError):
    """Raised when the requested move is not legal from the issue's
    current state: either the status graph forbids it (e.g. Closed ->
    In Progress, Pending -> Closed, Resolved -> Ready For Review), or this
    category's forward/backward routing has no such move defined."""


class UnauthorizedTransitionError(WorkflowError, PermissionError):
    """Raised when the acting user is not allowed to perform this
    transition on this issue (e.g. someone other than the assigned
    officer trying to forward it, or someone other than the issue's own
    student trying to confirm/reject a resolution)."""


class NoOfficerAvailableError(WorkflowError, LookupError):
    """Raised when no staff member with the required role (and, where
    applicable, department) could be found to route the issue to. The
    engine never leaves an issue silently unassigned or guesses a
    fallback officer."""


class MissingExplanationError(WorkflowError, ValueError):
    """Raised when a mandatory explanation/notes field was not supplied
    (e.g. rejecting a resolution without an explanation, resolving an
    issue without resolution notes, requesting more information without
    saying what is needed)."""
