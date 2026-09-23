import uuid

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.activities.services import complete_activity
from apps.catalog.models import Event
from apps.core.permissions import IsAuthenticatedOrDemo, can_access_employee
from apps.employees.models import Employee


class CompleteActivityView(APIView):
    permission_classes = [IsAuthenticatedOrDemo]

    def post(self, request, employee_id: str, event_id: str):
        if not can_access_employee(request, employee_id):
            raise PermissionDenied("You cannot update this employee profile")
        employee = get_object_or_404(Employee, pk=employee_id)
        event = get_object_or_404(Event.objects.prefetch_related("skill_gains__skill"), pk=event_id)
        key = request.headers.get("Idempotency-Key") or str(uuid.uuid4())
        try:
            result = complete_activity(employee, event, key)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(result, status=status.HTTP_200_OK)
