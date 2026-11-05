from django.contrib import admin
from django.contrib.auth.models import User

from .models import Department
from accounts.models import UserProfile


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):

    list_display = ("name", "kind", "assigned_officer")
    list_filter = ("kind",)
    search_fields = ("name",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if db_field.name == "assigned_officer":

            staff_user_ids = UserProfile.objects.exclude(
                role='student'
            ).values_list(
                'user_id',
                flat=True
            )

            kwargs["queryset"] = User.objects.filter(
                id__in=staff_user_ids
            )

        return super().formfield_for_foreignkey(
            db_field,
            request,
            **kwargs
        )
# Register your models here.
