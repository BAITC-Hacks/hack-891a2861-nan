from django.urls import path

from apps.activities.views import CompleteActivityView
from apps.accounts.views import LoginView, MeView
from apps.analytics.views import HRDashboardView
from apps.employees.views import EmployeeDetailView, EmployeeListView
from apps.imports.views import DatasetImportView
from apps.recommendations.views import EmployeeRecommendationsView

from .views import HealthLiveView, HealthReadyView, MetaView

urlpatterns = [
    path("health/live/", HealthLiveView.as_view(), name="health-live"),
    path("health/ready/", HealthReadyView.as_view(), name="health-ready"),
    path("meta/", MetaView.as_view(), name="meta"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("employees/", EmployeeListView.as_view(), name="employee-list"),
    path("employees/<str:employee_id>/", EmployeeDetailView.as_view(), name="employee-detail"),
    path(
        "employees/<str:employee_id>/recommendations/",
        EmployeeRecommendationsView.as_view(),
        name="employee-recommendations",
    ),
    path(
        "employees/<str:employee_id>/activities/<str:event_id>/complete/",
        CompleteActivityView.as_view(),
        name="activity-complete",
    ),
    path("hr/dashboard/", HRDashboardView.as_view(), name="hr-dashboard"),
    path("admin/import/", DatasetImportView.as_view(), name="dataset-import"),
]
