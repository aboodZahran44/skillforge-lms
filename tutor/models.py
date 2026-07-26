from django.db import models
from pgvector.django import VectorField


class LessonChunk(models.Model):
    lesson = models.ForeignKey("catalog.Lesson", on_delete=models.CASCADE, related_name="chunks")
    course = models.ForeignKey("catalog.Course", on_delete=models.CASCADE, related_name="chunks")
    content = models.TextField()
    order = models.PositiveIntegerField()
    embedding = VectorField(dimensions=1536, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["lesson", "order"], name="unique_chunk_order_per_lesson"
            ),
        ]