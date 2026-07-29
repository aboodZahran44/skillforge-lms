from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase

from orgs.models import Organization
from orgs.services import get_org_dashboard_data

Course = apps.get_model("catalog", "Course")
Enrollment = apps.get_model("learning", "Enrollment")
User = get_user_model()


class OrgDashboardQueryCountTest(TestCase):
    def test_dashboard_query_count_does_not_scale_with_employee_count(self):
        instructor = User.objects.create_user(email="perf-teacher@example.com", password="x")
        course = Course.objects.create(
            title="Perf Course", slug="perf-course", instructor=instructor
        )
        org = Organization.objects.create(name="Perf Org", slug="perf-org")

        for i in range(20):
            employee = User.objects.create_user(email=f"perf-emp-{i}@example.com", password="x")
            Enrollment.objects.create(user=employee, course=course, organization=org)

        with self.assertNumQueries(4):
            get_org_dashboard_data(org)