from django.contrib import admin, messages

from .models import Course, Lesson, Quiz, QuizChoice, QuizQuestion, Section


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1


class SectionInline(admin.TabularInline):
    model = Section
    extra = 1


class QuizInline(admin.TabularInline):
    model = Quiz
    extra = 0


class QuizChoiceInline(admin.TabularInline):
    model = QuizChoice
    extra = 2


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "instructor", "status"]
    list_filter = ["status"]
    inlines = [SectionInline, QuizInline]
    actions = ["approve_courses"]

    @admin.action(description="Approve selected courses")
    def approve_courses(self, request, queryset):
        not_ready = queryset.exclude(status=Course.Status.PENDING_REVIEW)
        if not_ready.exists():
            self.message_user(
                request,
                "Only courses with status 'Pending review' can be approved. "
                f"Skipped {not_ready.count()} course(s).",
                level=messages.WARNING,
            )

        ready = queryset.filter(status=Course.Status.PENDING_REVIEW)
        updated = ready.update(status=Course.Status.PUBLISHED)
        self.message_user(request, f"Approved {updated} course(s).", level=messages.SUCCESS)


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ["title", "course", "order"]
    inlines = [LessonInline]


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ["text", "quiz", "order"]
    inlines = [QuizChoiceInline]