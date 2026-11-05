# Hand-written to accompany the workflow engine (issues/workflow/).
#
# Why this migration exists: the 12 category workflows require six staff
# roles that had no equivalent in accounts.constants.ROLE_CHOICES --
# Department Admin, Lecturer, Bursary, Registry, School Admin Office, and
# Department Examination Officer (see issues/workflow/definitions.py for
# where each is used). UserProfile.role is a plain CharField, so this is a
# state-only change: SQLite never enforced the old choices as a DB-level
# CHECK constraint, so no data migration or column change is needed, but
# Django's migration history still needs to record the new choices list to
# stay in sync with accounts/models.py and accounts/constants.py.
#
# max_length=50 already comfortably fits every new role code (longest is
# "school_admin_office" at 20 characters), so it is left unchanged.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_userprofile_must_change_password_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='role',
            field=models.CharField(
                choices=[
                    ('student', 'Student'),
                    ('course_adviser', 'Course Adviser'),
                    ('hod', 'HOD'),
                    ('ict_officer', 'ICT Officer'),
                    ('exams_officer', 'Exams Officer'),
                    ('student_affairs_officer', 'Student Affairs Officer'),
                    ('admin', 'Admin'),
                    ('department_admin', 'Department Admin'),
                    ('lecturer', 'Lecturer'),
                    ('bursary', 'Bursary'),
                    ('registry', 'Registry'),
                    ('school_admin_office', 'School Admin Office'),
                    ('dept_exam_officer', 'Department Examination Officer'),
                ],
                default='student',
                max_length=50,
            ),
        ),
    ]
