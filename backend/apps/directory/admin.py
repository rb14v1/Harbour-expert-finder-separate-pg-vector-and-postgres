from django.contrib import admin

from apps.directory.models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ["id", "full_name", "department", "title", "user"]
    search_fields = ["full_name", "department", "title", "skills_summary"]
    list_filter = ["department"]
