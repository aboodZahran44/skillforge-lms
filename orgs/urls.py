from django.urls import path

from . import views

app_name = "orgs"

urlpatterns = [
    path("<int:org_id>/dashboard/", views.org_dashboard_view, name="dashboard"),
    path("<int:org_id>/compliance-report/", views.compliance_report_view, name="compliance-report"),
]