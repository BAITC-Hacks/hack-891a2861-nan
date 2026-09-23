from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import parsers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsHROrDemo
from apps.imports.services import DatasetValidationError, import_dataset


class DatasetImportView(APIView):
    permission_classes = [IsHROrDemo]
    parser_classes = [parsers.MultiPartParser]

    @extend_schema(
        operation_id="dataset_import",
        request={"multipart/form-data": OpenApiTypes.OBJECT},
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        required = ["employees", "skills", "events", "history"]
        missing = [name for name in required if name not in request.FILES]
        if missing:
            return Response(
                {"error": {"code": "missing_files", "details": missing}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for file in request.FILES.values():
            if file.size > 10 * 1024 * 1024:
                return Response(
                    {"error": {"code": "file_too_large", "details": file.name}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        try:
            counts = import_dataset(
                employees_file=request.FILES["employees"],
                skills_file=request.FILES["skills"],
                events_file=request.FILES["events"],
                history_file=request.FILES["history"],
            )
        except DatasetValidationError as exc:
            return Response(
                {"error": {"code": "invalid_dataset", "details": exc.errors}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"status": "imported", "counts": counts}, status=status.HTTP_201_CREATED)
