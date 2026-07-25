from django.contrib import admin

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


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ["title", "course", "order"]
    inlines = [LessonInline]


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ["text", "quiz", "order"]
    inlines = [QuizChoiceInline]