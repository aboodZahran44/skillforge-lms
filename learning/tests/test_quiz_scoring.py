from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase

from learning.models import Enrollment
from learning.services import MissingAnswerError, QuizMismatchError, submit_quiz_attempt

User = get_user_model()
Course = apps.get_model("catalog", "Course")
Quiz = apps.get_model("catalog", "Quiz")
QuizQuestion = apps.get_model("catalog", "QuizQuestion")
QuizChoice = apps.get_model("catalog", "QuizChoice")
Organization = apps.get_model("orgs", "Organization")


class QuizScoringTest(TestCase):
    def setUp(self):
        instructor = User.objects.create_user(email="teacher@example.com", password="x")
        self.student = User.objects.create_user(email="student@example.com", password="x")
        self.org = Organization.objects.create(name="Acme", slug="acme")
        self.course = Course.objects.create(
            title="Test Course", slug="test-course", instructor=instructor
        )
        self.other_course = Course.objects.create(
            title="Other Course", slug="other-course", instructor=instructor
        )
        self.quiz = Quiz.objects.create(
            course=self.course, title="Quiz 1", passing_score_percent=70
        )

        self.q1 = QuizQuestion.objects.create(quiz=self.quiz, text="2 + 2 = ?", order=1)
        self.q1_correct = QuizChoice.objects.create(question=self.q1, text="4", is_correct=True)
        QuizChoice.objects.create(question=self.q1, text="5", is_correct=False)

        self.q2 = QuizQuestion.objects.create(quiz=self.quiz, text="Capital of Jordan?", order=2)
        self.q2_correct = QuizChoice.objects.create(
            question=self.q2, text="Amman", is_correct=True
        )
        QuizChoice.objects.create(question=self.q2, text="Cairo", is_correct=False)

        self.enrollment = Enrollment.objects.create(
            user=self.student, course=self.course, organization=self.org
        )

    def test_all_correct_passes(self):
        attempt = submit_quiz_attempt(
            self.enrollment,
            self.quiz,
            {self.q1.id: self.q1_correct.id, self.q2.id: self.q2_correct.id},
        )
        self.assertEqual(attempt.score_percent, 100)
        self.assertTrue(attempt.passed)

    def test_half_correct_fails_at_70_threshold(self):
        wrong_choice = self.q2.choices.exclude(id=self.q2_correct.id).first()
        attempt = submit_quiz_attempt(
            self.enrollment,
            self.quiz,
            {self.q1.id: self.q1_correct.id, self.q2.id: wrong_choice.id},
        )
        self.assertEqual(attempt.score_percent, 50)
        self.assertFalse(attempt.passed)

    def test_quiz_from_different_course_raises(self):
        mismatched_quiz = Quiz.objects.create(course=self.other_course, title="Other Quiz")
        with self.assertRaises(QuizMismatchError):
            submit_quiz_attempt(
                self.enrollment, mismatched_quiz, {self.q1.id: self.q1_correct.id}
            )

    def test_missing_answer_raises(self):
        with self.assertRaises(MissingAnswerError):
            submit_quiz_attempt(self.enrollment, self.quiz, {self.q1.id: self.q1_correct.id})