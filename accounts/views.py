import json

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST


@ensure_csrf_cookie
@require_GET
def csrf_view(request):
    return JsonResponse({"csrfToken": get_token(request)})


@require_POST
def login_view(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    email = body.get("email", "").strip()
    password = body.get("password", "")

    user = authenticate(request, username=email, password=password)
    if user is None:
        return JsonResponse({"error": "Invalid credentials."}, status=401)

    login(request, user)
    return JsonResponse({"email": user.email, "full_name": user.full_name})


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"success": True})


@require_GET
def me_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Not authenticated."}, status=401)
    return JsonResponse({"email": request.user.email, "full_name": request.user.full_name})