from django.urls import path

from .views import (
    IssueListAPIView,
    IssueDetailAPIView,
    CreateIssueAPIView,
    IssueSubmitInfoAPIView,
    UploadDocumentAPIView,
    StatusUpdateAPIView,
    IssueStartReviewAPIView,
    IssueForwardAPIView,
    IssueSendBackAPIView,
    IssueRequestInfoAPIView,
    IssueResolveAPIView,
    IssueConfirmResolutionAPIView,
    IssueRejectResolutionAPIView,
    IssueManualAssignAPIView,
)

urlpatterns = [
    path(
        "",
        IssueListAPIView.as_view(),
        name="issue-list"
    ),

    path(
        "<int:issue_id>/",
        IssueDetailAPIView.as_view(),
        name="issue-detail"
    ),

    path(
        "create/",
        CreateIssueAPIView.as_view(),
        name="issue-create"
    ),

    path(
        "<int:issue_id>/upload-document/",
        UploadDocumentAPIView.as_view(),
        name="upload-document"
    ),

    path(
        "<int:issue_id>/status/",
        StatusUpdateAPIView.as_view(),
        name="issue-status"
    ),

    # --- Workflow engine actions ---
    path(
        "<int:issue_id>/start/",
        IssueStartReviewAPIView.as_view(),
        name="issue-start-review"
    ),

    path(
        "<int:issue_id>/forward/",
        IssueForwardAPIView.as_view(),
        name="issue-forward"
    ),

    path(
        "<int:issue_id>/send-back/",
        IssueSendBackAPIView.as_view(),
        name="issue-send-back"
    ),

    path(
        "<int:issue_id>/request-info/",
        IssueRequestInfoAPIView.as_view(),
        name="issue-request-info"
    ),

    path(
        "<int:issue_id>/submit-info/",
        IssueSubmitInfoAPIView.as_view(),
        name="issue-submit-info"
    ),

    path(
        "<int:issue_id>/resolve/",
        IssueResolveAPIView.as_view(),
        name="issue-resolve"
    ),

    path(
        "<int:issue_id>/confirm/",
        IssueConfirmResolutionAPIView.as_view(),
        name="issue-confirm-resolution"
    ),

    path(
        "<int:issue_id>/reject/",
        IssueRejectResolutionAPIView.as_view(),
        name="issue-reject-resolution"
    ),

    # --- Administrative Assignment Management (admin-only) ---
    path(
        "<int:issue_id>/assign/",
        IssueManualAssignAPIView.as_view(),
        name="issue-manual-assign"
    ),
]