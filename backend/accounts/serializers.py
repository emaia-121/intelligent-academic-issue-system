from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from rest_framework import serializers

from accounts.models import UserProfile

from departments.models import Department

from accounts.constants import STAFF_ROLE_CHOICES 

from issues.workflow.definitions import DEPARTMENT_SCOPED_ROLES

class StudentRegistrationSerializer(serializers.Serializer):

    first_name = serializers.CharField(
        max_length=150
    )

    last_name = serializers.CharField(
        max_length=150
    )

    email = serializers.EmailField()

    matric_number = serializers.CharField(
        max_length=50
    )

    phone_number = serializers.CharField(
        max_length=20
    )

    department_name = serializers.CharField(
        max_length=100
    )

    level = serializers.CharField(
        max_length=20
    )

    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )

    confirm_password = serializers.CharField(
        write_only=True
    )

    def validate_email(self, value):

        normalized_email = value.strip().lower()

        if User.objects.filter(
            email__iexact=normalized_email
        ).exists():
            raise serializers.ValidationError(
                "An account with this email address already exists."
            )

        return normalized_email

    def validate_matric_number(self, value):

        normalized_matric_number = value.strip().upper()

        if UserProfile.objects.filter(
            matric_number__iexact=normalized_matric_number
        ).exists():
            raise serializers.ValidationError(
                "An account with this matriculation number already exists."
            )

        return normalized_matric_number

    def validate_phone_number(self, value):

        phone_number = value.strip()

        if not phone_number:
            raise serializers.ValidationError(
                "Phone number is required."
            )

        return phone_number

    def validate_department_name(self, value):

        normalized_name = value.strip()

        department = Department.objects.filter(
            name__iexact=normalized_name,
            kind="academic"
        ).first()

        if department is None:
            raise serializers.ValidationError(
                "Please select a valid academic department."
            )

        return department.name

    def validate(self, attrs):

        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {
                    "confirm_password": (
                        "Password and confirmation password do not match."
                    )
                }
            )

        return attrs

class StaffAccountCreationSerializer(serializers.Serializer): 

    first_name = serializers.CharField(
        max_length=150
    )

    last_name = serializers.CharField(
        max_length=150
    )

    email = serializers.EmailField()

    phone_number = serializers.CharField(
        max_length=20
    )

    department_name = serializers.CharField(
        max_length=100
    )

    staff_id = serializers.CharField(
        max_length=50
    )

    role = serializers.ChoiceField(
        choices=STAFF_ROLE_CHOICES
    )


    def validate_email(self, value):

        normalized_email = value.strip().lower()

        if User.objects.filter(
            email__iexact=normalized_email
        ).exists():

            raise serializers.ValidationError(
                "An account with this email address already exists."
            )

        return normalized_email

    def validate_staff_id(self, value):

        normalized_staff_id = value.strip().upper()

        if UserProfile.objects.filter(
            staff_id__iexact=normalized_staff_id
        ).exists():

            raise serializers.ValidationError(
                "An account with this staff ID already exists."
            )

        return normalized_staff_id

    def validate_phone_number(self, value):

        phone_number = value.strip()

        if not phone_number:

            raise serializers.ValidationError(
                "Phone number is required."
            )

        return phone_number 


    def validate_department_name(self, value):

        normalized_name = value.strip()

        department = Department.objects.filter(
            name__iexact=normalized_name
        ).first()

        if department is None:
            raise serializers.ValidationError(
                "Please select a valid department."
            )

        return department.name

    def validate(self, attrs):

        role = attrs["role"]
        department_name = attrs["department_name"]

        department = Department.objects.get(
            name=department_name
        )

        if role in DEPARTMENT_SCOPED_ROLES:
            if department.kind != "academic":
                raise serializers.ValidationError(
                    {
                        "department_name":
                            "This role must be assigned to an academic department."
                    }
                )

        
        return attrs

class ChangePasswordSerializer(serializers.Serializer):

    current_password = serializers.CharField(
        write_only=True
    )

    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )

    confirm_new_password = serializers.CharField(
        write_only=True
    )

    def validate(self, attrs):

        if attrs["new_password"] != attrs["confirm_new_password"]:

            raise serializers.ValidationError(
                {
                    "confirm_new_password":
                        "Password and confirmation password do not match."
                }
            )

        return attrs 