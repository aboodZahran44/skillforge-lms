
from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from orgs.models import OrgAdmin, Organization, SeatLicense

Enrollment = apps.get_model("learning", "Enrollment")
Course = apps.get_model("catalog", "Course")
User = get_user_model()


@override_settings(ALLOWED_HOSTS=["testserver"])
class OrgDashboardIsolationTest(TestCase):
    def setUp(self):
        instructor = User.objects.create_user(email="teacher7@example.com", password="x")
        self.course = Course.objects.create(
            title="Dashboard Course", slug="dashboard-course", instructor=instructor
        )

        self.org_a = Organization.objects.create(name="Org A", slug="org-a-dash")
        self.org_b = Organization.objects.create(name="Org B", slug="org-b-dash")

        self.admin_a = User.objects.create_user(
            email="admin-a@example.com", password="testpass123"
        )
        OrgAdmin.objects.create(user=self.admin_a, organization=self.org_a)

        employee_b = User.objects.create_user(email="employee-b@example.com", password="x")
        Enrollment.objects.create(
            user=employee_b, course=self.course, organization=self.org_b
        )
        SeatLicense.objects.create(organization=self.org_b, total_seats=5, seats_used=1)

        self.client = Client()
        self.client.login(email="admin-a@example.com", password="testpass123")

    def test_admin_cannot_view_a_different_orgs_dashboard(self):
        response = self.client.get(f"/api/orgs/{self.org_b.id}/dashboard/")
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_download_a_different_orgs_compliance_report(self):
        response = self.client.get(f"/api/orgs/{self.org_b.id}/compliance-report/")
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(b"employee-b@example.com", response.content)

    def test_admin_can_view_their_own_orgs_dashboard(self):
        response = self.client.get(f"/api/orgs/{self.org_a.id}/dashboard/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["organization"], "Org A")

    def test_unauthenticated_request_rejected(self):
        anon_client = Client()
        response = anon_client.get(f"/api/orgs/{self.org_a.id}/dashboard/")
        self.assertEqual(response.status_code, 401)