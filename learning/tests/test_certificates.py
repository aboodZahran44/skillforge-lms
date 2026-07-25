import tempfile

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from learning.models import Certificate, Enrollment, QuizAttempt
from learning.tasks import generate_certificate_pdf

Course = apps.get_model("catalog", "Course")
Quiz = apps.get_model("catalog", "Quiz")
Organization = apps.get_model("orgs", "Organization")

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class GenerateCertificatePdfTest(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Acme", slug="acme")
        instructor = User.objects.create_user(email="teacher@example.com", password="x")
        learner = User.objects.create_user(
            email="learner@example.com", password="x", full_name="Learner One"
        )
        course = Course.objects.create(title="Course", slug="course", instructor=instructor)
        self.quiz = Quiz.objects.create(course=course, title="Final")
        self.enrollment = Enrollment.objects.create(
            user=learner, course=course, organization=org
        )

    def _attempt(self, passed=True, score=90):
        return QuizAttempt.objects.create(
            enrollment=self.enrollment, quiz=self.quiz, score_percent=score, passed=passed
        )

    def test_passed_attempt_persists_certificate_pdf(self):
        attempt = self._attempt()

        certificate_id = generate_certificate_pdf(attempt.id)

        certificate = Certificate.objects.get(id=certificate_id)
        self.assertEqual(certificate.attempt, attempt)
        with certificate.pdf.open("rb") as f:
            self.assertTrue(f.read().startswith(b"%PDF"))

    def test_task_is_idempotent(self):
        attempt = self._attempt()

        first_id = generate_certificate_pdf(attempt.id)
        second_id = generate_certificate_pdf(attempt.id)

        self.assertEqual(first_id, second_id)
        self.assertEqual(Certificate.objects.count(), 1)

    def test_failed_attempt_gets_no_certificate(self):
        attempt = self._attempt(passed=False, score=10)

        result = generate_certificate_pdf(attempt.id)

        self.assertIsNone(result)
        self.assertEqual(Certificate.objects.count(), 0)
