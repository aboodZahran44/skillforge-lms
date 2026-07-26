from django.db import transaction

from .models import Course
from .tasks import sync_course_to_index, sync_course_to_tutor_service_task


class CourseNotPendingReview(Exception):
    pass


def approve_course(course):
    if course.status != Course.Status.PENDING_REVIEW:
        raise CourseNotPendingReview(
            f"Course '{course.title}' is not pending review (status: {course.status})."
        )

    with transaction.atomic():
        course.status = Course.Status.PUBLISHED
        course.save(update_fields=["status"])
        transaction.on_commit(lambda: sync_course_to_index.delay(course.id))
        transaction.on_commit(lambda: sync_course_to_tutor_service_task.delay(course.id))

    return course