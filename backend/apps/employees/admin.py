from django.contrib import admin

from .models import Employee, EmployeeSkill

admin.site.register([Employee, EmployeeSkill])
