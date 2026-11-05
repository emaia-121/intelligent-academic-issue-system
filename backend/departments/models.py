from django.db import models
from django.contrib.auth.models import User

ACADEMIC = "academic"
ADMINISTRATIVE = "administrative"

KIND_CHOICES = (
    (ACADEMIC, "Academic"),
    (ADMINISTRATIVE, "Administrative"),
)

class Department(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    # Discriminator between real academic departments (Computer Science,
    # Chemistry, ...) and administrative offices (Bursary, Registry, ...).
    # Display-only for now, same as the rest of this model -- nothing in
    # the workflow engine reads it. Defaults to ACADEMIC so every existing
    # row remains valid without a data migration (see the Department
    # Architecture Review: Department itself is not yet the routing
    # mechanism, so this is purely additive).
    kind = models.CharField(
        max_length=20,
        choices=KIND_CHOICES,
        default=ACADEMIC,
    )

    assigned_officer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_departments",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_kind_display()})"
# Create your models here.
