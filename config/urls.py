"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    checks = {}
    overall_ok = True

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        overall_ok = False

    try:
        import redis as redis_lib
        from django.conf import settings

        client = redis_lib.from_url(settings.REDIS_URL)
        client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        overall_ok = False

    status_code = 200 if overall_ok else 503
    return JsonResponse(
        {"status": "ok" if overall_ok else "degraded", "checks": checks},
        status=status_code,
    )


urlpatterns = [
    path('admin/', admin.site.urls),
    path('healthz/', health_check, name='health-check'),
    path('api/', include('catalog.urls')),
    path('api/', include('orders.urls')),
    path('api/', include('tutor.urls')),
    path('api/auth/', include('accounts.urls')),
    path('api/orgs/', include('orgs.urls')),
]