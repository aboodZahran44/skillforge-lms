import csv

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

from .models import OrgAdmin, Organization
from .services import get_org_dashboard_data


def _authorize_org_admin(request, org_id):
    if not request.user.is_authenticated:
        return None, JsonResponse({"error": "Authentication required."}, status=401)

    if not OrgAdmin.objects.filter(user=request.user, organization_id=org_id).exists():
        return None, JsonResponse(
            {"error": "You are not an admin for this organization."}, status=403
        )

    try:
        organization = Organization.objects.get(id=org_id)
    except Organization.DoesNotExist:
        return None, JsonResponse({"error": "Organization not found."}, status=404)

    return organization, None


@require_GET
def org_dashboard_view(request, org_id):
    organization, error_response = _authorize_org_admin(request, org_id)
    if error_response:
        return error_response

    return JsonResponse(get_org_dashboard_data(organization))


@require_GET
def compliance_report_view(request, org_id):
    organization, error_response = _authorize_org_admin(request, org_id)
    if error_response:
        return error_response

    data = get_org_dashboard_data(organization)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="compliance-{org_id}.csv"'
    writer = csv.writer(response)
    writer.writerow(["Employee", "Email", "Course", "Lessons Completed", "Certificate Earned"])
    for emp in data["employees"]:
        writer.writerow(
            [
                emp["full_name"],
                emp["email"],
                emp["course"],
                emp["lessons_completed"],
                emp["certificate_earned"],
            ]
        )
    return response