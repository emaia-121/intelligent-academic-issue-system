from rest_framework import serializers

from .models import Department


class DepartmentSerializer(serializers.ModelSerializer):
    """Minimal, read-only representation of a Department.

    Deliberately exposes only id/name/kind/description -- no
    assigned_officer, no timestamps, no computed fields. This is meant to
    become the single generic shape every future consumer reads from
    (student registration, staff creation, a future Department admin page,
    reports, department lookups), not a response tailored to one screen.
    """

    class Meta:
        model = Department
        fields = ["id", "name", "kind", "description"]
        read_only_fields = fields
