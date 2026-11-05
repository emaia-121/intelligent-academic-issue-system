from rest_framework.views import APIView

from issues.utils.api_response import success_response

from .models import Category


class CategoryListAPIView(APIView):
    """Read-only listing of the real, canonical Category table.

    Added to support the manual category selection exception path (see
    issues/views.py's CreateIssueAPIView): when the ML classifier reports
    medium confidence (student must confirm/reject) or low confidence
    (student must pick manually), the frontend needs the real list of
    categories to build a picker from. Before this endpoint existed there
    was no real category-listing API anywhere in the project -- the only
    place categories were listed was a client-side mock catalogue
    (frontend/src/api/mock/store.ts) that does not match the real,
    canonical Category rows at all. Any authenticated user may call this
    (students included, since they are the ones doing manual selection);
    it is read-only and exposes nothing sensitive.
    """

    def get(self, request):
        categories = Category.objects.select_related("department").all()

        data = [
            {
                "id": category.id,
                "name": category.name,
                "department": category.department.name,
            }
            for category in categories
        ]

        return success_response(
            data=data,
            message="Categories retrieved successfully.",
        )
