# Project Structure

This tree summarizes the major folders and files in the current repository.

```text
StudentIssueManagementSystem/
├── backend/
│   ├── accounts/
│   │   ├── models.py
│   │   ├── views.py
│   │   └── tests.py
│   ├── categories/
│   │   ├── models.py
│   │   ├── views.py
│   │   └── tests.py
│   ├── departments/
│   │   ├── models.py
│   │   ├── views.py
│   │   └── tests.py
│   ├── documents_app/
│   │   ├── models.py
│   │   ├── views.py
│   │   └── tests.py
│   ├── issues/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── services/
│   │       ├── issue_service.py
│   │       ├── document_service.py
│   │       └── status_service.py
│   ├── student_issue_system/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── manage.py
│   ├── db.sqlite3
│   └── media/
├── database/
├── documents/
├── frontend/
├── models/
├── project notes/
├── research/
├── screenshots/
└── docs/
```

## 1. Major Folders and Files

| Path | Responsibility |
| --- | --- |
| backend/ | Django project root and backend application code |
| backend/issues/ | Core issue management domain, views, serializers, and services |
| backend/issues/services/ | Business logic for issue creation, document upload, and status handling |
| backend/categories/ | Category model and related logic |
| backend/departments/ | Department model and assigned officer routing |
| backend/documents_app/ | Document type definitions |
| backend/accounts/ | User profile model for role-based metadata |
| backend/student_issue_system/ | Project settings and top-level routing |
| backend/media/ | Uploaded issue documents |
| docs/ | Developer-facing documentation |

## 2. Important Files

- backend/manage.py: Django management entry point
- backend/student_issue_system/settings.py: Installed apps, database config, and media settings
- backend/student_issue_system/urls.py: Top-level URL routing
- backend/issues/urls.py: Issue API routes
- backend/issues/views.py: Current issue API views
- backend/issues/serializers.py: Request and response serialization
- backend/issues/models.py: Core issue domain models
- backend/issues/services/*.py: Business logic implementation
