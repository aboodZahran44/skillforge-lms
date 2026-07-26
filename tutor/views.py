from django.apps import apps
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .services import RateLimitExceededError, issue_tutor_token


@require_GET
def tutor_token_view(request, course_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)

    Enrollment = apps.get_model("learning", "Enrollment")
    try:
        enrollment = Enrollment.objects.get(user=request.user, course_id=course_id)
    except Enrollment.DoesNotExist:
        return JsonResponse({"error": "You are not enrolled in this course."}, status=403)

    try:
        token = issue_tutor_token(enrollment)
    except RateLimitExceededError as e:
        return JsonResponse({"error": str(e)}, status=429)

    return JsonResponse({"token": token, "expires_in_seconds": 300})