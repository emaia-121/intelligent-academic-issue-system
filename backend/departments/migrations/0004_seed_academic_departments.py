# Data migration (not a schema change): ensures the 31 real FUPRE academic
# departments exist as Department rows with kind="academic".
#
# Why the old seed data was never replaced: no migration in this app has
# ever managed Department *row data* -- 0001/0002/0003 are schema-only
# (0003 in particular was deliberately scoped to just adding the `kind`
# column; see that migration and the task that produced it, which
# explicitly said "do not write a data migration"). The 7 rows currently
# in the database (Bursary Office, Department of Computer Science, Exams
# and Records Unit, ICT Unit, Registry, School Admin Office, Student
# Affairs Office) were hand-created directly against the dev database
# early in the project -- the same situation categories/migrations/
# 0005_align_to_canonical_categories.py already documents and worked
# around for the Category table. Applying 0003 only added a column and a
# default value to whatever rows already existed; it was never going to
# insert the 31-department list, because it was never asked to.
#
# Why this migration does not simply delete the 7 old rows and recreate
# everything: Category.department is a required ForeignKey with
# on_delete=CASCADE (categories/models.py), and every one of the 12
# canonical categories already points at one of these exact 7 rows
# (categories/migrations/0005_align_to_canonical_categories.py wired them
# up by name). Deleting any of these 7 rows would CASCADE-delete the
# Category rows pointing at them, and transitively any real Issue rows
# filed under those categories -- silent, irreversible data loss, and
# exactly the kind of destructive migration 0005 itself explicitly
# refuses to perform ("Refusing to delete category ... it has real Issues
# attached."). So instead:
#
#   1. "Department of Computer Science" IS one of the 31 canonical
#      academic departments, just under an inconsistent name -- renamed
#      in place (same id, same row), so every Category currently pointing
#      at it via department_id keeps pointing at the correct row.
#   2. The other 6 existing rows are real administrative offices, not
#      academic departments, and were never meant to be part of the
#      31-name academic list. Rather than deleting rows Categories still
#      depend on, their `kind` is corrected to "administrative" (they
#      defaulted to "academic" under 0003's safe default, since `kind`
#      did not exist yet when they were created). This matches the
#      Department Architecture Review's own conclusion: one Department
#      table holding both academic departments and administrative
#      offices, distinguished by `kind`.
#   3. Every one of the 31 canonical academic departments is then
#      ensured to exist via update_or_create() keyed on name -- creating
#      whichever of the 30 remaining ones don't already exist, and
#      leaving the renamed Computer Science row (and any department that
#      already matches) untouched on a second run. Idempotent: reapplying
#      this migration, or running it again against a database that
#      already has some of these rows, makes no further changes.
#
# End state: the 31 canonical academic departments all exist with
# kind="academic" (one renamed in place, thirty newly created), and the 6
# pre-existing administrative-office rows Categories depend on are
# preserved with kind="administrative" rather than deleted. This is a
# deliberate, disclosed deviation from a literal "delete everything not
# in the 31-name list" reading of the request -- that reading would
# destroy real Category/Issue data through the CASCADE FK described
# above.

from django.db import migrations

ACADEMIC = "academic"
ADMINISTRATIVE = "administrative"

# The 31 real academic departments at FUPRE. Mirrors
# frontend/src/types/index.ts::ACADEMIC_DEPARTMENTS exactly.
ACADEMIC_DEPARTMENTS = [
    "Biochemistry",
    "Chemistry",
    "Environmental Management & Toxicology",
    "Geology",
    "Applied Geophysics",
    "Industrial Chemistry",
    "Mathematics",
    "Petroleum Chemistry",
    "Physics",
    "Science Laboratory Technology",
    "Statistics",
    "Chemical Engineering",
    "Civil Engineering",
    "Computer Engineering",
    "Electrical/Electronic Engineering",
    "Marine Engineering",
    "Mechanical Engineering",
    "Natural Gas Engineering",
    "Petrochemical Engineering",
    "Petroleum Engineering",
    "Computer Science",
    "Cyber Security",
    "Data Science",
    "Information Technology",
    "Software Engineering",
    "Maritime Economics & Finance",
    "Maritime Transport & Logistics",
    "Entrepreneurship",
    "Logistics & Supply Chain Management",
    "Petroleum Information Management",
    "Procurement Management",
]

# Pre-existing rows that real Category rows depend on via a CASCADE FK --
# corrected to kind=administrative, never deleted. See module docstring.
ADMINISTRATIVE_DEPARTMENTS = [
    "Bursary Office",
    "Exams and Records Unit",
    "ICT Unit",
    "Registry",
    "School Admin Office",
    "Student Affairs Office",
]

# The one existing row that IS one of the 31 academic departments above,
# renamed in place (id preserved) rather than deleted+recreated.
LEGACY_NAME_TO_CANONICAL = {
    "Department of Computer Science": "Computer Science",
}


def seed_academic_departments(apps, schema_editor):
    Department = apps.get_model("departments", "Department")

    # 1. Rename the one existing row that belongs in the academic list,
    #    in place -- preserves its id, so Category.department_id values
    #    already pointing at it remain correct.
    for old_name, canonical_name in LEGACY_NAME_TO_CANONICAL.items():
        Department.objects.filter(name=old_name).update(name=canonical_name, kind=ACADEMIC)

    # 2. Correct kind on the pre-existing administrative-office rows.
    #    Deliberately not deleted -- see module docstring.
    Department.objects.filter(name__in=ADMINISTRATIVE_DEPARTMENTS).update(kind=ADMINISTRATIVE)

    # 3. Ensure every one of the 31 canonical academic departments exists.
    #    update_or_create() keyed on name is idempotent: a second run (or
    #    running against a database where some of these already exist)
    #    finds the matching row and leaves it alone instead of creating a
    #    duplicate.
    for name in ACADEMIC_DEPARTMENTS:
        Department.objects.update_or_create(
            name=name,
            defaults={"kind": ACADEMIC},
        )


def noop_reverse(apps, schema_editor):
    # Not reversed, for the same reason categories/migrations/0005 isn't:
    # this migration renames a row in place and corrects/creates others --
    # there is no prior state to restore that wouldn't risk re-breaking
    # the Category FKs it fixed.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("departments", "0003_alter_department_options_department_kind_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_academic_departments, reverse_code=noop_reverse),
    ]
