import json

from django.apps import apps
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from .services import NotEnrolledError, RateLimitExceededError, ask_tutor

from .services import NotEnrolledError, RateLimitExceededError, ask_tutor, issue_tutor_token

@csrf_protect
@require_POST
def ask_tutor_view(request, course_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    question = body.get("question", "").strip()
    if not question:
        return JsonResponse({"error": "Question is required."}, status=400)

    Enrollment = apps.get_model("learning", "Enrollment")
    try:
        enrollment = Enrollment.objects.get(user=request.user, course_id=course_id)
    except Enrollment.DoesNotExist:
        return JsonResponse({"error": "You are not enrolled in this course."}, status=403)

    try:
        answer = ask_tutor(course_id, question, enrollment)
    except (NotEnrolledError, RateLimitExceededError) as e:
        status = 403 if isinstance(e, NotEnrolledError) else 429
        return JsonResponse({"error": str(e)}, status=status)

    return JsonResponse({"answer": answer})

@require_GET
def tutor_token_view(request, course_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)

    Enrollment = apps.get_model("learning", "Enrollment")
    try:
        enrollment = Enrollment.objects.get(user=request.user, course_id=course_id)
    except Enrollment.DoesNotExist:
        return JsonResponse({"error": "You are not enrolled in this course."}, status=403)

    token = issue_tutor_token(enrollment)
    return JsonResponse({"token": token, "expires_in_seconds": 300})