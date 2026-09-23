import uuid

from django.db import models

from apps.catalog.models import Event
from apps.employees.models import Employee


class RecommendationSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="recommendations")
    event = models.ForeignKey(Event, on_delete=models.PROTECT)
    rank = models.PositiveSmallIntegerField()
    score = models.DecimalField(max_digits=6, decimal_places=5)
    explanation = models.JSONField(default=dict)
    engine_version = models.CharField(max_length=32, default="hybrid-v1")
    context_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["rank"]
        indexes = [models.Index(fields=["employee", "context_hash"])]

    def __str__(self) -> str:
        return f"{self.employee_id}: #{self.rank} {self.event_id}"
