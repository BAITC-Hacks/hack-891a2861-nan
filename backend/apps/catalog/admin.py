from django.contrib import admin

from .models import Event, EventSkillGain, Grade, GradeRequirement, Role, Skill

admin.site.register([Role, Grade, Skill, GradeRequirement, Event, EventSkillGain])
