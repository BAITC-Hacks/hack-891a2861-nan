from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class LocalizedModel(models.Model):
    name_en = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255, blank=True)
    name_kk = models.CharField(max_length=255, blank=True)

    class Meta:
        abstract = True

    def localized_name(self, locale: str = "en") -> str:
        value = getattr(self, f"name_{locale}", "")
        return value or self.name_ru or self.name_en


class Role(LocalizedModel):
    code = models.CharField(max_length=64, primary_key=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name_en


class Grade(LocalizedModel):
    code = models.CharField(max_length=64)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="grades")
    rank = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["role_id", "rank"]
        constraints = [
            models.UniqueConstraint(fields=["role", "code"], name="unique_grade_code_per_role"),
            models.UniqueConstraint(fields=["role", "rank"], name="unique_grade_rank_per_role"),
        ]

    def __str__(self) -> str:
        return f"{self.role_id}: {self.name_en}"


class Skill(LocalizedModel):
    class Kind(models.TextChoices):
        HARD = "hard", "Hard skill"
        SOFT = "soft", "Soft skill"

    code = models.CharField(max_length=64, primary_key=True)
    kind = models.CharField(max_length=8, choices=Kind.choices)
    description_en = models.TextField(blank=True)
    description_ru = models.TextField(blank=True)
    description_kk = models.TextField(blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name_en


class GradeRequirement(models.Model):
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name="requirements")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="grade_requirements")
    required_level = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    priority = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1)])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["grade", "skill"], name="unique_grade_skill"),
            models.CheckConstraint(
                condition=models.Q(required_level__gte=0, required_level__lte=5),
                name="grade_required_level_0_5",
            ),
            models.CheckConstraint(
                condition=models.Q(priority__gte=1), name="grade_priority_positive"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.grade}: {self.skill_id} ≥ {self.required_level}"


class Event(LocalizedModel):
    class Format(models.TextChoices):
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"
        SELF_PACED = "self_paced", "Self-paced"

    code = models.CharField(max_length=64, primary_key=True)
    event_type = models.CharField(max_length=64)
    format = models.CharField(max_length=16, choices=Format.choices, default=Format.ONLINE)
    description_en = models.TextField(blank=True)
    description_ru = models.TextField(blank=True)
    description_kk = models.TextField(blank=True)
    duration_hours = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    is_mandatory = models.BooleanField(default=False)
    repeatable = models.BooleanField(default=False)
    prerequisites = models.JSONField(default=dict, blank=True)
    upcoming_sessions = models.JSONField(default=list, blank=True)
    available_from = models.DateField(null=True, blank=True)
    available_until = models.DateField(null=True, blank=True)
    audience_roles = models.ManyToManyField(Role, blank=True, related_name="events")
    audience_grades = models.ManyToManyField(Grade, blank=True, related_name="events")

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name_en


class EventSkillGain(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="skill_gains")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="event_gains")
    gain = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    max_level = models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "skill"], name="unique_event_skill_gain"),
            models.CheckConstraint(
                condition=models.Q(gain__gte=1, gain__lte=5), name="event_gain_1_5"
            ),
            models.CheckConstraint(
                condition=models.Q(max_level__gte=1, max_level__lte=5),
                name="event_max_level_1_5",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event_id}: {self.skill_id} +{self.gain}"
