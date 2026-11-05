from issues.models import Issue, IssueActivity
from categories.models import Category
from issues.workflow import service as workflow_service


def create_issue(student, category_id, title, description):

    try:
        category = Category.objects.get(
            id=category_id
        )

    except Category.DoesNotExist:

        raise ValueError(
            "Category not found."
        )

    # Issue is created with no assignee at all. Who receives it first is a
    # routing decision, and the workflow engine (issues/workflow/service.py)
    # is the single owner of every routing decision in this system -- there
    # is no longer a second, separate assignment mechanism living here.
    issue = Issue.objects.create(
        student=student,
        category=category,
        title=title,
        description=description
    )

    IssueActivity.objects.create(
        issue=issue,
        action="Issue Created",
        performed_by=student
    )

    # Delegate the first assignment to the workflow engine. It reads this
    # category's WorkflowDefinition.starting_role (issues/workflow/definitions.py)
    # and resolves the actual officer via the same role-resolution logic
    # every subsequent forward/backward move uses (issues/workflow/roles.py),
    # then records the "Automatically Assigned" activity itself. If nothing
    # can be assigned yet (unconfigured category, or nobody currently holds
    # the starting role), it leaves the issue unassigned and records why --
    # it does not raise, so issue creation always succeeds.
    workflow_service.perform_initial_assignment(issue)

    required_docs = category.required_documents()

    checklist = [
        {
            "document_id": doc.id,
            "document_name": doc.name
        }
        for doc in required_docs
    ]

    return {
        "issue_id": issue.id,
        "title": issue.title,
        "category": category.name,
        "assigned_to": issue.assigned_to.username if issue.assigned_to else None,
        "required_documents": checklist
    }
