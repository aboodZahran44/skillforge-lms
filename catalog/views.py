from django.http import JsonResponse

from . import search


def course_search(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"results": [], "degraded": False})

    results, degraded = search.search_courses(query)
    return JsonResponse({"results": results, "degraded": degraded})
