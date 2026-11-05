from django.contrib import admin
from django.contrib.auth.models import User

from .models import Issue, IssueDocument, IssueActivity 
from accounts.models import UserProfile

admin.site.site_header = "Student Issue Management System"
admin.site.site_title = "SIMS Administration"
admin.site.index_title = "Administration" 

@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if db_field.name == "assigned_to":

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


admin.site.register(IssueDocument)
admin.site.register(IssueActivity)