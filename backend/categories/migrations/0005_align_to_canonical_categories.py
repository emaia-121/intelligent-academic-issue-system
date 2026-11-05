# Data migration (not a schema change): brings the seeded Category rows
# into alignment with the 12 canonical category names used by both the ML
# classifier's label set (ml/model_config.py / ml/classifier.py) and the
# workflow engine's WORKFLOW_DEFINITIONS (issues/workflow/definitions.py).
#
# Why this is needed: those two components were always built around the
# 12 canonical names, but the categories_category table was seeded earlier
# (by hand, via the admin/shell -- there was never a migration or fixture
# that created the original rows) under a different, informal naming
# scheme: "Fee Payment Issue", "Incorrect Grade Entry", "Portal Login
# Issues" / "Portal Error" / "Wi-Fi Issues" / "Wi-Fi Setup" as four
# separate rows, etc. Any issue whose predicted/selected category used the
# old names would fail Category lookup, and the workflow engine would
# correctly raise WorkflowNotConfiguredError. This migration removes that
# mismatch at its source -- the database -- rather than adding any
# alias/translation layer in code.
#
# Written to be environment-agnostic, since Categories/Departments/
# Documents were never seeded by a migration in the first place:
#   - Against the real, hand-seeded dev database, every legacy row is
#     matched by its old name and either renamed in place (UPDATE, same
#     row id -- so existing Issue/IssueDocument history is preserved
#     untouched) or, for zero-Issue duplicates, merged into one survivor
#     and deleted (every duplicate is verified to have zero Issues first).
#   - Against a fresh database (e.g. `manage.py test`, or a new clone that
#     has never been manually seeded), none of the legacy rows exist, so
#     this migration creates the 12 canonical categories, their
#     departments, and their required documents directly. Either way the
#     end state is identical: exactly the 12 canonical categories, no
#     duplicates, no legacy names.
#   - Running it twice (idempotency) is also safe: matching by name means
#     a second run just finds the canonical rows already in place and
#     leaves them alone.
#
# Document catalogue renames follow the same principle: where an existing
# Document row is unambiguously the same real-world document the
# specification names slightly differently (e.g. "Error Message
# Print-Out" -> "Error Message Printout"), it is renamed in place (by id,
# never deleted), which leaves every existing IssueDocument row -- which
# points at a Document by id, not by name -- completely unaffected. Only
# genuinely new required-document types not previously in the catalogue
# are created fresh.
#
# See the chat summary for the two legacy categories folded in here
# ("Hostel Allocation Issues"/"Hostel Maintenance Complaints" into Student
# Welfare, and "Portal Error"/"Wi-Fi Issues"/"Wi-Fi Setup" into
# Portal/System Issue) flagged separately as possible future, out-of-scope
# functionality rather than silently discarded.

from django.db import migrations


# old catalogue name -> canonical specification wording. Renamed in place
# (id unchanged) wherever the old name exists.
RENAMED_DOCUMENTS = {
    "Error Message Print-Out": "Error Message Printout",
    "Transcript Request Form": "Transcript Request Form Slip",
    "Fee Receipt": "Dues Payment Receipts",
    "Clearance Slip": "Clearance Form",
    "Official Letter from Department": "Duly Addressed Letter",
    "Student Details Slip": "Student Portal Login Details",
}

# Already-correct existing names, plus genuinely new required-document
# types with no prior catalogue entry. get_or_create'd as-is.
UNCHANGED_OR_NEW_DOCUMENTS = [
    "Course Registration Slip",
    "Result Printout",
    "School Fees Receipt",
    "Admission Letter",
    "Student ID Card",
    "Course Form Printout",
    "Transcript Request Letter",
    "Stamped Payment Receipt",
    "Remita Payment Printout",
    "Academic Payment Receipts",
    "JAMB Result Printout",
    "WAEC/NECO Result Printout",
    "Certificate Request Letter",
    "Relevant Payment Receipt",
]


def align_categories(apps, schema_editor):
    Category = apps.get_model("categories", "Category")
    Department = apps.get_model("departments", "Department")
    Document = apps.get_model("documents_app", "Document")

    # --- 1. Rename/create the document catalogue entries we need -------
    doc_by_name = {}

    for old_name, new_name in RENAMED_DOCUMENTS.items():
        doc = Document.objects.filter(name=old_name).first()
        if doc is not None:
            doc.name = new_name
            doc.save()
        else:
            doc, _ = Document.objects.get_or_create(name=new_name)
        doc_by_name[new_name] = doc

    for name in UNCHANGED_OR_NEW_DOCUMENTS:
        doc, _ = Document.objects.get_or_create(name=name)
        doc_by_name[name] = doc

    def docs(*names):
        return [doc_by_name[n] for n in names]

    # --- 2. Departments every category needs ----------------------------
    # get_or_create throughout: on the real dev DB these already exist
    # (this is a no-op fetch); on a fresh DB they're created with the same
    # "no assigned_officer yet" default Bursary Office already has.
    dept_cs, _ = Department.objects.get_or_create(name="Department of Computer Science")
    dept_exams, _ = Department.objects.get_or_create(name="Exams and Records Unit")
    dept_student_affairs, _ = Department.objects.get_or_create(name="Student Affairs Office")
    dept_ict, _ = Department.objects.get_or_create(name="ICT Unit")
    dept_bursary, _ = Department.objects.get_or_create(name="Bursary Office")
    dept_school_admin, _ = Department.objects.get_or_create(name="School Admin Office")
    dept_registry, _ = Department.objects.get_or_create(name="Registry")

    # --- 3. Align (rename/merge/create) each of the 12 categories -------
    def align_category(canonical_name, legacy_names, department, doc_names):
        """Find every existing row matching `canonical_name` or any of
        `legacy_names`. If none exist (fresh database), create the
        category directly. If some exist, keep whichever one has real
        Issues attached as the survivor (never delete Issue history),
        rename/re-department it to the canonical values, and delete any
        other zero-Issue duplicates after merging nothing needed from
        them (their documents are being fully replaced by `doc_names`
        anyway, per the specification's authoritative document list)."""

        candidates = list(
            Category.objects.filter(name__in=[canonical_name, *legacy_names]).order_by("id")
        )

        if not candidates:
            category = Category.objects.create(name=canonical_name, department=department)
        else:
            survivor = next((c for c in candidates if c.issue_set.exists()), candidates[0])
            survivor.name = canonical_name
            survivor.department = department
            survivor.save()

            for duplicate in candidates:
                if duplicate.id == survivor.id:
                    continue
                assert not duplicate.issue_set.exists(), (
                    f"Refusing to delete category id={duplicate.id} "
                    f"({duplicate.name!r}): it has real Issues attached."
                )
                duplicate.delete()

            category = survivor

        category.documents.set(docs(*doc_names))
        return category

    align_category(
        "Missing Result", legacy_names=[],
        department=dept_exams,
        doc_names=["Course Registration Slip", "School Fees Receipt", "Result Printout"],
    )

    align_category(
        "Grade Dispute", legacy_names=["Incorrect Grade Entry"],
        department=dept_cs,  # was filed under Exams and Records -- wrong
                              # office, since Grade Dispute never leaves
                              # the student's own department (course
                              # adviser <-> lecturer only)
        doc_names=["Course Registration Slip", "School Fees Receipt", "Result Printout"],
    )

    align_category(
        "Course Registration", legacy_names=[],
        department=dept_cs,
        doc_names=["Course Form Printout", "School Fees Receipt"],
    )

    align_category(
        "Transcript Request", legacy_names=[],
        department=dept_exams,
        doc_names=["Transcript Request Form Slip", "Transcript Request Letter", "Stamped Payment Receipt"],
    )

    align_category(
        "School Fees Issue", legacy_names=["Fee Payment Issue"],
        department=dept_bursary,
        doc_names=["Remita Payment Printout", "Error Message Printout", "Student ID Card"],
    )

    align_category(
        "Academic Clearance", legacy_names=["Department Clearance Issues", "Clearance Issues"],
        department=dept_cs,  # the fully department-scoped workflow's
                              # correct office, not Bursary (one of the
                              # two legacy duplicate rows had that
                              # mismatch)
        doc_names=["Clearance Form", "Academic Payment Receipts"],
    )

    align_category(
        "Admission Issue", legacy_names=[],
        department=dept_school_admin,
        doc_names=["Admission Letter", "JAMB Result Printout", "WAEC/NECO Result Printout"],
    )

    align_category(
        "Certificate Collection", legacy_names=[],
        department=dept_registry,
        doc_names=["Dues Payment Receipts", "Certificate Request Letter"],
    )

    align_category(
        "Examination Issue", legacy_names=[],
        department=dept_exams,
        doc_names=["Duly Addressed Letter", "Student ID Card"],
    )

    align_category(
        "Portal/System Issue",
        legacy_names=["Portal Login Issues", "Portal Error", "Wi-Fi Issues", "Wi-Fi Setup"],
        department=dept_ict,
        doc_names=["Error Message Printout", "Student Portal Login Details", "Student ID Card"],
    )

    align_category(
        "Student Welfare",
        legacy_names=["Student ID Card Issues", "Hostel Allocation Issues", "Hostel Maintenance Complaints"],
        department=dept_student_affairs,
        doc_names=["School Fees Receipt", "Student ID Card", "Relevant Payment Receipt"],
    )

    align_category(
        "Other", legacy_names=[],
        department=dept_cs,
        doc_names=[],  # spec: required documents are determined case-by-case
    )


class Migration(migrations.Migration):

    dependencies = [
        ("categories", "0004_alter_category_options"),
        ("departments", "0002_department_assigned_officer"),
        ("documents_app", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(align_categories, reverse_code=migrations.RunPython.noop),
    ]
