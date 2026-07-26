from django.apps import apps


def is_course_complete(enrollment):
    Lesson = apps.get_model("catalog", "Lesson")
    total_lessons = Lesson.objects.filter(section__course_id=enrollment.course_id).count()

    if total_lessons == 0:
        return False

    from .models import LessonEvent

    completed_lesson_ids = set(
        enrollment.events.filter(
            event_type=LessonEvent.EventType.COMPLETED
        ).values_list("lesson_id", flat=True)
    )
    return len(completed_lesson_ids) >= total_lessons