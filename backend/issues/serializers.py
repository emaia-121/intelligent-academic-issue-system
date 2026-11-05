from rest_framework import serializers
from categories.models import Category

from .models import (
    Issue,
    IssueActivity,
    IssueDocument
) 

from issues.workflow.definitions import (
    get_workflow_definition,
    DEPARTMENT_SCOPED_ROLES,
)

class IssueActivitySerializer(
    serializers.ModelSerializer
):

    performed_by = serializers.SerializerMethodField()

    class Meta:

        model = IssueActivity

        fields = [
            "id",
            "action",
            "performed_by",
            "is_system_action",
            "notes",
            "created_at"
        ]

    def get_performed_by(
        self,
        obj
    ):

        if obj.is_system_action:
            return "System"

        if obj.performed_by:
            return obj.performed_by.username

        return None
    
class IssueDocumentSerializer(
    serializers.ModelSerializer
):

    document = serializers.CharField(
        source="document.name",
        read_only=True
    )

    class Meta:

        model = IssueDocument

        fields = [
            "id",
            "document",
            "file",
            "uploaded_at"
        ] 

class IssueSerializer(
    serializers.ModelSerializer
):

    student = serializers.CharField(
        source="student.username",
        read_only=True
    )

    # A plain CharField(source="assigned_to.username") silently OMITS this
    # key entirely for unassigned issues instead of returning null -- DRF
    # treats the AttributeError from `None.username` as "field not
    # required, skip it" (same nullable-FK gotcha IssueActivitySerializer
    # already avoids below via a SerializerMethodField). That silent
    # omission would undermine the "Unassigned" filter/badge/stat this
    # field now drives, so it's fixed here the same way.
    assigned_to = serializers.SerializerMethodField()

    def get_assigned_to(self, obj):
        return obj.assigned_to.email if obj.assigned_to else None

    category = serializers.CharField(
        source="category.name",
        read_only=True
    )

    department = serializers.SerializerMethodField()

    def get_department(self, obj):
        definition = get_workflow_definition(obj.category.name)

        if definition.starting_role in DEPARTMENT_SCOPED_ROLES:
            profile = getattr(obj.student, "userprofile", None)

            if profile and profile.department_name:
                return profile.department_name

        return obj.category.department.name
    
    resolved_at = serializers.SerializerMethodField() 

    def get_resolved_at(self, obj):
        activity = (
            obj.activities
            .filter(action="Issue Resolved")
            .order_by("-created_at")
            .first()
        )

        return activity.created_at if activity else None

    class Meta:

        model = Issue

        fields = [
            "id",
            "title",
            "description",

            "information_request",
            "student_information_response",

            "student",
            "assigned_to",

            "category",
            "department",

            "status",
            "is_complete",

            "resolution_notes",

            "created_at",
            "resolved_at"
        ] 


class IssueDetailSerializer(
    IssueSerializer
):

    documents = IssueDocumentSerializer(
        source="issuedocument_set",
        many=True,
        read_only=True
    )

    activity_history = IssueActivitySerializer(
        source="activities",
        many=True,
        read_only=True
    )

    # The set of documents this issue's category requires -- the same
    # {document_id, document_name} shape issue_service.create_issue()
    # already returns once, at creation time (see its `required_documents`
    # key). Exposing it here too means GET /issues/:id/ (used whenever an
    # issue is reopened later, e.g. from My Issues/Assigned Issues/All
    # Issues) carries the same real information, instead of the frontend
    # having to reconstruct it from a separate, non-authoritative source.
    # Category.required_documents() (categories/models.py) is the single
    # source of truth this reads from -- nothing is duplicated or
    # recomputed here.
    required_documents = serializers.SerializerMethodField()

    def get_required_documents(self, obj):
        return [
            {
                "document_id": doc.id,
                "document_name": doc.name,
            }
            for doc in obj.category.required_documents()
        ]

    class Meta(IssueSerializer.Meta):

        fields = IssueSerializer.Meta.fields + [
            "documents",
            "activity_history",
            "updated_at",
            "required_documents"
        ]

class CreateIssueSerializer(
    serializers.Serializer
):

    # Optional: normal submission omits this entirely and lets the ML
    # classifier (issues/views.py -> ml.classifier.predict_issue) determine
    # the category. It is only supplied on the second call of the
    # confirm/manual-selection exception path -- see CreateIssueAPIView.
    category_id = serializers.IntegerField(required=False)

    title = serializers.CharField(
        max_length=255
    )

    description = serializers.CharField()

class UploadDocumentSerializer(
    serializers.Serializer
):

    document_id = serializers.IntegerField()

    file = serializers.FileField()

class StatusUpdateSerializer(
    serializers.Serializer
):

    status = serializers.ChoiceField(
        choices=[
            "in_progress",
            "resolved",
            "closed"
        ]
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True
    )


# --- Workflow engine endpoints -------------------------------------------
# One serializer per workflow action, matching the parameters each
# issues/workflow/service.py function actually needs. Kept separate from
# StatusUpdateSerializer above since these actions carry different,
# action-specific data (an optional forward target role, a mandatory
# rejection explanation, etc.) that doesn't fit a single {status, notes}
# shape.

class WorkflowForwardSerializer(
    serializers.Serializer
):

    notes = serializers.CharField(
        required=False,
        allow_blank=True
    )

    # Only used (and required) when forwarding an "Other"-category issue,
    # whose forward destination is chosen at runtime rather than fixed.
    target_role = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True
    )


class WorkflowSendBackSerializer(
    serializers.Serializer
):

    notes = serializers.CharField(
        required=False,
        allow_blank=True
    )


class WorkflowRequestInfoSerializer(
    serializers.Serializer
):

    notes = serializers.CharField()

class WorkflowSubmitInfoSerializer(
    serializers.Serializer
):

    response = serializers.CharField()

class WorkflowResolveSerializer(
    serializers.Serializer
):

    notes = serializers.CharField()


class WorkflowRejectResolutionSerializer(
    serializers.Serializer
):

    explanation = serializers.CharField()


# --- Administrative Assignment Management --------------------------------
# Distinct from the WorkflowXxxSerializer family above: this is not a
# workflow transition (it doesn't move an issue between roles in its
# category's chain), it's the admin-only exception-handling action for an
# issue automatic assignment could not resolve. See
# issues/services/admin_assignment_service.py and
# issues/workflow/service.py::manual_assign_officer().

class ManualAssignSerializer(
    serializers.Serializer
):

    officer_id = serializers.IntegerField()

    notes = serializers.CharField(
        required=False,
        allow_blank=True
    )