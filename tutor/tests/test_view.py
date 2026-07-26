import json

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

Course = apps.get_model("catalog", "Course")
Organization = apps.get_model("orgs", "Organization")
Enrollment = apps.get_model("learning", "Enrollment")
User = get_user_model()


@override_settings(ALLOWED_HOSTS=["testserver"])
class AskTutorViewTest(TestCase):
    def setUp(self):
        instructor = User.objects.create_user(email="teacher6@example.com", password="x")
        self.student = User.objects.create_user(
            email="student6@example.com", password="testpass123"
        )
        self.org = Organization.objects.create(name="View Test Org", slug="view-test-org")

        self.course = Course.objects.create(
            title="View Test Course", slug="view-test-course", instructor=instructor
        )
        self.other_course = Course.objects.create(
            title="Other Course", slug="other-view-course", instructor=instructor
        )

        Enrollment.objects.create(
            user=self.student, course=self.course, organization=self.org
        )

        self.client = Client()
        self.client.login(email="student6@example.com", password="testpass123")

    def test_unauthenticated_request_rejected(self):
        anon_client = Client()
        response = anon_client.post(
            f"/api/courses/{self.course.id}/ask/",
            data=json.dumps({"question": "hi"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_asking_about_non_enrolled_course_is_forbidden(self):
        response = self.client.post(
            f"/api/courses/{self.other_course.id}/ask/",
            data=json.dumps({"question": "anything"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_missing_question_returns_400(self):
        response = self.client.post(
            f"/api/courses/{self.course.id}/ask/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)