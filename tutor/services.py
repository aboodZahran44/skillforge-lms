import jwt
import requests
from django.conf import settings
from django.utils import timezone


class RateLimitExceededError(Exception):
    pass


class SyncFailedError(Exception):
    pass


def _get_redis_client():
    import redis as redis_lib

    return redis_lib.from_url(settings.REDIS_URL)


def check_and_increment_rate_limit(user_id, limit=10, window_seconds=3600):
    client = _get_redis_client()
    key = f"tutor_rate_limit:{user_id}"

    count = client.incr(key)
    if count == 1:
        client.expire(key, window_seconds)

    if count > limit:
        raise RateLimitExceededError(
            f"You've reached the limit of {limit} tutor questions per hour."
        )


def issue_tutor_token(enrollment):
    check_and_increment_rate_limit(enrollment.user_id)

    now = timezone.now()
    payload = {
        "user_id": enrollment.user_id,
        "course_id": enrollment.course_id,
        "enrollment_id": enrollment.id,
        "iat": now,
        "exp": now + timezone.timedelta(minutes=5),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def sync_lesson_to_tutor_service(lesson):
    try:
        response = requests.post(
            f"{settings.TUTOR_SERVICE_URL}/internal/lessons/ingest",
            json={
                "lesson_id": lesson.id,
                "course_id": lesson.section.course_id,
                "content": lesson.content,
            },
            headers={"X-Internal-Key": settings.INTERNAL_API_KEY},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise SyncFailedError(f"Failed to sync lesson {lesson.id} to tutor service: {e}") from e


def sync_course_to_tutor_service(course):
    for section in course.sections.all():
        for lesson in section.lessons.all():
            sync_lesson_to_tutor_service(lesson)