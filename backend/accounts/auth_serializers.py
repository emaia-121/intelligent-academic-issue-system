from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken


class EmailTokenObtainPairSerializer(serializers.Serializer):

    email = serializers.EmailField()

    password = serializers.CharField(write_only=True)

    def validate(self, attrs):

        email = attrs["email"].strip().lower()
        password = attrs["password"].strip() 

        try:
            user = User.objects.get(email__iexact=email)

        except User.DoesNotExist:

            raise serializers.ValidationError(
                {
                    "email": "No account exists with this email address."
                }
            )

        authenticated_user = authenticate(
            username=user.username,
            password=password,
        )

        if authenticated_user is None:

            raise serializers.ValidationError(
                {
                    "password": "Incorrect password."
                }
            )

        refresh = RefreshToken.for_user(authenticated_user)

        profile = authenticated_user.userprofile

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": authenticated_user.id,
                "first_name": authenticated_user.first_name,
                "last_name": authenticated_user.last_name,
                "email": authenticated_user.email,
                "role": profile.role,
                "must_change_password": profile.must_change_password,
            },
        } 