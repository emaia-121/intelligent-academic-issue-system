from rest_framework.generics import ListAPIView

from .models import Department
from .serializers import DepartmentSerializer


class DepartmentListAPIView(ListAPIView):
    """GET /api/departments/ -- read-only list of every Department, ordered
    by kind then name (academic departments, then administrative offices,
    alphabetical within each group).

    Authenticated only, via the project's default DRF permission
    (IsAuthenticated -- see REST_FRAMEWORK in
    student_issue_system/settings.py); deliberately not restricted to
    admins, since students and staff both need a real department list
    (registration, staff creation, ...), not just administrators.

    A single, unfiltered queryset -- no select_related()/prefetch_related(),
    since DepartmentSerializer reads no related fields (assigned_officer is
    intentionally excluded from the response).
    """

    serializer_class = DepartmentSerializer
    queryset = Department.objects.all().order_by("kind", "name")
# Create your views here.
