from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase

from learning.models import Enrollment

Course = apps.get_model("catalog", "Course")
Organization = apps.get_model("orgs", "Organization")

User = get_user_model()


class TenancyIsolationTest(TestCase):
    def test_for_org_hides_other_organizations_enrollments(self):
        org_a = Organization.objects.create(name="Org A", slug="org-a")
        org_b = Organization.objects.create(name="Org B", slug="org-b")

        instructor = User.objects.create_user(email="teacher@example.com", password="x")
        course = Course.objects.create(
            title="Shared Course", slug="shared-course", instructor=instructor
        )

        user_a = User.objects.create_user(email="a@example.com", password="x")
        user_b = User.objects.create_user(email="b@example.com", password="x")

        enrollment_a = Enrollment.objects.create(
            user=user_a, course=course, organization=org_a
        )
        Enrollment.objects.create(user=user_b, course=course, organization=org_b)

        visible_to_org_a = Enrollment.objects.for_org(org_a)

        self.assertIn(enrollment_a, visible_to_org_a)
        self.assertEqual(visible_to_org_a.count(), 1)