from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAuthenticatedOrDemo, can_access_employee
from apps.employees.models import Employee
from apps.employees.views import request_locale
from apps.recommendations.engine import recommend


class EmployeeRecommendationsView(APIView):
    permission_classes = [IsAuthenticatedOrDemo]

    def get(self, request, employee_id: str):
        if not can_access_employee(request, employee_id):
            raise PermissionDenied("You cannot access this employee profile")
        employee = get_object_or_404(
            Employee.objects.select_related("role", "grade"), pk=employee_id
        )
        return Response(
            {
                "employee_id": employee.employee_id,
                "recommendations": recommend(employee, request_locale(request)),
            }
        )
