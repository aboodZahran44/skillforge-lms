from django.contrib import admin

from .models import LessonChunk


@admin.register(LessonChunk)
class LessonChunkAdmin(admin.ModelAdmin):
    list_display = ["lesson", "course", "order"]
    list_filter = ["course"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False