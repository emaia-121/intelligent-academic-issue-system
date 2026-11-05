ROLE_STUDENT = "student"
ROLE_COURSE_ADVISER = "course_adviser"
ROLE_HOD = "hod"
ROLE_ICT_OFFICER = "ict_officer"
ROLE_EXAMS_OFFICER = "exams_officer"
ROLE_STUDENT_AFFAIRS_OFFICER = "student_affairs_officer"
ROLE_ADMIN = "admin"

# Added to support the workflow engine's 12 category workflows. Each of
# these roles is a real destination in at least one category's forward
# chain, backward transitions, or final-authority set (see
# issues/workflow/definitions.py) and had no existing equivalent above.
ROLE_DEPARTMENT_ADMIN = "department_admin"
ROLE_LECTURER = "lecturer"
ROLE_BURSARY = "bursary"
ROLE_REGISTRY = "registry"
ROLE_SCHOOL_ADMIN_OFFICE = "school_admin_office"
ROLE_DEPT_EXAM_OFFICER = "dept_exam_officer"


ROLE_CHOICES = [
    (ROLE_STUDENT, "Student"),
    (ROLE_COURSE_ADVISER, "Course Adviser"),
    (ROLE_HOD, "HOD"),
    (ROLE_ICT_OFFICER, "ICT Officer"),
    (ROLE_EXAMS_OFFICER, "Exams Officer"),
    (ROLE_STUDENT_AFFAIRS_OFFICER, "Student Affairs Officer"),
    (ROLE_ADMIN, "Admin"),
    (ROLE_DEPARTMENT_ADMIN, "Department Admin"),
    (ROLE_LECTURER, "Lecturer"),
    (ROLE_BURSARY, "Bursary"),
    (ROLE_REGISTRY, "Registry"),
    (ROLE_SCHOOL_ADMIN_OFFICE, "School Admin Office"),
    (ROLE_DEPT_EXAM_OFFICER, "Department Examination Officer"),
]


STAFF_ROLE_CHOICES = [
    role
    for role in ROLE_CHOICES
    if role[0] != ROLE_STUDENT
] 