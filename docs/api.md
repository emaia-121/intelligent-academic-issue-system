# API Reference

The current backend exposes a small set of issue-related REST endpoints through Django REST Framework.

## 1. Base URL

The current URL prefix is:

```text
/api/issues/
```

## 2. Implemented Endpoints

| Method | URL | Purpose | Serializer | Service invoked |
| --- | --- | --- | --- | --- |
| GET | /api/issues/ | List all issues | IssueSerializer | None |
| POST | /api/issues/create/ | Create a new issue | CreateIssueSerializer | create_issue |

## 3. GET /api/issues/

### Description
Returns a list of all issues in the database.

### Request body
No body.

### Response body
A JSON array of issue objects.

Example response:

```json
[
  {
    "id": 1,
    "title": "Library access issue",
    "description": "I cannot access the library portal.",
    "student": "Miracle",
    "assigned_to": "officer1",
    "category": "ICT",
    "department": "Computer Science",
    "status": "pending",
    "is_complete": false,
    "resolution_notes": null,
    "created_at": "2026-07-06T00:00:00Z"
  }
]
```

### Status codes
- 200 OK

### Notes
The current implementation does not apply authentication or permission checks.

## 4. POST /api/issues/create/

### Description
Creates a new issue using the submitted category, title, and description.

### Request body
The request expects a JSON object with the following fields:

```json
{
  "category_id": 1,
  "title": "Library access issue",
  "description": "I cannot access the library portal."
}
```

### Validation
The CreateIssueSerializer validates:
- category_id: required integer
- title: required string, max length 255
- description: required string

### Response body
On success, the endpoint returns a dictionary with the created issue details and the required document list.

Example success response:

```json
{
  "issue_id": 1,
  "title": "Library access issue",
  "category": "ICT",
  "assigned_to": "officer1",
  "required_documents": [
    {
      "document_id": 1,
      "document_name": "Student ID"
    }
  ]
}
```

### Status codes
- 201 Created on success
- 400 Bad Request when validation fails

### Serializer used
- CreateIssueSerializer

### Service function invoked
- create_issue

### Important implementation note
The current implementation uses a hard-coded Django user named Miracle for the student field. This is a partial implementation and should not be treated as a finished authentication flow.

## 5. Not Yet Exposed via API

The following service functions are implemented in the codebase but are not currently exposed through URL routes:

- upload_document
- change_issue_status

These are available as Python service functions, but no API endpoint currently routes to them.
