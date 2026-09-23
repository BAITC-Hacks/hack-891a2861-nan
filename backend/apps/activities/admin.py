from django.contrib import admin

from .models import ActivityHistory, SkillChangeLog

admin.site.register([ActivityHistory, SkillChangeLog])
