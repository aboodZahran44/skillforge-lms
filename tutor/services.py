from django.conf import settings
from django.db import transaction
from langchain_openai import OpenAIEmbeddings
from pgvector.django import L2Distance

from .models import LessonChunk

_CHUNK_SIZE = 500


def _split_into_chunks(text):
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + _CHUNK_SIZE
        chunks.append(text[start:end].strip())
        start = end
    return [chunk for chunk in chunks if chunk]


def ingest_lesson(lesson):
    chunks_text = _split_into_chunks(lesson.content)
    if not chunks_text:
        return 0

    embeddings_client = OpenAIEmbeddings(
        model="text-embedding-3-small", api_key=settings.OPENAI_API_KEY
    )
    vectors = embeddings_client.embed_documents(chunks_text)

    with transaction.atomic():
        LessonChunk.objects.filter(lesson=lesson).delete()
        for order, (text, vector) in enumerate(zip(chunks_text, vectors, strict=True), start=1):
            LessonChunk.objects.create(
                lesson=lesson,
                course=lesson.section.course,
                content=text,
                order=order,
                embedding=vector,
            )
    return len(chunks_text)


def ingest_course(course):
    total = 0
    for section in course.sections.all():
        for lesson in section.lessons.all():
            total += ingest_lesson(lesson)
    return total

class NotEnrolledError(Exception):
    """Raised when the user tries to query a course they aren't enrolled in."""


def retrieve_relevant_chunks(course_id, question, enrollment, top_k=3):
    if enrollment.course_id != course_id:
        raise NotEnrolledError("You can only ask questions about a course you're enrolled in.")

    embeddings_client = OpenAIEmbeddings(
        model="text-embedding-3-small", api_key=settings.OPENAI_API_KEY
    )
    question_vector = embeddings_client.embed_query(question)

    chunks = (
        LessonChunk.objects.filter(course_id=course_id)
        .order_by(L2Distance("embedding", question_vector))[:top_k]
    )
    return list(chunks)