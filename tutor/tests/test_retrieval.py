from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase

from tutor.services import NotEnrolledError, retrieve_relevant_chunks

Enrollment = apps.get_model("learning", "Enrollment")
Course = apps.get_model("catalog", "Course")
Organization = apps.get_model("orgs", "Organization")
User = get_user_model()


class CourseIsolationTest(TestCase):
    def setUp(self):
        instructor = User.objects.create_user(email="teacher3@example.com", password="x")
        self.student = User.objects.create_user(email="student3@example.com", password="x")
        self.org = Organization.objects.create(name="Tutor Org", slug="tutor-org")

        self.course_a = Course.objects.create(
            title="Course A", slug="course-a", instructor=instructor
        )
        self.course_b = Course.objects.create(
            title="Course B", slug="course-b", instructor=instructor
        )
        self.enrollment = Enrollment.objects.create(
            user=self.student, course=self.course_a, organization=self.org
        )

    def test_cannot_query_a_course_not_enrolled_in(self):
        with self.assertRaises(NotEnrolledError):
            retrieve_relevant_chunks(self.course_b.id, "some question", self.enrollment)