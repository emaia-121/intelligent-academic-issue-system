from django.urls import path

from .views import DepartmentListAPIView

urlpatterns = [
    path(
        "",
        DepartmentListAPIView.as_view(),
        name="department-list"
    ),
]
