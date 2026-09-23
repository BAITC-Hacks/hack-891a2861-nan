from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.services import dashboard
from apps.core.permissions import IsHROrDemo
from apps.employees.views import request_locale


class HRDashboardView(APIView):
    permission_classes = [IsHROrDemo]

    def get(self, request):
        return Response(dashboard(request_locale(request)))
