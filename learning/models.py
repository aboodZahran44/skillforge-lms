from django.conf import settings
from django.db import models


class EnrollmentQuerySet(models.QuerySet):
    def for_org(self, organization):
        return self.filter(organization=organization)


class Enrollment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments"
    )
    course = models.ForeignKey(
        "catalog.Course", on_delete=models.CASCADE, related_name="enrollments"
    )
    organization = models.ForeignKey(
        "orgs.Organization", on_delete=models.CASCADE, related_name="enrollments"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    objects = EnrollmentQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "course"], name="unique_enrollment_per_user_course"
            ),
        ]

    def __str__(self):
        return f"{self.user} in {self.course}"


class LessonEvent(models.Model):
    class EventType(models.TextChoices):
        COMPLETED = "completed", "Completed"

    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="events"
    )
    lesson = models.ForeignKey(
        "catalog.Lesson", on_delete=models.CASCADE, related_name="events"
    )
    event_type = models.CharField(
        max_length=20, choices=EventType.choices, default=EventType.COMPLETED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "lesson", "event_type"], name="unique_lesson_event"
            ),
        ]

    def __str__(self):
        return f"{self.enrollment} — {self.lesson} ({self.event_type})"
    
class QuizAttempt(models.Model):
    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="quiz_attempts"
    )
    quiz = models.ForeignKey(
        "catalog.Quiz", on_delete=models.CASCADE, related_name="attempts"
    )
    score_percent = models.PositiveIntegerField()
    passed = models.BooleanField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.enrollment} — {self.quiz} ({self.score_percent}%)"


class QuizAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey("catalog.QuizQuestion", on_delete=models.CASCADE)
    selected_choice = models.ForeignKey("catalog.QuizChoice", on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"], name="unique_answer_per_question_per_attempt"
            ),
        ]

    def __str__(self):
        return f"{self.attempt} — Q{self.question_id}"