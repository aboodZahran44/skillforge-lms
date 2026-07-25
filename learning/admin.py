from django.contrib import admin

from .models import Enrollment, LessonEvent


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ["user", "course", "organization", "enrolled_at"]
    list_filter = ["organization", "course"]


@admin.register(LessonEvent)
class LessonEventAdmin(admin.ModelAdmin):
    list_display = ["enrollment", "lesson", "event_type", "created_at"]
    list_filter = ["event_type"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False