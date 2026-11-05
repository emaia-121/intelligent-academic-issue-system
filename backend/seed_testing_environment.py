import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "student_issue_system.testing_settings")
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile
from accounts.constants import (
    ROLE_ADMIN, ROLE_COURSE_ADVISER, ROLE_HOD, ROLE_ICT_OFFICER,
    ROLE_EXAMS_OFFICER, ROLE_STUDENT_AFFAIRS_OFFICER, ROLE_DEPARTMENT_ADMIN,
    ROLE_LECTURER, ROLE_BURSARY, ROLE_REGISTRY, ROLE_SCHOOL_ADMIN_OFFICE,
    ROLE_DEPT_EXAM_OFFICER,
)
from categories.models import Category
from departments.models import Department
from documents_app.models import Document
from issues.models import Issue, IssueActivity, IssueDocument
from issues.workflow.definitions import WORKFLOW_DEFINITIONS

PASSWORD = "TestPass!2026"

# Remove only this script's controlled test accounts and their related data.
TEST_EMAILS = {
    "test.admin@example.test",
    "test.student1@example.test",
    "test.student2@example.test",
    "test.courseadviser@example.test",
    "test.courseadviser2@example.test",
    "test.hod@example.test",
    "test.departmentadmin@example.test",
    "test.lecturer@example.test",
    "test.dept.exam@example.test",
    "test.exams@example.test",
    "test.ict@example.test",
    "test.bursary@example.test",
    "test.registry@example.test",
    "test.schooladmin@example.test",
    "test.studentaffairs@example.test",
}

old_users = list(User.objects.filter(email__in=TEST_EMAILS))
if old_users:
    IssueActivity.objects.filter(performed_by__in=old_users).delete()
    IssueDocument.objects.filter(issue__student__in=old_users).delete()
    Issue.objects.filter(student__in=old_users).delete()
    User.objects.filter(id__in=[u.id for u in old_users]).delete()

cs = Department.objects.get(name="Computer Science", kind="academic")
chemical = Department.objects.get(name="Chemical Engineering", kind="academic")

central_departments = {
    ROLE_ICT_OFFICER: "ICT Unit",
    ROLE_EXAMS_OFFICER: "Exams and Records Unit",
    ROLE_BURSARY: "Bursary Office",
    ROLE_REGISTRY: "Registry",
    ROLE_SCHOOL_ADMIN_OFFICE: "School Admin Office",
    ROLE_STUDENT_AFFAIRS_OFFICER: "Student Affairs Office",
}

def create_user(email, first, last, role, department, staff_id=None, matric=None, level=None):
    user = User.objects.create_user(
        username=email,
        email=email,
        password=PASSWORD,
        first_name=first,
        last_name=last,
    )
    UserProfile.objects.create(
        user=user,
        role=role,
        department_name=department.name,
        staff_id=staff_id,
        matric_number=matric,
        level=level,
        must_change_password=False,
    )
    return user

create_user("test.admin@example.test", "Test", "Admin", ROLE_ADMIN, cs, staff_id="TEST-ADM-001")

create_user("test.student1@example.test", "Test", "Student One", "student", cs, matric="CSC/TEST/001", level="400L")
create_user("test.student2@example.test", "Test", "Student Two", "student", chemical, matric="CHE/TEST/002", level="400L")

staff_specs = [
    ("test.courseadviser@example.test", "Test", "Course Adviser", ROLE_COURSE_ADVISER, cs, "TEST-CA-001"),
    ("test.courseadviser2@example.test", "Test", "Course Adviser Two", ROLE_COURSE_ADVISER, chemical, "TEST-CA-002"),
    ("test.hod@example.test", "Test", "HOD", ROLE_HOD, cs, "TEST-HOD-001"),
    ("test.departmentadmin@example.test", "Test", "Department Admin", ROLE_DEPARTMENT_ADMIN, cs, "TEST-DA-001"),
    ("test.lecturer@example.test", "Test", "Lecturer", ROLE_LECTURER, cs, "TEST-LEC-001"),
    ("test.dept.exam@example.test", "Test", "Department Exam Officer", ROLE_DEPT_EXAM_OFFICER, cs, "TEST-DEO-001"),
    ("test.exams@example.test", "Test", "Exams Officer", ROLE_EXAMS_OFFICER, cs, "TEST-EXAMS-001"),
    ("test.ict@example.test", "Test", "ICT Officer", ROLE_ICT_OFFICER, cs, "TEST-ICT-001"),
    ("test.bursary@example.test", "Test", "Bursary Officer", ROLE_BURSARY, central_departments[ROLE_BURSARY] and Department.objects.get(name=central_departments[ROLE_BURSARY]), "TEST-BUR-001"),
    ("test.registry@example.test", "Test", "Registry Officer", ROLE_REGISTRY, Department.objects.get(name="Registry"), "TEST-REG-001"),
    ("test.schooladmin@example.test", "Test", "School Admin", ROLE_SCHOOL_ADMIN_OFFICE, Department.objects.get(name="School Admin Office"), "TEST-SAO-001"),
    ("test.studentaffairs@example.test", "Test", "Student Affairs", ROLE_STUDENT_AFFAIRS_OFFICER, Department.objects.get(name="Student Affairs Office"), "TEST-SAO-002"),
]
for spec in staff_specs:
    create_user(*spec)

# Ensure the canonical category/document catalogue is present and aligned
# with the workflow definitions. Migration 0005 normally creates these on
# a fresh database; this also makes the setup resilient to an already
# migrated test database.
category_departments = {
    "Missing Result": "Exams and Records Unit",
    "Grade Dispute": "Computer Science",
    "Course Registration": "Computer Science",
    "Transcript Request": "Exams and Records Unit",
    "School Fees Issue": "Bursary Office",
    "Academic Clearance": "Computer Science",
    "Admission Issue": "School Admin Office",
    "Certificate Collection": "Registry",
    "Examination Issue": "Exams and Records Unit",
    "Portal/System Issue": "ICT Unit",
    "Student Welfare": "Student Affairs Office",
    "Other": "Computer Science",
}

for category_name, definition in WORKFLOW_DEFINITIONS.items():
    dept = Department.objects.get(name=category_departments[category_name])
    category, _ = Category.objects.get_or_create(name=category_name, defaults={"department": dept})
    category.department = dept
    category.save()
    docs = []
    for doc_name in definition.required_documents:
        doc, _ = Document.objects.get_or_create(name=doc_name)
        docs.append(doc)
    category.documents.set(docs)

print("TEST ENVIRONMENT READY")
print(f"Database: {django.conf.settings.DATABASES['default']['NAME']}")
print(f"Password for all test accounts: {PASSWORD}")
print("Accounts:")
for u in User.objects.order_by("id"):
    p = u.userprofile
    print(f"  {u.email} | {p.role} | {p.department_name}")
print(f"Categories: {Category.objects.count()}")
print(f"Documents: {Document.objects.count()}")
print(f"Issues: {Issue.objects.count()}")
