from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.core.exceptions import ValidationError

from accounts.serializers import StudentRegistrationSerializer
from accounts.services import create_student_account

from accounts.serializers import StaffAccountCreationSerializer
from accounts.services import create_staff_account 

from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.auth_serializers import EmailTokenObtainPairSerializer

from accounts.permissions import IsSystemAdmin 

from rest_framework.permissions import IsAuthenticated

from accounts.serializers import ChangePasswordSerializer

from accounts.services import change_password

from accounts.constants import ROLE_STUDENT
from accounts.models import UserProfile


class StaffDirectoryAPIView(APIView):
    """GET /api/accounts/staff/directory/ -- admin-only, read-only list of
    every staff account (every UserProfile whose role isn't 'student').

    Added specifically to support the Administrative Assignment Management
    feature's "pick an officer to manually assign" control -- without
    this, an admin has no way to discover which User id to pass to
    IssueManualAssignAPIView (issues/views.py). Reuses the exact
    staff-filtering query already duplicated in departments/admin.py and
    issues/admin.py (formfield_for_foreignkey's `UserProfile.objects.exclude(role='student')`)
    rather than introducing new filtering logic.
    """

    permission_classes = [IsSystemAdmin]

    def get(self, request):

        profiles = UserProfile.objects.exclude(
            role=ROLE_STUDENT
        ).select_related("user").order_by("user__first_name", "user__last_name")

        data = [
            {
                "id": profile.user.id,
                "first_name": profile.user.first_name,
                "last_name": profile.user.last_name,
                "email": profile.user.email,
                "role": profile.role,
                "department_name": profile.department_name,
            }
            for profile in profiles
        ]

        return Response(
            {
                "success": True,
                "message": "Staff directory retrieved successfully.",
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


class StaffAccountCreationView(APIView):

    permission_classes = [IsSystemAdmin] 

    def post(self, request):

        serializer = StaffAccountCreationSerializer(
            data=request.data
        )

        if not serializer.is_valid():

            return Response(
                {
                    "success": False,
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = create_staff_account(
            serializer.validated_data
        )

        user = result["user"]
        profile = result["profile"]

        return Response(
            {
                "success": True,
                "message": "Staff account created successfully.",
                "data": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "role": profile.role,
                    "temporary_password": result["temporary_password"],
                },
            },
            status=status.HTTP_201_CREATED,
        ) 

class StudentRegistrationView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        serializer = StudentRegistrationSerializer(
            data=request.data
        )

        if not serializer.is_valid():

            return Response(
                {
                    "success": False,
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = create_student_account(
            serializer.validated_data
        )

        user = result["user"]
        profile = result["profile"]

        return Response(
            {
                "success": True,
                "message": "Registration successful.",
                "data": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "role": profile.role,
                },
            },
            status=status.HTTP_201_CREATED,
        )

class EmailLoginView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        serializer = EmailTokenObtainPairSerializer(
            data=request.data
        )

        if not serializer.is_valid():

            return Response(
                {
                    "success": False,
                    "message": "Login failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {
                "success": True,
                "message": "Login successful.",
                "data": serializer.validated_data,
            },
            status=status.HTTP_200_OK,
        ) 

class ChangePasswordView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = ChangePasswordSerializer(
            data=request.data
        )

        if not serializer.is_valid():

            return Response(
                {
                    "success": False,
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:

            change_password(
                request.user,
                serializer.validated_data,
            )

        except ValueError as error:

            return Response(
                {
                    "success": False,
                    "message": str(error),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except ValidationError as error:

            return Response(
                {
                    "success": False,
                    "message": "Account profile validation failed.",
                    "errors": error.message_dict,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "success": True,
                "message": "Password changed successfully.",
            },
            status=status.HTTP_200_OK,
        )


class CurrentUserProfileAPIView(APIView):
    """
    GET /api/accounts/me/

    Returns the authenticated user's own profile information.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.userprofile

        data = {
            "id": request.user.id,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
            "role": profile.role,
            "department_name": profile.department_name,
            "staff_id": profile.staff_id,
            "matric_number": profile.matric_number,
            "level": profile.level,
            "phone_number": profile.phone_number,
            "must_change_password": profile.must_change_password,
        }

        return Response(
            {
                "success": True,
                "message": "Profile retrieved successfully.",
                "data": data,
            },
            status=status.HTTP_200_OK,
        ) 