from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAuthenticatedOrDemo, can_access_employee
from apps.employees.models import Employee
from apps.employees.services import next_grade_for
from apps.recommendations.engine import recommend
from apps.recommendations.llm import build_evidence, explain_recommendations


class EmployeeRecommendationsView(APIView):
    permission_classes = [IsAuthenticatedOrDemo]

    @extend_schema(operation_id="employee_recommendations", responses={200: OpenApiTypes.OBJECT})
    def get(self, request, employee_id: str):
        if not can_access_employee(request, employee_id):
            raise PermissionDenied("You cannot access this employee profile")
        employee = get_object_or_404(
            Employee.objects.select_related("role", "grade"), pk=employee_id
        )
        locale = employee.locale if employee.locale in {"en", "ru", "kk"} else "en"
        recommendations = recommend(employee, locale)
        target = next_grade_for(employee)
        ai_explanation = None
        if target and recommendations:
            history = list(
                employee.activities.select_related("event")
                .prefetch_related("event__skill_gains")
                .order_by("-occurred_at")[:50]
            )
            evidence = build_evidence(employee, target, recommendations, history, locale)
            ai_explanation = explain_recommendations(evidence).model_dump()
        return Response(
            {
                "employee_id": employee.employee_id,
                "recommendations": recommendations,
                "ai_explanation": ai_explanation,
            }
        )
