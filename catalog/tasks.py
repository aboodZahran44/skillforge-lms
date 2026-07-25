from celery import shared_task
from django.apps import apps

from . import search


@shared_task
def sync_course_to_index(course_id):
    """Bring the search index in line with the course's current state.

    Re-reads the course so that concurrent updates converge on the latest
    state regardless of task ordering. Non-published or deleted courses are
    removed from the index.
    """
    Course = apps.get_model("catalog", "Course")

    course = Course.objects.filter(id=course_id).first()
    if course is None or course.status != Course.Status.PUBLISHED:
        search.remove_course(course_id)
        return

    search.index_course(course)
