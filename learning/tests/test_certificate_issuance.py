from unittest import mock

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase

from learning.models import Enrollment, LessonEvent
from learning.selectors import is_course_complete
from learning.services import submit_quiz_attempt
from learning.tasks import generate_certificate_pdf

User = get_user_model()
Course = apps.get_model("catalog", "Course")
Section = apps.get_model("catalog", "Section")
Lesson = apps.get_model("catalog", "Lesson")
Quiz = apps.get_model("catalog", "Quiz")
QuizQuestion = apps.get_model("catalog", "QuizQuestion")
QuizChoice = apps.get_model("catalog", "QuizChoice")
Organization = apps.get_model("orgs", "Organization")
Certificate = apps.get_model("learning", "Certificate")


class CertificateIssuanceGatingTest(TestCase):
    def setUp(self):
        instructor = User.objects.create_user(email="teacher2@example.com", password="x")
        self.student = User.objects.create_user(email="student2@example.com", password="x")
        self.org = Organization.objects.create(name="Acme2", slug="acme2")
        self.course = Course.objects.create(
            title="Cert Gating Course", slug="cert-gating-course", instructor=instructor
        )
        section = Section.objects.create(course=self.course, title="Only section", order=1)
        self.lesson_1 = Lesson.objects.create(section=section, title="L1", order=1)
        self.lesson_2 = Lesson.objects.create(section=section, title="L2", order=2)

        self.quiz = Quiz.objects.create(
            course=self.course, title="Final quiz", passing_score_percent=70
        )
        self.question = QuizQuestion.objects.create(quiz=self.quiz, text="Q1", order=1)
        self.correct_choice = QuizChoice.objects.create(
            question=self.question, text="Right", is_correct=True
        )

        self.enrollment = Enrollment.objects.create(
            user=self.student, course=self.course, organization=self.org
        )

    def test_passing_quiz_without_finishing_lessons_does_not_issue_certificate(self):
        with self.captureOnCommitCallbacks(execute=True):
            attempt = submit_quiz_attempt(
                self.enrollment, self.quiz, {self.question.id: self.correct_choice.id}
            )

        self.assertTrue(attempt.passed)
        self.assertFalse(Certificate.objects.filter(attempt=attempt).exists())

    def test_passing_quiz_after_finishing_all_lessons_issues_certificate(self):
        LessonEvent.objects.create(enrollment=self.enrollment, lesson=self.lesson_1)
        LessonEvent.objects.create(enrollment=self.enrollment, lesson=self.lesson_2)
        self.assertTrue(is_course_complete(self.enrollment))

        with mock.patch(
            "learning.tasks.generate_certificate_pdf.delay",
            side_effect=lambda attempt_id: generate_certificate_pdf.apply(args=[attempt_id]),
        ), self.captureOnCommitCallbacks(execute=True):
            attempt = submit_quiz_attempt(
                self.enrollment, self.quiz, {self.question.id: self.correct_choice.id}
            )

        self.assertTrue(attempt.passed)
        self.assertTrue(Certificate.objects.filter(attempt=attempt).exists())