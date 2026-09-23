import uuid

from django.db import models

from apps.catalog.models import Event, Skill
from apps.employees.models import Employee


class ActivityHistory(models.Model):
    class Status(models.TextChoices):
        REGISTERED = "registered", "Registered"
        COMPLETED = "completed", "Completed"
        MISSED = "missed", "Missed"
        DECLINED = "declined", "Declined"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="activities")
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="participations")
    status = models.CharField(max_length=16, choices=Status.choices)
    occurred_at = models.DateTimeField()
    completed_on_time = models.BooleanField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=128, null=True, blank=True, unique=True)
    source = models.CharField(max_length=32, default="dataset")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [models.Index(fields=["employee", "status"])]

    def __str__(self) -> str:
        return f"{self.employee_id}: {self.event_id} ({self.status})"


class SkillChangeLog(models.Model):
    activity = models.ForeignKey(
        ActivityHistory, on_delete=models.CASCADE, related_name="skill_changes"
    )
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT)
    before_level = models.PositiveSmallIntegerField()
    after_level = models.PositiveSmallIntegerField()
    rule_version = models.CharField(max_length=16, default="v1")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["activity", "skill"], name="unique_activity_skill_change"
            )
        ]

    def __str__(self) -> str:
        return f"{self.skill_id}: {self.before_level} → {self.after_level}"
