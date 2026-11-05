"""
Workflow engine test suite.

Covers, per the workflow specification: every legal status transition,
every explicitly-called-out illegal transition, forward routing, backward
routing, the student confirmation workflow (confirm + reject), the
additional-information-request round trip, category-specific workflow
validation (including the dynamic "Other" category), and final-authority
validation.

These tests exercise issues/workflow/service.py directly (the same
functions issues/views.py's workflow endpoints call) plus
issues/services/document_service.py's request-info upload round trip and
issues/services/status_service.py's now-delegating implementation. They do
not touch authentication, the ML classifier, or anything under ml/.
"""

from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import UserProfile
from categories.models import Category
from departments.models import Department
from documents_app.models import Document
from issues.models import Issue, IssueActivity
from issues.services import admin_assignment_service, document_service, issue_service, status_service
from issues.workflow import service as workflow_service
from issues.workflow.exceptions import (
    InvalidTransitionError,
    MissingExplanationError,
    NoOfficerAvailableError,
    UnauthorizedTransitionError,
    WorkflowNotConfiguredError,
)
from ml.classifier import (
    CategoryLookupError,
    ClassifierArtifactNotFoundError,
    ClassifierLoadError,
    PredictionInputError,
)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class WorkflowTestBase(TestCase):
    """Shared fixtures: a couple of departments, one staff member per role
    needed across the 12 category workflows, and a small document
    catalogue. Individual tests create the Issue(s) and Category(ies) they
    need on top of this.

    PASSWORD_HASHERS is overridden to a fast hasher for the duration of
    these tests only (via override_settings, not touched in the real
    settings.py) -- setUp() creates over a dozen Users per test, and the
    project's default PBKDF2 hasher is intentionally slow, which made the
    full suite take minutes. This has no effect outside the test run.
    """

    def setUp(self):
        self.dept_cs = Department.objects.create(name="Department of Computer Science")
        self.dept_exams = Department.objects.create(name="Exams and Records Unit")

        self.student = self._make_user("student1", "student", department_name="Computer Science")
        self.other_student = self._make_user("student2", "student", department_name="Computer Science")

        self.admin = self._make_user("admin1", "admin")

        self.course_adviser = self._make_user("adviser1", "course_adviser", department_name="Computer Science")
        self.hod = self._make_user("hod1", "hod", department_name="Computer Science")
        self.department_admin = self._make_user("deptadmin1", "department_admin", department_name="Computer Science")
        self.lecturer = self._make_user("lecturer1", "lecturer", department_name="Computer Science")
        self.dept_exam_officer = self._make_user("deptexam1", "dept_exam_officer", department_name="Computer Science")

        self.exams_officer = self._make_user("examsofficer1", "exams_officer")
        self.bursary = self._make_user("bursary1", "bursary")
        self.registry = self._make_user("registry1", "registry")
        self.ict_officer = self._make_user("ict1", "ict_officer")
        self.school_admin_office = self._make_user("schooladmin1", "school_admin_office")
        self.student_affairs_officer = self._make_user("studentaffairs1", "student_affairs_officer")

        self.doc = Document.objects.create(name="Course Registration Slip")

    def _make_user(self, username, role, department_name=None):
        user = User.objects.create_user(username=username, password="password123")
        UserProfile.objects.create(user=user, role=role, department_name=department_name)
        return user

    def _make_category(self, name, department=None):
        category = Category.objects.create(
            name=name,
            department=department or self.dept_cs,
        )
        category.documents.add(self.doc)
        return category

    def _make_issue(self, category, assigned_to, status="in_progress", student=None):
        return Issue.objects.create(
            student=student or self.student,
            category=category,
            assigned_to=assigned_to,
            title=f"{category.name} issue",
            description="Test issue description.",
            status=status,
            is_complete=True,
        )


# ---------------------------------------------------------------------
# Initial assignment: issue_service.create_issue() delegating to
# workflow_service.perform_initial_assignment(). The workflow engine is
# the only thing that ever sets Issue.assigned_to -- these tests exercise
# the real create_issue() entry point (not _make_issue(), which sets
# assigned_to directly and is only a fixture shortcut for tests that don't
# care about initial assignment).
# ---------------------------------------------------------------------

class InitialAssignmentTests(WorkflowTestBase):

    def test_missing_result_auto_assigns_to_course_adviser(self):
        category = self._make_category("Missing Result", department=self.dept_exams)

        result = issue_service.create_issue(
            student=self.student,
            category_id=category.id,
            title="Missing result",
            description="My GST111 result is missing.",
        )

        issue = Issue.objects.get(id=result["issue_id"])
        self.assertEqual(issue.assigned_to, self.course_adviser)
        self.assertEqual(result["assigned_to"], "adviser1")
        self.assertTrue(issue.activities.filter(action="Automatically Assigned").exists())

    def test_transcript_request_auto_assigns_to_department_admin(self):
        category = self._make_category("Transcript Request", department=self.dept_exams)

        result = issue_service.create_issue(
            student=self.student,
            category_id=category.id,
            title="Transcript request",
            description="I need my official transcript.",
        )

        issue = Issue.objects.get(id=result["issue_id"])
        self.assertEqual(issue.assigned_to, self.department_admin)
        self.assertEqual(result["assigned_to"], "deptadmin1")

    def test_school_fees_issue_auto_assigns_to_bursary(self):
        category = self._make_category("School Fees Issue", department=self.dept_cs)

        result = issue_service.create_issue(
            student=self.student,
            category_id=category.id,
            title="Fee payment not reflecting",
            description="I paid but the portal still shows a balance.",
        )

        issue = Issue.objects.get(id=result["issue_id"])
        self.assertEqual(issue.assigned_to, self.bursary)
        self.assertEqual(result["assigned_to"], "bursary1")

    def test_initial_assignment_does_not_depend_on_department_assigned_officer(self):
        # Point Department.assigned_officer at an unrelated staff member
        # and confirm the created issue is still routed to the real
        # Course Adviser through the workflow engine -- proving there is
        # no remaining code path that reads this field for routing.
        decoy_officer = self._make_user("decoy_officer", "ict_officer")
        self.dept_exams.assigned_officer = decoy_officer
        self.dept_exams.save()

        category = self._make_category("Missing Result", department=self.dept_exams)

        result = issue_service.create_issue(
            student=self.student,
            category_id=category.id,
            title="Missing result",
            description="My result is missing.",
        )

        issue = Issue.objects.get(id=result["issue_id"])
        self.assertEqual(issue.assigned_to, self.course_adviser)
        self.assertNotEqual(issue.assigned_to, decoy_officer)

    def test_unconfigured_category_creates_issue_unassigned_instead_of_raising(self):
        category = self._make_category("Not A Real Category", department=self.dept_cs)

        result = issue_service.create_issue(
            student=self.student,
            category_id=category.id,
            title="Something unusual",
            description="Does not match any of the 12 canonical categories.",
        )

        issue = Issue.objects.get(id=result["issue_id"])
        self.assertIsNone(issue.assigned_to)
        self.assertIsNone(result["assigned_to"])
        self.assertTrue(issue.activities.filter(action="Automatic Assignment Skipped").exists())

    def test_no_officer_available_creates_issue_unassigned_instead_of_raising(self):
        # Academic Clearance's starting role (department_admin) is
        # department-scoped; a student from a department with no
        # Department Admin on staff should still get a created issue,
        # just left unassigned, not a failed request.
        chemistry_student = self._make_user("chem_student2", "student", department_name="Chemistry")
        category = self._make_category("Academic Clearance", department=self.dept_cs)

        result = issue_service.create_issue(
            student=chemistry_student,
            category_id=category.id,
            title="Clearance",
            description="Need academic clearance.",
        )

        issue = Issue.objects.get(id=result["issue_id"])
        self.assertIsNone(issue.assigned_to)
        self.assertTrue(issue.activities.filter(action="Automatic Assignment Skipped").exists())

    def test_created_issue_can_proceed_through_start_review_immediately(self):
        # End-to-end sanity check that the engine-assigned officer is a
        # fully valid participant in the rest of the workflow (not just an
        # attribute set in isolation): once required documents are
        # present, the assigned Course Adviser can pick the issue up.
        category = self._make_category("Missing Result", department=self.dept_exams)

        result = issue_service.create_issue(
            student=self.student,
            category_id=category.id,
            title="Missing result",
            description="My result is missing.",
        )
        issue = Issue.objects.get(id=result["issue_id"])
        issue.status = "ready_for_review"
        issue.save()

        workflow_service.start_review(issue, self.course_adviser)
        issue.refresh_from_db()
        self.assertEqual(issue.status, "in_progress")
        self.assertEqual(issue.assigned_to, self.course_adviser)


# ---------------------------------------------------------------------
# Status-graph legality (independent of category)
# ---------------------------------------------------------------------

class StatusTransitionGraphTests(WorkflowTestBase):

    def test_all_legal_edges_pass(self):
        legal_pairs = [
            ("pending", "ready_for_review"),
            ("ready_for_review", "in_progress"),
            ("in_progress", "ready_for_review"),
            ("in_progress", "pending"),
            ("in_progress", "resolved"),
            ("resolved", "closed"),
            ("resolved", "pending"),
        ]
        for current, new in legal_pairs:
            with self.subTest(current=current, new=new):
                workflow_service.validate_status_transition(current, new)  # must not raise

    def test_explicitly_invalid_examples_from_spec(self):
        invalid_pairs = [
            ("closed", "in_progress"),
            ("pending", "closed"),
            ("resolved", "ready_for_review"),
        ]
        for current, new in invalid_pairs:
            with self.subTest(current=current, new=new):
                with self.assertRaises(InvalidTransitionError):
                    workflow_service.validate_status_transition(current, new)

    def test_closed_has_no_outgoing_transitions_at_all(self):
        for new_status in ["pending", "ready_for_review", "in_progress", "resolved", "closed"]:
            with self.assertRaises(InvalidTransitionError):
                workflow_service.validate_status_transition("closed", new_status)


# ---------------------------------------------------------------------
# start_review
# ---------------------------------------------------------------------

class StartReviewTests(WorkflowTestBase):

    def test_assigned_officer_can_start_review(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="ready_for_review")

        result = workflow_service.start_review(issue, self.course_adviser)

        issue.refresh_from_db()
        self.assertEqual(issue.status, "in_progress")
        self.assertEqual(result["status"], "in_progress")
        self.assertTrue(issue.activities.filter(action="Issue Review Started").exists())

    def test_non_assigned_user_cannot_start_review(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="ready_for_review")

        with self.assertRaises(UnauthorizedTransitionError):
            workflow_service.start_review(issue, self.hod)

    def test_admin_can_start_review_for_anyone(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="ready_for_review")

        workflow_service.start_review(issue, self.admin)
        issue.refresh_from_db()
        self.assertEqual(issue.status, "in_progress")

    def test_cannot_start_review_from_pending(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="pending")

        with self.assertRaises(InvalidTransitionError):
            workflow_service.start_review(issue, self.course_adviser)


# ---------------------------------------------------------------------
# Forward routing
# ---------------------------------------------------------------------

class ForwardRoutingTests(WorkflowTestBase):

    def test_missing_result_forwards_through_full_chain(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="in_progress")

        result = workflow_service.forward_issue(issue, self.course_adviser)
        issue.refresh_from_db()
        self.assertEqual(issue.status, "ready_for_review")
        self.assertEqual(issue.assigned_to, self.department_admin)
        self.assertEqual(result["assigned_to"], "deptadmin1")

        workflow_service.start_review(issue, self.department_admin)
        workflow_service.forward_issue(issue, self.department_admin)
        issue.refresh_from_db()
        self.assertEqual(issue.assigned_to, self.hod)

        workflow_service.start_review(issue, self.hod)
        workflow_service.forward_issue(issue, self.hod)
        issue.refresh_from_db()
        self.assertEqual(issue.assigned_to, self.exams_officer)

    def test_forwarding_past_final_stage_is_rejected(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.exams_officer, status="in_progress")

        with self.assertRaises(InvalidTransitionError):
            workflow_service.forward_issue(issue, self.exams_officer)

    def test_forward_creates_activity_entry(self):
        category = self._make_category("Grade Dispute", department=self.dept_cs)
        issue = self._make_issue(category, self.course_adviser, status="in_progress")

        workflow_service.forward_issue(issue, self.course_adviser, notes="Escalating.")

        self.assertTrue(
            issue.activities.filter(action="Issue Forwarded").exists()
        )

    def test_non_assigned_officer_cannot_forward(self):
        category = self._make_category("Grade Dispute", department=self.dept_cs)
        issue = self._make_issue(category, self.course_adviser, status="in_progress")

        with self.assertRaises(UnauthorizedTransitionError):
            workflow_service.forward_issue(issue, self.lecturer)

    def test_forward_reassigns_officer_to_ready_for_review_not_in_progress(self):
        # New officer must explicitly start_review(); forwarding alone
        # never leaves the issue "in_progress" under someone who hasn't
        # picked it up yet.
        category = self._make_category("Course Registration", department=self.dept_cs)
        issue = self._make_issue(category, self.course_adviser, status="in_progress")

        workflow_service.forward_issue(issue, self.course_adviser)
        issue.refresh_from_db()
        self.assertEqual(issue.status, "ready_for_review")
        self.assertEqual(issue.assigned_to, self.exams_officer)

class NoOfficerAvailableTests(WorkflowTestBase):

    def test_forward_raises_no_officer_available_when_department_has_no_match(self):
        category = self._make_category("Examination Issue", department=self.dept_exams)
        chemistry_student = self._make_user("chem_student", "student", department_name="Chemistry")
        chem_exam_officer = self._make_user(
            "chem_exam_officer", "dept_exam_officer", department_name="Chemistry"
        )
        issue = self._make_issue(
            category, chem_exam_officer, status="in_progress", student=chemistry_student
        )

        # Forwarding from dept_exam_officer -> hod: no HOD exists for
        # Chemistry in this test's fixtures.
        with self.assertRaises(NoOfficerAvailableError):
            workflow_service.forward_issue(issue, chem_exam_officer)


# ---------------------------------------------------------------------
# Backward routing
# ---------------------------------------------------------------------

class BackwardRoutingTests(WorkflowTestBase):

    def test_missing_result_hod_can_send_back_to_course_adviser(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.hod, status="in_progress")

        workflow_service.send_back_issue(issue, self.hod, notes="Needs more detail.")
        issue.refresh_from_db()

        self.assertEqual(issue.status, "ready_for_review")
        self.assertEqual(issue.assigned_to, self.course_adviser)
        self.assertTrue(issue.activities.filter(action="Issue Returned").exists())

    def test_department_admin_cannot_send_back_missing_result(self):
        # Only HOD -> Course Adviser is a defined backward transition for
        # Missing Result; Department Admin has none.
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.department_admin, status="in_progress")

        with self.assertRaises(InvalidTransitionError):
            workflow_service.send_back_issue(issue, self.department_admin)

    def test_examination_issue_has_two_backward_sources_to_same_role(self):
        category = self._make_category("Examination Issue", department=self.dept_exams)

        issue_from_hod = self._make_issue(category, self.hod, status="in_progress")
        workflow_service.send_back_issue(issue_from_hod, self.hod)
        issue_from_hod.refresh_from_db()
        self.assertEqual(issue_from_hod.assigned_to, self.dept_exam_officer)

        issue_from_exams = self._make_issue(category, self.exams_officer, status="in_progress")
        workflow_service.send_back_issue(issue_from_exams, self.exams_officer)
        issue_from_exams.refresh_from_db()
        self.assertEqual(issue_from_exams.assigned_to, self.dept_exam_officer)

    def test_categories_with_no_backward_transitions_reject_send_back(self):
        category = self._make_category("Transcript Request", department=self.dept_exams)
        issue = self._make_issue(category, self.hod, status="in_progress")

        with self.assertRaises(InvalidTransitionError):
            workflow_service.send_back_issue(issue, self.hod)


# ---------------------------------------------------------------------
# Academic Clearance: Department Admin -> HOD -> Department Admin
# ---------------------------------------------------------------------

class AcademicClearanceLoopTests(WorkflowTestBase):

    def test_full_loop_ends_with_department_admin_resolving(self):
        category = self._make_category("Academic Clearance", department=self.dept_cs)
        issue = self._make_issue(category, self.department_admin, status="in_progress")

        workflow_service.forward_issue(issue, self.department_admin)
        issue.refresh_from_db()
        self.assertEqual(issue.assigned_to, self.hod)

        workflow_service.start_review(issue, self.hod)
        workflow_service.send_back_issue(issue, self.hod)
        issue.refresh_from_db()
        self.assertEqual(issue.assigned_to, self.department_admin)
        self.assertEqual(issue.status, "ready_for_review")

        workflow_service.start_review(issue, self.department_admin)
        result = workflow_service.resolve_issue(issue, self.department_admin, notes="Cleared.")
        self.assertEqual(result["status"], "resolved")

    def test_hod_cannot_resolve_academic_clearance(self):
        category = self._make_category("Academic Clearance", department=self.dept_cs)
        issue = self._make_issue(category, self.hod, status="in_progress")

        with self.assertRaises(InvalidTransitionError):
            workflow_service.resolve_issue(issue, self.hod, notes="Trying anyway.")


# ---------------------------------------------------------------------
# Final authority validation
# ---------------------------------------------------------------------

class FinalAuthorityTests(WorkflowTestBase):

    def test_final_authority_can_resolve(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="in_progress")

        result = workflow_service.resolve_issue(issue, self.course_adviser, notes="Found the result.")
        self.assertEqual(result["status"], "resolved")

    def test_non_final_authority_cannot_resolve(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.department_admin, status="in_progress")

        with self.assertRaises(InvalidTransitionError):
            workflow_service.resolve_issue(issue, self.department_admin, notes="Attempting resolve.")

    def test_dual_final_authority_category_allows_either_role(self):
        category = self._make_category("Examination Issue", department=self.dept_exams)

        issue_a = self._make_issue(category, self.dept_exam_officer, status="in_progress")
        result_a = workflow_service.resolve_issue(issue_a, self.dept_exam_officer, notes="Handled at dept level.")
        self.assertEqual(result_a["status"], "resolved")

        issue_b = self._make_issue(category, self.exams_officer, status="in_progress")
        result_b = workflow_service.resolve_issue(issue_b, self.exams_officer, notes="Handled centrally.")
        self.assertEqual(result_b["status"], "resolved")

    def test_resolve_requires_notes(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="in_progress")

        with self.assertRaises(MissingExplanationError):
            workflow_service.resolve_issue(issue, self.course_adviser, notes="")

    def test_resolve_does_not_change_ownership(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="in_progress")

        workflow_service.resolve_issue(issue, self.course_adviser, notes="Done.")
        issue.refresh_from_db()
        self.assertEqual(issue.assigned_to, self.course_adviser)

    def test_single_role_category_final_authority(self):
        category = self._make_category("School Fees Issue", department=self.dept_cs)
        issue = self._make_issue(category, self.bursary, status="in_progress")

        result = workflow_service.resolve_issue(issue, self.bursary, notes="Payment reconciled.")
        self.assertEqual(result["status"], "resolved")

        # And a single-role category cannot be forwarded further.
        issue2 = self._make_issue(category, self.bursary, status="in_progress")
        with self.assertRaises(InvalidTransitionError):
            workflow_service.forward_issue(issue2, self.bursary)


# ---------------------------------------------------------------------
# Student confirmation workflow: confirm and reject
# ---------------------------------------------------------------------

class StudentConfirmationTests(WorkflowTestBase):

    def _resolved_issue(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="resolved")
        issue.resolution_notes = "Result has been found and uploaded."
        issue.save()
        return issue

    def test_student_can_confirm_resolution(self):
        issue = self._resolved_issue()
        result = workflow_service.confirm_resolution(issue, self.student)
        self.assertEqual(result["status"], "closed")
        issue.refresh_from_db()
        self.assertEqual(issue.status, "closed")
        self.assertTrue(issue.activities.filter(action="Issue Closed").exists())

    def test_non_student_cannot_confirm_resolution(self):
        issue = self._resolved_issue()
        with self.assertRaises(UnauthorizedTransitionError):
            workflow_service.confirm_resolution(issue, self.course_adviser)

    def test_other_student_cannot_confirm_someone_elses_issue(self):
        issue = self._resolved_issue()
        with self.assertRaises(UnauthorizedTransitionError):
            workflow_service.confirm_resolution(issue, self.other_student)

    def test_closed_issue_cannot_be_modified_by_non_admin(self):
        issue = self._resolved_issue()
        workflow_service.confirm_resolution(issue, self.student)

        with self.assertRaises(InvalidTransitionError) as ctx:
            workflow_service.forward_issue(issue, self.course_adviser)
        self.assertIn("closed", str(ctx.exception).lower())

    def test_student_reject_requires_mandatory_explanation(self):
        issue = self._resolved_issue()
        with self.assertRaises(MissingExplanationError):
            workflow_service.reject_resolution(issue, self.student, explanation="")

        with self.assertRaises(MissingExplanationError):
            workflow_service.reject_resolution(issue, self.student, explanation="   ")

    def test_student_reject_moves_to_pending_without_changing_ownership_or_restarting(self):
        issue = self._resolved_issue()
        original_officer = issue.assigned_to

        result = workflow_service.reject_resolution(
            issue, self.student, explanation="The result shown is for the wrong course."
        )
        issue.refresh_from_db()

        self.assertEqual(result["status"], "pending")
        self.assertEqual(issue.status, "pending")
        self.assertEqual(issue.assigned_to, original_officer)
        self.assertTrue(
            issue.activities.filter(
                action="Student Rejected Resolution",
                notes="The result shown is for the wrong course.",
            ).exists()
        )

    def test_non_student_cannot_reject(self):
        issue = self._resolved_issue()
        with self.assertRaises(UnauthorizedTransitionError):
            workflow_service.reject_resolution(issue, self.course_adviser, explanation="Not valid.")

    def test_admin_can_confirm_on_behalf_of_student(self):
        issue = self._resolved_issue()
        result = workflow_service.confirm_resolution(issue, self.admin)
        self.assertEqual(result["status"], "closed")


# ---------------------------------------------------------------------
# Additional information request + upload round trip
# ---------------------------------------------------------------------

class AdditionalInformationTests(WorkflowTestBase):

    def test_request_more_information_moves_to_pending_without_changing_owner(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="in_progress")

        result = workflow_service.request_more_information(
            issue, self.course_adviser, notes="Please upload your latest result slip."
        )
        issue.refresh_from_db()

        self.assertEqual(result["status"], "pending")
        self.assertEqual(issue.status, "pending")
        self.assertEqual(issue.assigned_to, self.course_adviser)
        self.assertTrue(issue.activities.filter(action="Additional Information Requested").exists())

    def test_request_more_information_requires_notes(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="in_progress")

        with self.assertRaises(MissingExplanationError):
            workflow_service.request_more_information(issue, self.course_adviser, notes="")

    def test_student_upload_returns_issue_to_ready_for_review_after_info_request(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="in_progress")

        workflow_service.request_more_information(issue, self.course_adviser, notes="Need more proof.")
        issue.refresh_from_db()
        self.assertEqual(issue.status, "pending")

        upload_file = SimpleUploadedFile("slip.pdf", b"file-bytes", content_type="application/pdf")
        result = document_service.upload_document(
            issue_id=issue.id,
            document_id=self.doc.id,
            file=upload_file,
            user=self.student,
        )

        self.assertEqual(result["status"], "ready_for_review")
        issue.refresh_from_db()
        self.assertEqual(issue.status, "ready_for_review")
        # Ownership never changed throughout the round trip.
        self.assertEqual(issue.assigned_to, self.course_adviser)

        # And the same officer picks it back up.
        workflow_service.start_review(issue, self.course_adviser)
        issue.refresh_from_db()
        self.assertEqual(issue.status, "in_progress")
        self.assertEqual(issue.assigned_to, self.course_adviser)

    def test_document_upload_does_not_disturb_status_outside_pending(self):
        # Guard added to document_service.upload_document: the automatic
        # pending -> ready_for_review flip must only fire when the issue
        # was actually pending, not unconditionally.
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="in_progress")

        upload_file = SimpleUploadedFile("slip.pdf", b"file-bytes", content_type="application/pdf")
        document_service.upload_document(
            issue_id=issue.id, document_id=self.doc.id, file=upload_file, user=self.student
        )

        issue.refresh_from_db()
        self.assertEqual(issue.status, "in_progress")

    def test_document_upload_blocked_on_closed_issue_for_non_admin(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="closed")

        upload_file = SimpleUploadedFile("slip.pdf", b"file-bytes", content_type="application/pdf")
        with self.assertRaises(ValueError):
            document_service.upload_document(
                issue_id=issue.id, document_id=self.doc.id, file=upload_file, user=self.student
            )

    def test_document_upload_allowed_on_closed_issue_for_admin(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="closed")

        upload_file = SimpleUploadedFile("slip.pdf", b"file-bytes", content_type="application/pdf")
        result = document_service.upload_document(
            issue_id=issue.id, document_id=self.doc.id, file=upload_file, user=self.admin
        )
        self.assertEqual(result["document_uploaded"], self.doc.name)


# ---------------------------------------------------------------------
# "Other" category: dynamic forward destination
# ---------------------------------------------------------------------

class DynamicOtherCategoryTests(WorkflowTestBase):

    def test_hod_can_resolve_other_directly(self):
        category = self._make_category("Other", department=self.dept_cs)
        issue = self._make_issue(category, self.hod, status="in_progress")

        result = workflow_service.resolve_issue(issue, self.hod, notes="Handled directly.")
        self.assertEqual(result["status"], "resolved")

    def test_hod_can_forward_other_to_a_chosen_role(self):
        category = self._make_category("Other", department=self.dept_cs)
        issue = self._make_issue(category, self.hod, status="in_progress")

        result = workflow_service.forward_issue(issue, self.hod, target_role="ict_officer", notes="ICT matter.")
        self.assertEqual(result["assigned_to"], "ict1")
        issue.refresh_from_db()
        self.assertEqual(issue.assigned_to, self.ict_officer)
        self.assertEqual(issue.status, "ready_for_review")

    def test_other_forward_without_target_role_is_rejected(self):
        category = self._make_category("Other", department=self.dept_cs)
        issue = self._make_issue(category, self.hod, status="in_progress")

        with self.assertRaises(InvalidTransitionError):
            workflow_service.forward_issue(issue, self.hod)

    def test_other_forward_to_invalid_role_is_rejected(self):
        category = self._make_category("Other", department=self.dept_cs)
        issue = self._make_issue(category, self.hod, status="in_progress")

        with self.assertRaises(InvalidTransitionError):
            workflow_service.forward_issue(issue, self.hod, target_role="not_a_real_role")

    def test_other_forward_to_student_or_admin_role_is_rejected(self):
        category = self._make_category("Other", department=self.dept_cs)
        issue = self._make_issue(category, self.hod, status="in_progress")

        with self.assertRaises(InvalidTransitionError):
            workflow_service.forward_issue(issue, self.hod, target_role="student")

    def test_fixed_chain_category_rejects_target_role(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="in_progress")

        with self.assertRaises(InvalidTransitionError):
            workflow_service.forward_issue(issue, self.course_adviser, target_role="hod")


# ---------------------------------------------------------------------
# Category-specific workflow configuration validation
# ---------------------------------------------------------------------

class WorkflowConfigurationTests(WorkflowTestBase):

    def test_unconfigured_category_raises_meaningful_error(self):
        category = self._make_category("Not A Real Category", department=self.dept_cs)
        issue = self._make_issue(category, self.course_adviser, status="in_progress")

        with self.assertRaises(WorkflowNotConfiguredError):
            workflow_service.forward_issue(issue, self.course_adviser)

    def test_officer_whose_role_is_not_in_this_category_workflow_is_rejected(self):
        category = self._make_category("School Fees Issue", department=self.dept_cs)
        # Assigned to a course adviser, who has no part in School Fees
        # Issue's (Bursary-only) workflow -- represents a data
        # inconsistency the engine should surface, not silently allow.
        issue = self._make_issue(category, self.course_adviser, status="in_progress")

        with self.assertRaises(InvalidTransitionError):
            workflow_service.forward_issue(issue, self.course_adviser)

    def test_all_twelve_categories_are_configured(self):
        from issues.workflow.definitions import WORKFLOW_DEFINITIONS

        expected = {
            "Missing Result",
            "Grade Dispute",
            "Course Registration",
            "Transcript Request",
            "School Fees Issue",
            "Academic Clearance",
            "Admission Issue",
            "Certificate Collection",
            "Examination Issue",
            "Portal/System Issue",
            "Student Welfare",
            "Other",
        }
        self.assertEqual(set(WORKFLOW_DEFINITIONS.keys()), expected)


# ---------------------------------------------------------------------
# Certificate Collection: Registry -> Bursary, Bursary-only final authority
# ---------------------------------------------------------------------

class CertificateCollectionTests(WorkflowTestBase):

    def test_registry_forwards_to_bursary_who_alone_can_resolve(self):
        category = self._make_category("Certificate Collection", department=self.dept_cs)
        issue = self._make_issue(category, self.registry, status="in_progress")

        with self.assertRaises(InvalidTransitionError):
            workflow_service.resolve_issue(issue, self.registry, notes="Trying to resolve early.")

        workflow_service.forward_issue(issue, self.registry)
        issue.refresh_from_db()
        self.assertEqual(issue.assigned_to, self.bursary)

        workflow_service.start_review(issue, self.bursary)
        result = workflow_service.resolve_issue(issue, self.bursary, notes="Dues cleared, certificate released.")
        self.assertEqual(result["status"], "resolved")


# ---------------------------------------------------------------------
# The pre-existing StatusUpdateAPIView code path (status_service.py),
# now delegating to the workflow engine.
# ---------------------------------------------------------------------

class LegacyStatusServiceDelegationTests(WorkflowTestBase):

    def test_in_progress_delegates_to_start_review(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="ready_for_review")

        result = status_service.change_issue_status(issue, self.course_adviser, "in_progress")
        self.assertEqual(result["status"], "in_progress")

    def test_resolved_delegates_to_resolve_issue_and_requires_final_authority(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.department_admin, status="in_progress")

        with self.assertRaises(InvalidTransitionError):
            status_service.change_issue_status(issue, self.department_admin, "resolved", notes="Trying.")

    def test_closed_delegates_to_confirm_resolution_and_requires_student(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="resolved")

        # Officer can no longer self-close, unlike the old implementation.
        with self.assertRaises(UnauthorizedTransitionError):
            status_service.change_issue_status(issue, self.course_adviser, "closed")

        result = status_service.change_issue_status(issue, self.student, "closed")
        self.assertEqual(result["status"], "closed")

    def test_pending_is_not_supported_through_this_endpoint(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="in_progress")

        with self.assertRaises(ValueError):
            status_service.change_issue_status(issue, self.course_adviser, "pending", notes="x")


# ---------------------------------------------------------------------
# Administrative Assignment Management -- issues/workflow/service.py's
# manual_assign_officer() and issues/services/admin_assignment_service.py,
# exercised directly at the service layer (no HTTP involved).
# ---------------------------------------------------------------------

class ManualAssignmentServiceTests(WorkflowTestBase):

    def _unassigned_issue(self, category_name="Academic Clearance"):
        # Academic Clearance's starting role (department_admin) has nobody
        # in the Chemistry department in this fixture set, so
        # create_issue() genuinely produces a workflow exception here --
        # exactly the situation manual assignment exists for.
        chemistry_student = self._make_user("chem_student3", "student", department_name="Chemistry")
        category = self._make_category(category_name, department=self.dept_cs)
        result = issue_service.create_issue(
            student=chemistry_student,
            category_id=category.id,
            title="Clearance",
            description="Need academic clearance.",
        )
        issue = Issue.objects.get(id=result["issue_id"])
        self.assertIsNone(issue.assigned_to)  # sanity check on the fixture itself
        return issue

    def test_admin_can_manually_assign_unassigned_issue(self):
        issue = self._unassigned_issue()
        new_dept_admin = self._make_user("new_deptadmin", "department_admin", department_name="Chemistry")

        result = workflow_service.manual_assign_officer(issue, self.admin, new_dept_admin)

        issue.refresh_from_db()
        self.assertEqual(issue.assigned_to, new_dept_admin)
        self.assertEqual(result["assigned_to"], "new_deptadmin")

    def test_manual_assignment_creates_issue_activity(self):
        issue = self._unassigned_issue()
        new_dept_admin = self._make_user("new_deptadmin2", "department_admin", department_name="Chemistry")

        workflow_service.manual_assign_officer(
            issue, self.admin, new_dept_admin, notes="Newly hired, covering Chemistry."
        )

        activity = issue.activities.filter(action="Issue Manually Assigned").first()
        self.assertIsNotNone(activity)
        self.assertEqual(activity.performed_by, self.admin)
        self.assertFalse(activity.is_system_action)
        self.assertIn("new_deptadmin2", activity.notes)
        self.assertIn("Newly hired, covering Chemistry.", activity.notes)
        self.assertIsNotNone(activity.created_at)

    def test_activity_timeline_distinguishes_automatic_from_manual(self):
        issue = self._unassigned_issue()
        new_dept_admin = self._make_user("new_deptadmin3", "department_admin", department_name="Chemistry")
        workflow_service.manual_assign_officer(issue, self.admin, new_dept_admin)

        actions = list(issue.activities.values_list("action", flat=True))
        self.assertIn("Automatic Assignment Skipped", actions)  # from create_issue()
        self.assertIn("Issue Manually Assigned", actions)  # distinct action string
        self.assertNotEqual(
            actions.index("Automatic Assignment Skipped"),
            actions.index("Issue Manually Assigned"),
        )

    def test_non_admin_cannot_manually_assign(self):
        issue = self._unassigned_issue()
        new_dept_admin = self._make_user("new_deptadmin4", "department_admin", department_name="Chemistry")

        with self.assertRaises(UnauthorizedTransitionError):
            workflow_service.manual_assign_officer(issue, self.hod, new_dept_admin)

        issue.refresh_from_db()
        self.assertIsNone(issue.assigned_to)

    def test_cannot_manually_assign_already_assigned_issue(self):
        category = self._make_category("Missing Result", department=self.dept_exams)
        issue = self._make_issue(category, self.course_adviser, status="in_progress")

        with self.assertRaises(InvalidTransitionError):
            workflow_service.manual_assign_officer(issue, self.admin, self.hod)

    def test_cannot_manually_assign_to_a_student(self):
        issue = self._unassigned_issue()

        with self.assertRaises(InvalidTransitionError):
            workflow_service.manual_assign_officer(issue, self.admin, self.other_student)

    def test_manually_assigned_issue_follows_normal_workflow_immediately(self):
        # Feature 4's worked example: no Course Adviser existed, the issue
        # became unassigned, an admin manually assigns it to a newly
        # created Course Adviser, and that officer can immediately start
        # review / forward / resolve with no special handling.
        category = self._make_category("Missing Result", department=self.dept_exams)
        no_adviser_student = self._make_user("no_adviser_student", "student", department_name="Physics")
        result = issue_service.create_issue(
            student=no_adviser_student,
            category_id=category.id,
            title="Missing result",
            description="No adviser exists yet for my department.",
        )
        issue = Issue.objects.get(id=result["issue_id"])
        self.assertIsNone(issue.assigned_to)

        new_adviser = self._make_user("physics_adviser", "course_adviser", department_name="Physics")
        physics_dept_admin = self._make_user("physics_deptadmin", "department_admin", department_name="Physics")
        workflow_service.manual_assign_officer(issue, self.admin, new_adviser)
        issue.status = "ready_for_review"
        issue.save()

        # start_review
        workflow_service.start_review(issue, new_adviser)
        issue.refresh_from_db()
        self.assertEqual(issue.status, "in_progress")

        # forward -- exactly like any other Missing Result issue
        workflow_service.forward_issue(issue, new_adviser)
        issue.refresh_from_db()
        self.assertEqual(issue.assigned_to, physics_dept_admin)
        self.assertEqual(issue.status, "ready_for_review")

    def test_admin_assignment_service_resolves_ids_and_delegates(self):
        issue = self._unassigned_issue()
        new_dept_admin = self._make_user("new_deptadmin5", "department_admin", department_name="Chemistry")

        result = admin_assignment_service.manually_assign_issue(
            issue_id=issue.id,
            admin_user=self.admin,
            officer_id=new_dept_admin.id,
            notes="Covering the gap.",
        )

        self.assertEqual(result["assigned_to"], "new_deptadmin5")
        issue.refresh_from_db()
        self.assertEqual(issue.assigned_to, new_dept_admin)

    def test_admin_assignment_service_raises_on_missing_issue(self):
        with self.assertRaises(ValueError):
            admin_assignment_service.manually_assign_issue(
                issue_id=999999, admin_user=self.admin, officer_id=self.hod.id,
            )

    def test_admin_assignment_service_raises_on_missing_officer(self):
        issue = self._unassigned_issue()
        with self.assertRaises(ValueError):
            admin_assignment_service.manually_assign_issue(
                issue_id=issue.id, admin_user=self.admin, officer_id=999999,
            )


# ---------------------------------------------------------------------
# Administrative Assignment Management -- HTTP layer. Full request/
# response/permission round trip through the real URLs, using DRF's
# APIClient with force_authenticate (the standard way to test
# permission-gated DRF views without issuing real JWTs).
# ---------------------------------------------------------------------

class UnassignedFilterAndManualAssignAPITests(WorkflowTestBase):

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def _unassigned_issue(self):
        chemistry_student = self._make_user("chem_student4", "student", department_name="Chemistry")
        category = self._make_category("Academic Clearance", department=self.dept_cs)
        result = issue_service.create_issue(
            student=chemistry_student,
            category_id=category.id,
            title="Clearance",
            description="Need academic clearance.",
        )
        issue = Issue.objects.get(id=result["issue_id"])
        self.assertIsNone(issue.assigned_to)
        return issue

    def test_unassigned_filter_isolates_only_null_assigned_issues(self):
        unassigned_issue = self._unassigned_issue()
        assigned_category = self._make_category("Missing Result", department=self.dept_exams)
        assigned_issue = self._make_issue(assigned_category, self.course_adviser, status="in_progress")

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse("issue-list"), {"unassigned": "true"})

        self.assertEqual(response.status_code, 200)
        returned_ids = {row["id"] for row in response.data["data"]}
        self.assertIn(unassigned_issue.id, returned_ids)
        self.assertNotIn(assigned_issue.id, returned_ids)

    def test_default_list_endpoint_behaviour_is_unchanged(self):
        unassigned_issue = self._unassigned_issue()
        assigned_category = self._make_category("Missing Result", department=self.dept_exams)
        assigned_issue = self._make_issue(assigned_category, self.course_adviser, status="in_progress")

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse("issue-list"))  # no ?unassigned param at all

        returned_ids = {row["id"] for row in response.data["data"]}
        self.assertIn(unassigned_issue.id, returned_ids)
        self.assertIn(assigned_issue.id, returned_ids)

    def test_unassigned_count_increases_when_an_issue_cannot_be_assigned(self):
        # This is exactly the query the admin dashboard's "Unassigned
        # Issues" stat card is built on (GET /issues/?unassigned=true,
        # length of the result) -- verified here at the API layer since
        # the dashboard itself is a frontend concern with no backend
        # counterpart to unit test directly.
        self.client.force_authenticate(user=self.admin)

        before = self.client.get(reverse("issue-list"), {"unassigned": "true"})
        count_before = len(before.data["data"])

        self._unassigned_issue()

        after = self.client.get(reverse("issue-list"), {"unassigned": "true"})
        count_after = len(after.data["data"])

        self.assertEqual(count_after, count_before + 1)

    def test_admin_can_manually_assign_via_endpoint(self):
        issue = self._unassigned_issue()
        new_dept_admin = self._make_user("api_deptadmin", "department_admin", department_name="Chemistry")

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse("issue-manual-assign", kwargs={"issue_id": issue.id}),
            {"officer_id": new_dept_admin.id, "notes": "Covering Chemistry."},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        issue.refresh_from_db()
        self.assertEqual(issue.assigned_to, new_dept_admin)
        self.assertTrue(issue.activities.filter(action="Issue Manually Assigned").exists())

    def test_unauthorized_users_cannot_manually_assign(self):
        issue = self._unassigned_issue()
        new_dept_admin = self._make_user("api_deptadmin2", "department_admin", department_name="Chemistry")

        # A non-admin staff member, authenticated but not permitted.
        self.client.force_authenticate(user=self.hod)
        response = self.client.post(
            reverse("issue-manual-assign", kwargs={"issue_id": issue.id}),
            {"officer_id": new_dept_admin.id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        issue.refresh_from_db()
        self.assertIsNone(issue.assigned_to)

    def test_unauthenticated_user_cannot_manually_assign(self):
        issue = self._unassigned_issue()
        new_dept_admin = self._make_user("api_deptadmin3", "department_admin", department_name="Chemistry")

        response = self.client.post(  # no force_authenticate -- anonymous
            reverse("issue-manual-assign", kwargs={"issue_id": issue.id}),
            {"officer_id": new_dept_admin.id},
            format="json",
        )
        self.assertIn(response.status_code, (401, 403))
        issue.refresh_from_db()
        self.assertIsNone(issue.assigned_to)

    def test_assigned_issue_disappears_from_unassigned_filter(self):
        issue = self._unassigned_issue()
        new_dept_admin = self._make_user("api_deptadmin4", "department_admin", department_name="Chemistry")

        self.client.force_authenticate(user=self.admin)

        before = self.client.get(reverse("issue-list"), {"unassigned": "true"})
        self.assertIn(issue.id, {row["id"] for row in before.data["data"]})

        self.client.post(
            reverse("issue-manual-assign", kwargs={"issue_id": issue.id}),
            {"officer_id": new_dept_admin.id},
            format="json",
        )

        after = self.client.get(reverse("issue-list"), {"unassigned": "true"})
        self.assertNotIn(issue.id, {row["id"] for row in after.data["data"]})

    def test_staff_directory_endpoint_lists_only_non_student_profiles(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse("staff-directory"))

        self.assertEqual(response.status_code, 200)
        roles_returned = {row["role"] for row in response.data["data"]}
        self.assertNotIn("student", roles_returned)
        self.assertIn("course_adviser", roles_returned)

    def test_staff_directory_endpoint_is_admin_only(self):
        self.client.force_authenticate(user=self.hod)
        response = self.client.get(reverse("staff-directory"))
        self.assertEqual(response.status_code, 403)

    def test_serialized_unassigned_issue_has_null_not_missing_assigned_to(self):
        # Regression check for the SerializerMethodField fix in
        # issues/serializers.py -- a plain CharField(source="assigned_to.username")
        # silently omitted the key entirely for unassigned issues instead
        # of returning null, which would have broken any frontend code
        # checking `issue.assigned_to === null`.
        issue = self._unassigned_issue()

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse("issue-detail", kwargs={"issue_id": issue.id}))

        self.assertIn("assigned_to", response.data["data"])
        self.assertIsNone(response.data["data"]["assigned_to"])


# ---------------------------------------------------------------------
# ML classifier integration: CreateIssueAPIView now optionally invokes
# ml.classifier.predict_issue() when the request omits category_id. These
# tests patch issues.views.predict_issue directly rather than exercising
# the real trained model -- the classifier has already been tested
# independently (ml/test_classifier.py) and its output contract
# (category / confidence / requires_confirmation / requires_manual_review)
# is fixed; what's under test here is CreateIssueAPIView's branching on
# that contract, not the model's accuracy.
# ---------------------------------------------------------------------

class MLIssueCreationAPITests(WorkflowTestBase):

    def setUp(self):
        super().setUp()
        self.missing_result = self._make_category("Missing Result", department=self.dept_exams)
        self.transcript_request = self._make_category("Transcript Request", department=self.dept_exams)
        self.client = APIClient()

    def _prediction(self, category, *, confidence=0.9, requires_confirmation=False, requires_manual_review=False):
        return {
            "category": {"id": category.id, "name": category.name},
            "confidence": confidence,
            "requires_confirmation": requires_confirmation,
            "requires_manual_review": requires_manual_review,
            "top_predictions": [{"category": category.name, "confidence": confidence}],
        }

    # --- High confidence: single call, immediate creation -----------------

    def test_high_confidence_creates_issue_immediately(self):
        self.client.force_authenticate(user=self.student)
        prediction = self._prediction(self.missing_result, confidence=0.95)

        with patch("issues.views.predict_issue", return_value=prediction) as mock_predict:
            response = self.client.post(
                reverse("issue-create"),
                {"title": "Missing result", "description": "My GST111 result is missing."},
                format="json",
            )

        mock_predict.assert_called_once()
        self.assertEqual(response.status_code, 201)
        data = response.data["data"]
        self.assertEqual(data["status"], "created")
        self.assertEqual(data["category"], "Missing Result")
        self.assertEqual(data["assigned_to"], "adviser1")
        self.assertEqual(
            [d["document_id"] for d in data["required_documents"]],
            [self.doc.id],
        )

        issue = Issue.objects.get(id=data["issue_id"])
        self.assertEqual(issue.assigned_to, self.course_adviser)
        self.assertEqual(
            list(issue.activities.order_by("created_at").values_list("action", flat=True)),
            ["Issue Created", "Automatically Assigned"],
        )

    def test_high_confidence_response_never_exposes_raw_confidence(self):
        # Confidence is a backend concern -- the student-facing response
        # should never carry a numeric confidence value.
        self.client.force_authenticate(user=self.student)
        prediction = self._prediction(self.missing_result, confidence=0.95)

        with patch("issues.views.predict_issue", return_value=prediction):
            response = self.client.post(
                reverse("issue-create"),
                {"title": "Missing result", "description": "My GST111 result is missing."},
                format="json",
            )

        self.assertNotIn("confidence", response.data["data"])

    # --- Medium confidence: confirmation required --------------------------

    def test_medium_confidence_returns_confirmation_required_and_does_not_create(self):
        self.client.force_authenticate(user=self.student)
        prediction = self._prediction(self.missing_result, confidence=0.7, requires_confirmation=True)

        with patch("issues.views.predict_issue", return_value=prediction):
            response = self.client.post(
                reverse("issue-create"),
                {"title": "Ambiguous issue", "description": "Something about my result maybe."},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["status"], "confirmation_required")
        self.assertEqual(data["predicted_category"]["name"], "Missing Result")
        self.assertTrue(data["requires_confirmation"])
        self.assertNotIn("confidence", data)
        self.assertEqual(Issue.objects.count(), 0)

    def test_medium_confidence_confirmed_creates_issue_and_does_not_reclassify(self):
        self.client.force_authenticate(user=self.student)
        prediction = self._prediction(self.missing_result, confidence=0.7, requires_confirmation=True)

        with patch("issues.views.predict_issue", return_value=prediction) as mock_predict:
            first = self.client.post(
                reverse("issue-create"),
                {"title": "Ambiguous issue", "description": "Something about my result maybe."},
                format="json",
            )
            predicted_id = first.data["data"]["predicted_category"]["id"]

            second = self.client.post(
                reverse("issue-create"),
                {
                    "title": "Ambiguous issue",
                    "description": "Something about my result maybe.",
                    "category_id": predicted_id,
                },
                format="json",
            )

        # predict_issue must be called exactly once (the first request) --
        # confirming the suggestion must never re-run the classifier.
        mock_predict.assert_called_once()
        self.assertEqual(second.status_code, 201)
        data = second.data["data"]
        self.assertEqual(data["status"], "created")
        self.assertEqual(data["category"], "Missing Result")
        issue = Issue.objects.get(id=data["issue_id"])
        self.assertEqual(issue.assigned_to, self.course_adviser)

    def test_medium_confidence_rejected_manual_category_becomes_authoritative(self):
        self.client.force_authenticate(user=self.student)
        prediction = self._prediction(self.missing_result, confidence=0.7, requires_confirmation=True)

        with patch("issues.views.predict_issue", return_value=prediction) as mock_predict:
            self.client.post(
                reverse("issue-create"),
                {"title": "Ambiguous issue", "description": "Something about my result maybe."},
                format="json",
            )

            # Student rejects "Missing Result" and manually picks a
            # different category instead.
            second = self.client.post(
                reverse("issue-create"),
                {
                    "title": "Ambiguous issue",
                    "description": "Something about my result maybe.",
                    "category_id": self.transcript_request.id,
                },
                format="json",
            )

        mock_predict.assert_called_once()
        self.assertEqual(second.status_code, 201)
        data = second.data["data"]
        self.assertEqual(data["category"], "Transcript Request")
        issue = Issue.objects.get(id=data["issue_id"])
        self.assertEqual(issue.assigned_to, self.department_admin)

    # --- Low confidence: manual selection required --------------------------

    def test_low_confidence_returns_manual_selection_required_and_does_not_create(self):
        self.client.force_authenticate(user=self.student)
        prediction = self._prediction(self.missing_result, confidence=0.3, requires_manual_review=True)

        with patch("issues.views.predict_issue", return_value=prediction):
            response = self.client.post(
                reverse("issue-create"),
                {"title": "Vague issue", "description": "Not sure what category this is."},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["status"], "manual_selection_required")
        self.assertTrue(data["requires_manual_review"])
        self.assertEqual(Issue.objects.count(), 0)

    def test_low_confidence_manual_selection_creates_issue_and_does_not_reclassify(self):
        self.client.force_authenticate(user=self.student)
        prediction = self._prediction(self.missing_result, confidence=0.3, requires_manual_review=True)

        with patch("issues.views.predict_issue", return_value=prediction) as mock_predict:
            self.client.post(
                reverse("issue-create"),
                {"title": "Vague issue", "description": "Not sure what category this is."},
                format="json",
            )

            second = self.client.post(
                reverse("issue-create"),
                {
                    "title": "Vague issue",
                    "description": "Not sure what category this is.",
                    "category_id": self.transcript_request.id,
                },
                format="json",
            )

        mock_predict.assert_called_once()
        self.assertEqual(second.status_code, 201)
        issue = Issue.objects.get(id=second.data["data"]["issue_id"])
        self.assertEqual(issue.category, self.transcript_request)
        self.assertEqual(issue.assigned_to, self.department_admin)

    # --- Classifier failures handled gracefully -----------------------------

    def test_missing_model_artifacts_handled_gracefully(self):
        self.client.force_authenticate(user=self.student)
        with patch("issues.views.predict_issue", side_effect=ClassifierArtifactNotFoundError("missing")):
            response = self.client.post(
                reverse("issue-create"),
                {"title": "Issue", "description": "Description."},
                format="json",
            )
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.data["success"])
        self.assertNotIn("Traceback", response.data["message"])
        self.assertEqual(Issue.objects.count(), 0)

    def test_classifier_load_error_handled_gracefully(self):
        self.client.force_authenticate(user=self.student)
        with patch("issues.views.predict_issue", side_effect=ClassifierLoadError("corrupt")):
            response = self.client.post(
                reverse("issue-create"),
                {"title": "Issue", "description": "Description."},
                format="json",
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(Issue.objects.count(), 0)

    def test_category_lookup_error_handled_gracefully(self):
        self.client.force_authenticate(user=self.student)
        with patch("issues.views.predict_issue", side_effect=CategoryLookupError("no match")):
            response = self.client.post(
                reverse("issue-create"),
                {"title": "Issue", "description": "Description."},
                format="json",
            )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(Issue.objects.count(), 0)

    def test_prediction_input_error_handled_gracefully(self):
        self.client.force_authenticate(user=self.student)
        with patch("issues.views.predict_issue", side_effect=PredictionInputError("empty")):
            response = self.client.post(
                reverse("issue-create"),
                {"title": "Issue", "description": "Description."},
                format="json",
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Issue.objects.count(), 0)

    # --- Existing validation preserved --------------------------------------

    def test_missing_title_still_rejected_without_reaching_classifier(self):
        self.client.force_authenticate(user=self.student)
        with patch("issues.views.predict_issue") as mock_predict:
            response = self.client.post(
                reverse("issue-create"),
                {"description": "No title supplied."},
                format="json",
            )
        mock_predict.assert_not_called()
        self.assertEqual(response.status_code, 400)

    # --- Category listing endpoint (needed for the manual picker) ----------

    def test_category_list_endpoint_returns_real_categories(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(reverse("category-list"))

        self.assertEqual(response.status_code, 200)
        names = {row["name"] for row in response.data["data"]}
        self.assertIn("Missing Result", names)
        self.assertIn("Transcript Request", names)
