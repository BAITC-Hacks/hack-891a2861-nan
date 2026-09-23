from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import issue_token
from .serializers import LoginSerializer


def user_payload(user) -> dict:
    employee = getattr(user, "employee_profile", None)
    return {
        "id": user.pk,
        "username": user.username,
        "role": user.role,
        "employee_id": employee.employee_id if employee else None,
        "display_name": employee.display_name if employee else (user.get_full_name() or user.username),
    }


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, responses={200: dict})
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        return Response({"token": issue_token(user), "user": user_payload(user)})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        return Response(user_payload(request.user))
