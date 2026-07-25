import logging

from django.conf import settings
from django.db.models import Q
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError as ESConnectionError

logger = logging.getLogger(__name__)

INDEX_NAME = "courses"

MAX_RESULTS = 20


def get_client():
    return Elasticsearch(settings.ELASTICSEARCH_URL)


def ensure_index():
    client = get_client()
    if not client.indices.exists(index=INDEX_NAME):
        client.indices.create(
            index=INDEX_NAME,
            mappings={
                "properties": {
                    "title": {"type": "text"},
                    "description": {"type": "text"},
                    "status": {"type": "keyword"},
                }
            },
        )


def index_course(course):
    try:
        client = get_client()
        client.index(
            index=INDEX_NAME,
            id=course.id,
            document={
                "title": course.title,
                "description": course.description,
                "status": course.status,
            },
        )
    except ESConnectionError:
        logger.warning("Elasticsearch unreachable; skipped indexing course %s", course.id)


def remove_course(course_id):
    try:
        client = get_client()
        client.options(ignore_status=404).delete(index=INDEX_NAME, id=course_id)
    except ESConnectionError:
        logger.warning("Elasticsearch unreachable; skipped removing course %s", course_id)


def search_courses(query):
    """Search published courses. Returns (results, degraded).

    Falls back to a plain database search (no typo tolerance, no relevance
    ranking) when Elasticsearch is unreachable — degraded is True in that case.
    """
    try:
        client = get_client()
        response = client.search(
            index=INDEX_NAME,
            size=MAX_RESULTS,
            query={
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^2", "description"],
                            "fuzziness": "AUTO",
                        }
                    },
                    "filter": {"term": {"status": "published"}},
                }
            },
        )
        results = [
            {
                "id": int(hit["_id"]),
                "title": hit["_source"]["title"],
                "description": hit["_source"]["description"],
            }
            for hit in response["hits"]["hits"]
        ]
        return results, False
    except ESConnectionError:
        logger.warning("Elasticsearch unreachable; falling back to database search")
        return _database_search(query), True


def _database_search(query):
    from .models import Course

    courses = Course.objects.filter(
        Q(title__icontains=query) | Q(description__icontains=query),
        status=Course.Status.PUBLISHED,
    )[:MAX_RESULTS]
    return [
        {"id": course.id, "title": course.title, "description": course.description}
        for course in courses
    ]
