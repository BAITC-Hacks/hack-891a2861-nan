from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CareerQuestUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Career Quest", {"fields": ("role", "organisation_unit")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Career Quest", {"fields": ("role", "organisation_unit")}),
    )
    list_display = (*UserAdmin.list_display, "role", "organisation_unit")
    list_filter = (*UserAdmin.list_filter, "role")
