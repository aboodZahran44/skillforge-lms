from django.db import transaction

from .models import Course
from .tasks import sync_course_to_index


class CourseNotPendingReview(Exception):
    """Raised when trying to approve a course that isn't awaiting review."""


def approve_course(course):
    if course.status != Course.Status.PENDING_REVIEW:
        raise CourseNotPendingReview(
            f"Course {course.id} has status '{course.status}', expected 'pending_review'."
        )

    with transaction.atomic():
        course.status = Course.Status.PUBLISHED
        course.save(update_fields=["status", "updated_at"])
        transaction.on_commit(lambda: sync_course_to_index.delay(course.id))

    return course
