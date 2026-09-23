from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAuthenticatedOrDemo, can_access_employee
from apps.employees.models import Employee
from apps.employees.serializers import (
    ActivitySerializer,
    EmployeeListSerializer,
    EmployeeSkillSerializer,
)
from apps.employees.services import trajectory_for


def request_locale(request) -> str:
    locale = request.query_params.get("locale", "en")
    return locale if locale in {"en", "ru", "kk"} else "en"


class EmployeeListView(APIView):
    permission_classes = [IsAuthenticatedOrDemo]

    def get(self, request):
        employees = Employee.objects.select_related("role", "grade")
        return Response(EmployeeListSerializer(employees, many=True).data)


class EmployeeDetailView(APIView):
    permission_classes = [IsAuthenticatedOrDemo]

    def get(self, request, employee_id: str):
        if not can_access_employee(request, employee_id):
            raise PermissionDenied("You cannot access this employee profile")
        locale = request_locale(request)
        employee = get_object_or_404(
            Employee.objects.select_related("role", "grade").prefetch_related(
                "skill_levels__skill", "activities__event"
            ),
            pk=employee_id,
        )
        return Response(
            {
                "employee_id": employee.employee_id,
                "display_name": employee.display_name,
                "role": {
                    "code": employee.role_id,
                    "name": employee.role.localized_name(locale),
                },
                "grade": {
                    "code": employee.grade.code,
                    "name": employee.grade.localized_name(locale),
                },
                "tenure_months": employee.tenure_months,
                "organisation_unit": employee.organisation_unit,
                "skills": EmployeeSkillSerializer(
                    employee.skill_levels.all(), many=True, context={"locale": locale}
                ).data,
                "activities": ActivitySerializer(
                    employee.activities.all()[:20], many=True, context={"locale": locale}
                ).data,
                "trajectory": trajectory_for(employee, locale),
            }
        )
