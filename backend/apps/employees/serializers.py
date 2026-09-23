from rest_framework import serializers

from apps.activities.models import ActivityHistory
from apps.employees.models import Employee, EmployeeSkill


class EmployeeListSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="role.name_en")
    grade = serializers.CharField(source="grade.name_en")

    class Meta:
        model = Employee
        fields = [
            "employee_id",
            "display_name",
            "role",
            "grade",
            "tenure_months",
            "organisation_unit",
        ]


class EmployeeSkillSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source="skill_id")
    name = serializers.SerializerMethodField()
    kind = serializers.CharField(source="skill.kind")

    class Meta:
        model = EmployeeSkill
        fields = ["code", "name", "kind", "level"]

    def get_name(self, obj) -> str:
        return obj.skill.localized_name(self.context.get("locale", "en"))


class ActivitySerializer(serializers.ModelSerializer):
    event_code = serializers.CharField(source="event_id")
    event_name = serializers.SerializerMethodField()

    class Meta:
        model = ActivityHistory
        fields = ["id", "event_code", "event_name", "status", "occurred_at", "completed_on_time"]

    def get_event_name(self, obj) -> str:
        return obj.event.localized_name(self.context.get("locale", "en"))
