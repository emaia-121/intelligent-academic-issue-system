from django.urls import path

from accounts.views import (
    StudentRegistrationView,
    StaffAccountCreationView,
    StaffDirectoryAPIView,
    EmailLoginView,
    ChangePasswordView,
    CurrentUserProfileAPIView, 
)

urlpatterns = [
    path(
        "register/",
        StudentRegistrationView.as_view(),
        name="student-register",
    ),

    path(
        "login/",
        EmailLoginView.as_view(),
        name="email-login",
    ),

    path(
        "staff/",
        StaffAccountCreationView.as_view(),
        name="staff-account-create",
    ),

    path(
        "staff/directory/",
        StaffDirectoryAPIView.as_view(),
        name="staff-directory",
    ),

    path(
        "change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),

    path(
        "me/",
        CurrentUserProfileAPIView.as_view(),
        name="current-user-profile",
    ),
] 
