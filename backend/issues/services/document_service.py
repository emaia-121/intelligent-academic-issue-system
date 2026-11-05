from issues.models import (
    Issue,
    IssueDocument,
    IssueActivity
)

from documents_app.models import Document

def check_issue_completeness(issue):

    required_docs = issue.category.documents.all()

    uploaded_doc_ids = IssueDocument.objects.filter(
        issue=issue
    ).values_list(
        'document_id',
        flat=True
    )

    missing_documents = []

    for doc in required_docs:

        if doc.id not in uploaded_doc_ids:
            missing_documents.append(doc.name)

    is_complete = len(missing_documents) == 0

    return {
        "is_complete": is_complete,
        "missing_documents": missing_documents
    }

def upload_document(
    issue_id,
    document_id,
    file,
    user=None
):
    try:

        issue = Issue.objects.get(
            id=issue_id
        )

    except Issue.DoesNotExist:

        raise ValueError(
            "Issue not found."
        )

    # Closed issues cannot be modified except by system administrators
    # (fixed status rule enforced by the workflow engine -- see
    # issues/workflow/service.py). `user` is optional and defaults to None
    # only to stay backward compatible with any other existing caller of
    # this function; when it is None the upload is treated as non-admin
    # and blocked, which is the safe default for a closed issue.
    profile = getattr(user, "userprofile", None) if user is not None else None
    is_admin = bool(profile and profile.role == "admin")

    if issue.status == "closed" and not is_admin:

        raise ValueError(
            "This issue is closed. Closed issues cannot be modified "
            "except by system administrators."
        )

    try:
        document = Document.objects.get(
            id=document_id
        )

    except Document.DoesNotExist:

        raise ValueError(
            "Required document not found."
        )

    existing_upload = IssueDocument.objects.filter(
        issue=issue,
        document=document
    ).first() 
    
    if existing_upload:
        
        existing_upload.file = file
        existing_upload.save()
        
        issue_document = existing_upload
        
    else:
        
        issue_document = IssueDocument.objects.create(
            issue=issue,
            document=document,
            file=file
        )

    IssueActivity.objects.create(
        issue=issue,
        action="Document Uploaded",
        performed_by=issue.student, 
        notes=f"{document.name} uploaded"
    ) 

    completeness_result = check_issue_completeness(
        issue
    )

    issue.is_complete = completeness_result[
        "is_complete"
    ]

    # Only auto-advance to "ready_for_review" when the issue was actually
    # waiting on the student (status == "pending"). This is the same
    # transition point whether the student is completing a brand new
    # issue's checklist for the first time, responding to an officer's
    # "request more information" (In Progress -> Pending), or uploading
    # optional evidence after rejecting a resolution (Resolved -> Pending)
    # -- in every case "pending" is what they're clearing. Previously this
    # flip fired unconditionally, so re-uploading/replacing a document
    # while an issue was e.g. In Progress or Resolved would silently yank
    # it back to "ready_for_review" and away from whoever currently owned
    # it, which conflicts with the workflow engine's ownership rules (see
    # issues/workflow/service.py). This is the minimal change needed to
    # make this existing side effect consistent with those rules.
    became_ready = issue.status == "pending" and issue.is_complete

    if became_ready:

        issue.status = "ready_for_review"

    issue.save()

    if became_ready:

        IssueActivity.objects.create(
            issue=issue,
            action="Issue Ready For Review",
            performed_by=None,
            is_system_action=True,
            notes="All required documents submitted"
        )

    return {
        
        "issue_id": issue.id,
        
        "document_uploaded": document.name,
        
        "is_complete": issue.is_complete,
        
        "status": issue.status,
        
        "missing_documents": completeness_result[
            
            "missing_documents"
        ]
    }