from django.conf import settings
from rest_framework.permissions import BasePermission


class IsAuthenticatedOrDemo(BasePermission):
    def has_permission(self, request, view) -> bool:
        return bool(getattr(settings, "DEMO_MODE", False) or request.user.is_authenticated)


class IsHROrDemo(BasePermission):
    def has_permission(self, request, view) -> bool:
        if getattr(settings, "DEMO_MODE", False):
            return request.headers.get("X-Demo-Role", "hr") in {"hr", "admin"}
        return bool(request.user.is_authenticated and request.user.role in {"hr", "admin"})


def can_access_employee(request, employee_id: str) -> bool:
    if getattr(settings, "DEMO_MODE", False):
        role = request.headers.get("X-Demo-Role", "employee")
        selected = request.headers.get("X-Employee-ID", employee_id)
        return role in {"hr", "admin"} or selected == employee_id
    if not request.user.is_authenticated:
        return False
    if request.user.role in {"hr", "admin"}:
        return True
    profile = getattr(request.user, "employee_profile", None)
    return bool(profile and profile.employee_id == employee_id)
