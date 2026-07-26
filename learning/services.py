from django.db import transaction

from .models import QuizAnswer, QuizAttempt
from .selectors import is_course_complete
from .tasks import generate_certificate_pdf


class QuizMismatchError(Exception):
    """Raised when the quiz doesn't belong to the enrollment's course."""


class MissingAnswerError(Exception):
    """Raised when the submission doesn't cover every question in the quiz."""


def submit_quiz_attempt(enrollment, quiz, answers):
    if enrollment.course_id != quiz.course_id:
        raise QuizMismatchError("This quiz does not belong to the enrolled course.")

    questions = list(quiz.questions.all())
    if not questions:
        raise MissingAnswerError("This quiz has no questions.")

    with transaction.atomic():
        attempt = QuizAttempt.objects.create(
            enrollment=enrollment, quiz=quiz, score_percent=0, passed=False
        )

        correct = 0
        for question in questions:
            choice_id = answers.get(question.id)
            if choice_id is None:
                raise MissingAnswerError(f"No answer submitted for question {question.id}.")

            choice = question.choices.get(id=choice_id)
            if choice.is_correct:
                correct += 1

            QuizAnswer.objects.create(attempt=attempt, question=question, selected_choice=choice)

        score_percent = round((correct / len(questions)) * 100)
        attempt.score_percent = score_percent
        attempt.passed = score_percent >= quiz.passing_score_percent
        attempt.save(update_fields=["score_percent", "passed"])

    if attempt.passed and is_course_complete(enrollment):
        transaction.on_commit(lambda: generate_certificate_pdf.delay(attempt.id))

    return attempt