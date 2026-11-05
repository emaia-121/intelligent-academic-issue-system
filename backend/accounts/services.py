from django.db import transaction
from django.contrib.auth.models import User

from accounts.models import UserProfile

from accounts.utils import generate_temporary_password
from accounts.constants import ROLE_STUDENT 

@transaction.atomic
def create_staff_account(validated_data):
    """
    Creates a staff account.

    Creates:
        - Django User
        - UserProfile

    Generates a secure temporary password.

    Returns:
        user
        profile
        temporary_password
    """

    email = validated_data.pop("email")

    first_name = validated_data.pop("first_name")

    last_name = validated_data.pop("last_name")

    role = validated_data.pop("role")

    phone_number = validated_data.pop("phone_number")

    department_name = validated_data.pop("department_name")

    staff_id = validated_data.pop("staff_id")

    temporary_password = generate_temporary_password()

    user = User.objects.create(
        username=email,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )

    user.set_password(temporary_password)
    user.save()

    profile = UserProfile.objects.create(
        user=user,
        role=role,
        phone_number=phone_number,
        department_name=department_name,
        staff_id=staff_id,
        must_change_password=True
    )

    return {
        "user": user,
        "profile": profile,
        "temporary_password": temporary_password
    }

@transaction.atomic
def create_student_account(validated_data):
    """
    Creates a new student account.

    Creates both:
        - Django User
        - UserProfile

    Everything is executed inside a database transaction.
    """

    validated_data.pop("confirm_password")

    password = validated_data.pop("password")

    email = validated_data.pop("email")

    first_name = validated_data.pop("first_name")

    last_name = validated_data.pop("last_name")

    matric_number = validated_data.pop("matric_number")

    phone_number = validated_data.pop("phone_number")

    department_name = validated_data.pop("department_name")

    level = validated_data.pop("level")

    user = User.objects.create(
        username=email,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )

    user.set_password(password)
    user.save()

    profile = UserProfile.objects.create(
        user=user,
        role=ROLE_STUDENT,
        matric_number=matric_number,
        phone_number=phone_number,
        department_name=department_name,
        level=level,
    )

    return {
        "user": user,
        "profile": profile,
    }

@transaction.atomic
def change_password(user, validated_data):
    current_password = validated_data["current_password"]

    new_password = validated_data["new_password"]

    confirm_new_password = validated_data["confirm_new_password"]

    if not user.check_password(current_password):
        raise ValueError(
            "Current password is incorrect."
        )

    user.set_password(new_password)
    user.save()

    profile = user.userprofile

    profile.must_change_password = False
    profile.save()

    return {
        "success": True
    }
