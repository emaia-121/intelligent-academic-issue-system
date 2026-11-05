from rest_framework.permissions import BasePermission

from accounts.constants import ROLE_ADMIN

class IsSystemAdmin(BasePermission):

    message = "Only system administrators can perform this action."

    def has_permission(self, request, view):

        if not request.user.is_authenticated:
            return False

        try:
            profile = request.user.userprofile

        except Exception:
            return False

        return profile.role == ROLE_ADMIN 