# Service Layer Reference

The current implementation uses a small service layer to keep business logic out of the API views.

## 1. Service Summary

| Service function | Purpose |
| --- | --- |
| create_issue | Creates a new issue, assigns it to an officer, and returns required documents |
| check_issue_completeness | Determines whether all required documents have been uploaded |
| upload_document | Stores an uploaded document and updates issue completeness/status |
| change_issue_status | Validates and applies issue status transitions |

## 2. create_issue

### Purpose
Creates a new issue and records the initial activity.

### Parameters
- student: Django User instance representing the student who submitted the issue
- category_id: integer ID of the Category
- title: issue title
- description: issue description

### Return value
A dictionary with:
- issue_id
- title
- category
- assigned_to
- required_documents

### Models used
- Category
- Issue
- IssueActivity

### Business rules enforced
- The category must exist.
- The category’s department’s assigned officer is used as the initial assignee if present.
- A new IssueActivity entry is created for “Issue Created”.
- If an assigned officer exists, a system-generated activity is logged for automatic assignment.

### Side effects
- Creates an Issue row
- Creates an IssueActivity row
- Sets the initial assignee from the department’s assigned officer

## 3. check_issue_completeness

### Purpose
Checks whether all required documents for an issue’s category have been uploaded.

### Parameters
- issue: Issue instance

### Return value
A dictionary with:
- is_complete: boolean
- missing_documents: list of missing document names

### Models used
- Issue
- IssueDocument
- Category
- Document

### Business rules enforced
- The required documents are taken from the issue’s category documents relationship.
- Uploads are considered complete only when every required document has been attached.

### Side effects
- None; this function is read-only and does not change the database.

## 4. upload_document

### Purpose
Stores a document upload for an issue and updates the issue’s completeness and status.

### Parameters
- issue_id: integer ID of the Issue
- document_id: integer ID of the Document definition
- file: uploaded file object

### Return value
A dictionary with:
- issue_id
- document_uploaded
- is_complete
- status
- missing_documents

### Models used
- Issue
- IssueDocument
- Document
- IssueActivity

### Business rules enforced
- The issue and document definition must exist.
- If the same document is uploaded again, the existing upload is replaced.
- If all required documents have been uploaded, the issue becomes complete and its status is set to ready_for_review.

### Side effects
- Creates or updates an IssueDocument row
- Creates an IssueActivity row for the upload
- Updates issue.is_complete
- Updates issue.status to ready_for_review when the issue becomes complete
- Creates a system-generated activity when the issue becomes ready for review

## 5. change_issue_status

### Purpose
Applies an allowed status transition for an issue.

### Parameters
- issue: Issue instance
- user: Django User instance attempting the transition
- new_status: target status string
- notes: optional notes used for resolution

### Return value
A dictionary with:
- success: boolean
- message: explanation of the outcome
- status: updated status when successful

### Models used
- Issue
- IssueActivity

### Business rules enforced
- Only the following transitions are allowed:
  - pending -> none
  - ready_for_review -> in_progress
  - in_progress -> resolved
  - resolved -> closed
  - closed -> none
- Only the assigned officer or an admin is allowed to change the status.
- Resolution notes are required before moving an issue to resolved.

### Side effects
- Updates the Issue status
- Stores resolution notes when resolving
- Creates an IssueActivity entry for the status change

## 6. Notes on Partial Implementation

The service layer is implemented, but the corresponding API endpoints for document upload and status update are not currently wired in the URL configuration. The business rules exist in the service code, but they are not yet fully exposed to API consumers.
