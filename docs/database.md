# Database Model Reference

This document describes the database models that are currently implemented in the backend.

## 1. Model Summary

| Model | Purpose | Current implementation status |
| --- | --- | --- |
| Issue | Represents a student-submitted issue | Implemented |
| IssueDocument | Links an issue to a document upload file | Implemented |
| IssueActivity | Stores audit trail events related to an issue | Implemented |
| Category | Groups issues into categories and defines required documents | Implemented |
| Department | Represents a department and its assigned officer | Implemented |
| Document | Defines a reusable document type | Implemented |
| UserProfile | Stores extra profile fields for a Django user | Implemented as a model only |

## 2. Issue

### Purpose
Represents a complaint or issue submitted by a student.

### Fields

| Field | Type | Null/Blank | Description |
| --- | --- | --- | --- |
| id | AutoField | No | Primary key |
| student | ForeignKey to User | No | The student who created the issue |
| assigned_to | ForeignKey to User | Yes | Optional assigned officer |
| category | ForeignKey to Category | No | Category associated with the issue |
| title | CharField(255) | No | Issue title |
| description | TextField | No | Detailed description |
| status | CharField | No | Current status; choices are pending, ready_for_review, in_progress, resolved, closed |
| is_complete | BooleanField | No | Indicates whether required documents have been uploaded |
| resolution_notes | TextField | Yes | Notes entered when resolving an issue |
| created_at | DateTimeField | No | Timestamp when the issue was created |
| updated_at | DateTimeField | No | Last update timestamp |

### Relationships
- Many-to-one with User as student
- Many-to-one with User as assigned_to
- Many-to-one with Category
- One-to-many with IssueDocument
- One-to-many with IssueActivity

## 3. IssueDocument

### Purpose
Stores a document upload associated with an issue.

### Fields

| Field | Type | Null/Blank | Description |
| --- | --- | --- | --- |
| id | AutoField | No | Primary key |
| issue | ForeignKey to Issue | No | Parent issue |
| document | ForeignKey to Document | No | Document definition that this upload satisfies |
| file | FileField | No | Uploaded file |
| uploaded_at | DateTimeField | No | Upload timestamp |

### Relationships
- Many-to-one with Issue
- Many-to-one with Document

## 4. IssueActivity

### Purpose
Records the history of actions taken on an issue.

### Fields

| Field | Type | Null/Blank | Description |
| --- | --- | --- | --- |
| id | AutoField | No | Primary key |
| issue | ForeignKey to Issue | No | Related issue |
| action | CharField(255) | No | Activity label |
| performed_by | ForeignKey to User | Yes | User who performed the action |
| is_system_action | BooleanField | No | Indicates whether the action was system-generated |
| notes | TextField | Yes | Optional notes |
| created_at | DateTimeField | No | Activity timestamp |

### Relationships
- Many-to-one with Issue
- Many-to-one with User as performed_by

## 5. Category

### Purpose
Defines an issue category and the documents required to make an issue complete.

### Fields

| Field | Type | Null/Blank | Description |
| --- | --- | --- | --- |
| id | AutoField | No | Primary key |
| name | CharField(120) | No | Category name |
| department | ForeignKey to Department | No | Owning department |
| description | TextField | Yes | Category description |
| documents | ManyToManyField to Document | Yes | Required documents for the category |

### Relationships
- Many-to-one with Department
- Many-to-many with Document
- One-to-many with Issue

## 6. Department

### Purpose
Represents an academic or administrative department.

### Fields

| Field | Type | Null/Blank | Description |
| --- | --- | --- | --- |
| id | AutoField | No | Primary key |
| name | CharField(100) | No | Department name |
| description | TextField | Yes | Department description |
| assigned_officer | ForeignKey to User | Yes | Optional designated officer |

### Relationships
- One-to-many with Category
- Optional many-to-one with User as assigned_officer

## 7. Document

### Purpose
Defines a document type that can be required for category completion.

### Fields

| Field | Type | Null/Blank | Description |
| --- | --- | --- | --- |
| id | AutoField | No | Primary key |
| name | CharField(150) | No | Document name |
| description | TextField | Yes | Document description |

### Relationships
- Many-to-many with Category
- One-to-many with IssueDocument

## 8. UserProfile

### Purpose
Stores profile information for Django users such as role and department metadata.

### Fields

| Field | Type | Null/Blank | Description |
| --- | --- | --- | --- |
| id | AutoField | No | Primary key |
| user | OneToOneField to User | No | Linked Django user |
| role | CharField(30) | No | Role choices include student, course_adviser, hod, ict_officer, exams_officer, admin |
| matric_number | CharField(50) | Yes | Student identifier |
| phone_number | CharField(20) | Yes | Phone number |
| department_name | CharField(100) | Yes | Department name |
| level | CharField(20) | Yes | Academic level |

### Relationships
- One-to-one with Django User

## 9. Business Purpose of Each Model

| Model | Business purpose |
| --- | --- |
| Issue | Tracks a student complaint from submission to resolution |
| IssueDocument | Associates supporting files with a complaint |
| IssueActivity | Maintains an audit trail for issue-related actions |
| Category | Encodes the classification of issues and their document requirements |
| Department | Represents the organizational owner of a category and its assigned officer |
| Document | Defines the document types that are expected for a category |
| UserProfile | Holds role-based profile data for users |
