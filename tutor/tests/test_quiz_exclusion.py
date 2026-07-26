from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase

from tutor.models import LessonChunk
from tutor.services import ingest_course

Course = apps.get_model("catalog", "Course")
Section = apps.get_model("catalog", "Section")
Lesson = apps.get_model("catalog", "Lesson")
Quiz = apps.get_model("catalog", "Quiz")
QuizQuestion = apps.get_model("catalog", "QuizQuestion")
QuizChoice = apps.get_model("catalog", "QuizChoice")
User = get_user_model()


class QuizExclusionTest(TestCase):
    def test_quiz_content_never_enters_the_vector_store(self):
        instructor = User.objects.create_user(email="teacher4@example.com", password="x")
        course = Course.objects.create(
            title="Quiz Exclusion Course", slug="quiz-exclusion-course", instructor=instructor
        )
        section = Section.objects.create(course=course, title="Section", order=1)
        Lesson.objects.create(
            section=section, title="Lesson", order=1,
            content="Ordinary lesson content about loops and iteration.",
        )

        secret_marker = "ZEBRA-QUIZ-SECRET-42"
        quiz = Quiz.objects.create(course=course, title="Quiz")
        question = QuizQuestion.objects.create(quiz=quiz, text=secret_marker, order=1)
        QuizChoice.objects.create(question=question, text="correct answer", is_correct=True)

        ingest_course(course)

        leaked = LessonChunk.objects.filter(content__icontains=secret_marker)
        self.assertEqual(leaked.count(), 0)