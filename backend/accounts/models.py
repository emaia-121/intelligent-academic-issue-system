from django.core.exceptions import ValidationError 
from django.db import models
from django.contrib.auth.models import User

from accounts.constants import (
    ROLE_CHOICES,
    ROLE_STUDENT,
    ROLE_ADMIN, 
)

from departments.models import Department
from issues.workflow.definitions import DEPARTMENT_SCOPED_ROLES 

class UserProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default=ROLE_STUDENT 
    )

    must_change_password = models.BooleanField(
        default=False
    )

    matric_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True
    )

    staff_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    department_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    level = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    def clean(self):
        super().clean()

        department_name = (self.department_name or "").strip()

        # Admin accounts may legitimately have no department.
        if self.role == ROLE_ADMIN and not department_name:
            return

        # Students and department-scoped staff must belong to
        # a valid academic department.
        if self.role == ROLE_STUDENT or self.role in DEPARTMENT_SCOPED_ROLES:
            if not department_name:
                raise ValidationError({
                    "department_name": (
                        "A valid academic department is required for "
                        "this role."
                    )
                })

            department = Department.objects.filter(
                name__iexact=department_name,
                kind="academic"
            ).first()

            if department is None:
                raise ValidationError({
                    "department_name": (
                        "Please select a valid academic department."
                    )
                })

            self.department_name = department.name
            return

        # Central staff roles must have a valid department.
        if not department_name:
            raise ValidationError({
                "department_name": (
                    "A valid department is required for this staff role."
                )
            })

        department = Department.objects.filter(
            name__iexact=department_name
        ).first()

        if department is None:
            raise ValidationError({
                "department_name": (
                    "Please select a valid department."
                )
            })

        self.department_name = department.name

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username
# Create your models here.

