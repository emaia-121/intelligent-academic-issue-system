from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import (
    MultiPartParser,
    FormParser
) 

from accounts.permissions import IsSystemAdmin

from .models import Issue
from .serializers import (
    IssueSerializer,
    CreateIssueSerializer,
    UploadDocumentSerializer,
    StatusUpdateSerializer,
    IssueDetailSerializer,
    WorkflowForwardSerializer,
    WorkflowSendBackSerializer,
    WorkflowRequestInfoSerializer,
    WorkflowResolveSerializer,
    WorkflowRejectResolutionSerializer,
    ManualAssignSerializer,
    WorkflowSubmitInfoSerializer,
)

from .services.issue_service import create_issue
from .services.document_service import upload_document
from .services.status_service import change_issue_status
from .services.admin_assignment_service import manually_assign_issue

from .workflow import service as workflow_service
from .workflow.exceptions import WorkflowError, UnauthorizedTransitionError

from .utils.api_response import (
    success_response,
    error_response
)

# ML classifier -- CreateIssueAPIView is the ONLY place in the API layer
# that ever calls predict_issue(). The classifier itself (ml/classifier.py)
# is untouched: it only ever predicts a category, it never creates an
# Issue, assigns an officer, or knows anything about the workflow engine.
from ml.classifier import (
    predict_issue,
    ClassifierArtifactNotFoundError,
    ClassifierLoadError,
    CategoryLookupError,
    PredictionInputError,
    ClassifierError,
)


def _get_issue_or_none(issue_id):
    try:
        return Issue.objects.select_related(
            "category",
            "category__department",
            "assigned_to",
            "student",
        ).get(id=issue_id)
    except Issue.DoesNotExist:
        return None


def _workflow_error_response(exc):
    # UnauthorizedTransitionError -> 403, every other WorkflowError
    # subclass (invalid transition, unconfigured workflow, no officer
    # available, missing mandatory explanation) -> 400. Mirrors the
    # PermissionError/ValueError split already used elsewhere in this
    # module.
    status_code = 403 if isinstance(exc, UnauthorizedTransitionError) else 400
    return error_response(message=str(exc), status_code=status_code)

class IssueListAPIView(APIView):

    def get(self, request):

        issues = Issue.objects.all()

        # Optional ?unassigned=true -- isolates exactly the workflow
        # exceptions perform_initial_assignment() could not resolve an
        # officer for (issues/workflow/service.py). Existing callers that
        # don't pass this param keep getting every issue, unfiltered,
        # exactly as before.
        unassigned_param = request.query_params.get("unassigned")
        if unassigned_param is not None and unassigned_param.lower() in ("true", "1", "yes"):
            issues = issues.filter(assigned_to__isnull=True)

        serializer = IssueSerializer(
            issues,
            many=True
        )

        return success_response(
            data=serializer.data,
            message="Issues retrieved successfully."
        )
    
class IssueDetailAPIView(APIView):

    def get(
        self,
        request,
        issue_id
    ):

        try:
            
            issue = Issue.objects.get(
                id=issue_id
            )

        except Issue.DoesNotExist:
            
            return error_response(
                message="Issue not found.",
                status_code=404
            )

        serializer = IssueDetailSerializer(
            issue
        )

        return success_response(
            data=serializer.data,
            message="Issue retrieved successfully."
        )
    
class CreateIssueAPIView(APIView):
    """
    Normal submission (student picks nothing): POST { title, description }.
    The category has not been determined yet, so this view asks the ML
    classifier for one:

      - High confidence (requires_confirmation == False and
        requires_manual_review == False): the issue is created immediately
        using the predicted category. One request, one response, exactly
        like the pre-ML flow from the caller's point of view.

      - Medium confidence (requires_confirmation == True): nothing is
        created. The response reports the predicted category and asks the
        frontend to get the student to confirm or reject it.

      - Low confidence (requires_manual_review == True): nothing is
        created. The response asks the frontend to present the canonical
        category list (GET /api/categories/) for manual selection.

    Confirm / manual-selection submission (student has now resolved a
    category, either by confirming the suggestion or picking one from the
    list): POST { title, description, category_id }. Supplying category_id
    skips prediction entirely -- the classifier is never called a second
    time, and the manually-resolved category is authoritative. This is the
    same code path high-confidence auto-creation falls into once its
    category has been decided, so category resolution always happens
    exactly once, in exactly one place, before issue_service.create_issue()
    is ever called.
    """

    def post(
        self,
        request
    ):

        serializer = CreateIssueSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors
            )

        title = serializer.validated_data["title"]
        description = serializer.validated_data["description"]
        category_id = serializer.validated_data.get("category_id")

        if category_id is None:

            try:
                prediction = predict_issue(title=title, description=description)

            except PredictionInputError as e:
                return error_response(
                    message=str(e),
                    status_code=400
                )

            except (ClassifierArtifactNotFoundError, ClassifierLoadError):
                # The classifier is unavailable (artifacts missing/corrupt).
                # Never surface the underlying exception -- fail in a way
                # the student can still act on.
                return error_response(
                    message=(
                        "The automatic category classifier is temporarily "
                        "unavailable. Please select a category manually."
                    ),
                    status_code=503
                )

            except CategoryLookupError:
                # The classifier predicted a label with no matching row in
                # the real Category table.
                return error_response(
                    message=(
                        "Could not match the predicted category to a known "
                        "category. Please select a category manually."
                    ),
                    status_code=422
                )

            except ClassifierError:
                # Catch-all for any other documented classifier failure
                # mode -- still no stack trace reaches the client.
                return error_response(
                    message=(
                        "Could not automatically classify this issue. "
                        "Please select a category manually."
                    ),
                    status_code=500
                )

            if prediction["requires_manual_review"]:
                return success_response(
                    data={
                        "status": "manual_selection_required",
                        "predicted_category": prediction["category"],
                        "requires_confirmation": False,
                        "requires_manual_review": True,
                    },
                    message=(
                        "We could not confidently determine a category for "
                        "this issue. Please select one manually."
                    ),
                    status_code=200
                )

            if prediction["requires_confirmation"]:
                return success_response(
                    data={
                        "status": "confirmation_required",
                        "predicted_category": prediction["category"],
                        "requires_confirmation": True,
                        "requires_manual_review": False,
                    },
                    message="Please confirm the predicted category.",
                    status_code=200
                )

            category_id = prediction["category"]["id"]

        try:

            result = create_issue(
                student=request.user,
                category_id=category_id,
                title=title,
                description=description
            )

        except ValueError as e:

            return error_response(
                message=str(e)
            )

        result["status"] = "created"

        return success_response(
            data=result,
            message="Issue created successfully.",
            status_code=201
        )
    
class UploadDocumentAPIView(APIView):

    parser_classes = [
        MultiPartParser,
        FormParser
    ]

    def post(
        self,
        request,
        issue_id
    ):

        serializer = UploadDocumentSerializer(
            data=request.data
        )

        if serializer.is_valid():

            try:
                
                result = upload_document(
                    issue_id=issue_id,
                    document_id=serializer.validated_data["document_id"],
                    file=serializer.validated_data["file"],
                    user=request.user
                )

            except ValueError as e:
                
                return error_response(
                    message=str(e)
                )

            return success_response(
                data=result,
                message="Document uploaded successfully."
            )

        return error_response(
            message="Validation failed.",
            errors=serializer.errors
        )
    
class StatusUpdateAPIView(APIView):

    def patch(
        self,
        request,
        issue_id
    ):

        serializer = StatusUpdateSerializer(
            data=request.data
        )

        if serializer.is_valid():

            try:
                
                issue = Issue.objects.get(
                    id=issue_id
                )

            except Issue.DoesNotExist:
                
                return error_response(
                    message="Issue not found.",
                    status_code=404
                )
            
            user = request.user

            try:
                
                result = change_issue_status(
                    issue=issue,
                    user=user,
                    new_status=serializer.validated_data["status"],
                    notes=serializer.validated_data.get("notes")
                )

                return success_response(
                    data=result,
                    message=f"Issue status updated to {result['status'].replace('_', ' ').title()}."
                )

            except WorkflowError as e:

                return _workflow_error_response(e)

            except PermissionError as e:

                return error_response(
                    message=str(e),
                    status_code=403
                )

            except ValueError as e:

                return error_response(
                    message=str(e)
                )

        return error_response(
            message="Validation failed.",
            errors=serializer.errors
        )


# --- Workflow engine endpoints --------------------------------------------
# Each view below is a thin delegator: it loads the issue, validates the
# request body with the matching serializer, calls straight into
# issues/workflow/service.py, and translates the result (or a raised
# WorkflowError) into a response. None of these views contain any
# transition, routing, or authorization logic themselves -- that all lives
# in the workflow engine, per the "no workflow logic scattered across
# views" requirement.

class IssueStartReviewAPIView(APIView):
    """POST /issues/<id>/start/ -- ready_for_review -> in_progress."""

    def post(self, request, issue_id):

        issue = _get_issue_or_none(issue_id)

        if issue is None:
            return error_response(message="Issue not found.", status_code=404)

        try:
            result = workflow_service.start_review(issue, request.user)
        except WorkflowError as e:
            return _workflow_error_response(e)

        return success_response(data=result, message="Issue review started.")


class IssueForwardAPIView(APIView):
    """POST /issues/<id>/forward/ -- move to the next role in the
    category's workflow (or, for "Other", to an officer-chosen role)."""

    def post(self, request, issue_id):

        issue = _get_issue_or_none(issue_id)

        if issue is None:
            return error_response(message="Issue not found.", status_code=404)

        serializer = WorkflowForwardSerializer(data=request.data)

        if not serializer.is_valid():
            return error_response(message="Validation failed.", errors=serializer.errors)

        try:
            result = workflow_service.forward_issue(
                issue,
                request.user,
                notes=serializer.validated_data.get("notes"),
                target_role=serializer.validated_data.get("target_role") or None,
            )
        except WorkflowError as e:
            return _workflow_error_response(e)

        return success_response(data=result, message="Issue forwarded.")


class IssueSendBackAPIView(APIView):
    """POST /issues/<id>/send-back/ -- move to the previous role, per this
    category's explicit backward transitions."""

    def post(self, request, issue_id):

        issue = _get_issue_or_none(issue_id)

        if issue is None:
            return error_response(message="Issue not found.", status_code=404)

        serializer = WorkflowSendBackSerializer(data=request.data)

        if not serializer.is_valid():
            return error_response(message="Validation failed.", errors=serializer.errors)

        try:
            result = workflow_service.send_back_issue(
                issue,
                request.user,
                notes=serializer.validated_data.get("notes"),
            )
        except WorkflowError as e:
            return _workflow_error_response(e)

        return success_response(data=result, message="Issue returned to the previous stage.")


class IssueRequestInfoAPIView(APIView):
    """POST /issues/<id>/request-info/ -- in_progress -> pending. Ownership
    does not change."""

    def post(self, request, issue_id):

        issue = _get_issue_or_none(issue_id)

        if issue is None:
            return error_response(message="Issue not found.", status_code=404)

        serializer = WorkflowRequestInfoSerializer(data=request.data)

        if not serializer.is_valid():
            return error_response(message="Validation failed.", errors=serializer.errors)

        try:
            result = workflow_service.request_more_information(
                issue,
                request.user,
                notes=serializer.validated_data["notes"],
            )
        except WorkflowError as e:
            return _workflow_error_response(e)

        return success_response(
            data=result,
            message="Additional information requested from the student.",
        )
class IssueSubmitInfoAPIView(APIView):
    """POST /issues/<id>/submit-info/ -- pending -> ready_for_review.
    Only the issue's own student may submit the requested information.
    Ownership does not change.
    """

    def post(self, request, issue_id):

        issue = _get_issue_or_none(issue_id)

        if issue is None:
            return error_response(
                message="Issue not found.",
                status_code=404
            )

        serializer = WorkflowSubmitInfoSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors
            )

        try:
            result = workflow_service.submit_additional_information(
                issue,
                request.user,
                response=serializer.validated_data["response"],
            )
        except WorkflowError as e:
            return _workflow_error_response(e)

        return success_response(
            data=result,
            message="Additional information submitted successfully.",
        ) 

class IssueResolveAPIView(APIView):
    """POST /issues/<id>/resolve/ -- in_progress -> resolved. Only a final
    authority role for the issue's category may resolve it."""

    def post(self, request, issue_id):

        issue = _get_issue_or_none(issue_id)

        if issue is None:
            return error_response(message="Issue not found.", status_code=404)

        serializer = WorkflowResolveSerializer(data=request.data)

        if not serializer.is_valid():
            return error_response(message="Validation failed.", errors=serializer.errors)

        try:
            result = workflow_service.resolve_issue(
                issue,
                request.user,
                notes=serializer.validated_data["notes"],
            )
        except WorkflowError as e:
            return _workflow_error_response(e)

        return success_response(data=result, message="Issue resolved.")


class IssueConfirmResolutionAPIView(APIView):
    """POST /issues/<id>/confirm/ -- resolved -> closed. Only the issue's
    own student (or an admin) may confirm."""

    def post(self, request, issue_id):

        issue = _get_issue_or_none(issue_id)

        if issue is None:
            return error_response(message="Issue not found.", status_code=404)

        try:
            result = workflow_service.confirm_resolution(issue, request.user)
        except WorkflowError as e:
            return _workflow_error_response(e)

        return success_response(data=result, message="Issue closed.")


class IssueRejectResolutionAPIView(APIView):
    """POST /issues/<id>/reject/ -- resolved -> pending, with a mandatory
    explanation. The assigned officer and required documents are
    unchanged; the issue does not restart."""

    def post(self, request, issue_id):

        issue = _get_issue_or_none(issue_id)

        if issue is None:
            return error_response(message="Issue not found.", status_code=404)

        serializer = WorkflowRejectResolutionSerializer(data=request.data)

        if not serializer.is_valid():
            return error_response(message="Validation failed.", errors=serializer.errors)

        try:
            result = workflow_service.reject_resolution(
                issue,
                request.user,
                explanation=serializer.validated_data["explanation"],
            )
        except WorkflowError as e:
            return _workflow_error_response(e)

        return success_response(
            data=result,
            message="Resolution rejected; issue reopened for the assigned officer.",
        )


# --- Administrative Assignment Management ---------------------------------

class IssueManualAssignAPIView(APIView):
    """POST /issues/<id>/assign/ -- admin-only. Manually assigns an
    officer to an issue that automatic assignment could not resolve (see
    issues/workflow/service.py::perform_initial_assignment()). Contains no
    assignment logic itself: request validation only, then delegates to
    issues/services/admin_assignment_service.py, which resolves the
    issue/officer IDs and hands off to
    issues/workflow/service.py::manual_assign_officer() for the actual
    state change and IssueActivity entry -- the same single approved
    place every other assignment in this system is written from.

    permission_classes reuses IsSystemAdmin (accounts/permissions.py), the
    same class already gating StaffAccountCreationView -- no new
    permission system introduced. manual_assign_officer() also checks
    admin status itself, so this is defence in depth, not the only check.
    """

    permission_classes = [IsSystemAdmin]

    def post(self, request, issue_id):

        serializer = ManualAssignSerializer(data=request.data)

        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors
            )

        try:
            result = manually_assign_issue(
                issue_id=issue_id,
                admin_user=request.user,
                officer_id=serializer.validated_data["officer_id"],
                notes=serializer.validated_data.get("notes"),
            )

        except WorkflowError as e:
            return _workflow_error_response(e)

        except ValueError as e:
            status_code = 404 if "not found" in str(e).lower() else 400
            return error_response(message=str(e), status_code=status_code)

        return success_response(data=result, message="Issue manually assigned.")
# Create your views here.
