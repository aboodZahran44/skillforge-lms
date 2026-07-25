from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from elasticsearch.exceptions import ConnectionError as ESConnectionError

from . import search, services
from .models import Course
from .tasks import sync_course_to_index

User = get_user_model()


def make_course(status=Course.Status.PENDING_REVIEW, slug="test-course", **kwargs):
    instructor = kwargs.pop("instructor", None) or User.objects.create_user(
        email=f"{slug}-teacher@example.com", password="x"
    )
    return Course.objects.create(
        title=kwargs.pop("title", "Test Course"),
        slug=slug,
        description=kwargs.pop("description", "A course for testing."),
        instructor=instructor,
        status=status,
    )


class ApproveCourseServiceTest(TestCase):
    @patch("catalog.services.sync_course_to_index.delay")
    def test_approve_publishes_and_enqueues_index_sync(self, mock_delay):
        course = make_course()

        with self.captureOnCommitCallbacks(execute=True):
            services.approve_course(course)

        course.refresh_from_db()
        self.assertEqual(course.status, Course.Status.PUBLISHED)
        mock_delay.assert_called_once_with(course.id)

    def test_approve_rejects_non_pending_course(self):
        course = make_course(status=Course.Status.DRAFT)

        with self.assertRaises(services.CourseNotPendingReview):
            services.approve_course(course)

        course.refresh_from_db()
        self.assertEqual(course.status, Course.Status.DRAFT)


class SyncCourseToIndexTaskTest(TestCase):
    @patch("catalog.tasks.search.index_course")
    def test_published_course_is_indexed(self, mock_index):
        course = make_course(status=Course.Status.PUBLISHED)

        sync_course_to_index(course.id)

        mock_index.assert_called_once()
        self.assertEqual(mock_index.call_args.args[0].id, course.id)

    @patch("catalog.tasks.search.remove_course")
    def test_unpublished_course_is_removed(self, mock_remove):
        course = make_course(status=Course.Status.DRAFT)

        sync_course_to_index(course.id)

        mock_remove.assert_called_once_with(course.id)

    @patch("catalog.tasks.search.remove_course")
    def test_deleted_course_is_removed(self, mock_remove):
        sync_course_to_index(999999)

        mock_remove.assert_called_once_with(999999)


class SearchCoursesTest(TestCase):
    @patch("catalog.search.get_client")
    def test_returns_elasticsearch_hits(self, mock_get_client):
        mock_get_client.return_value.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_id": "1",
                        "_source": {"title": "Python", "description": "Learn Python."},
                    }
                ]
            }
        }

        results, degraded = search.search_courses("python")

        self.assertFalse(degraded)
        self.assertEqual(results, [{"id": 1, "title": "Python", "description": "Learn Python."}])

    @patch("catalog.search.get_client")
    def test_falls_back_to_database_when_es_unreachable(self, mock_get_client):
        mock_get_client.return_value.search.side_effect = ESConnectionError("down")
        published = make_course(
            status=Course.Status.PUBLISHED, slug="pub", title="Python Basics"
        )
        make_course(status=Course.Status.DRAFT, slug="draft", title="Python Drafts")

        results, degraded = search.search_courses("python")

        self.assertTrue(degraded)
        self.assertEqual([r["id"] for r in results], [published.id])


class CourseSearchViewTest(TestCase):
    @patch("catalog.views.search.search_courses")
    def test_returns_results_and_degraded_flag(self, mock_search):
        mock_search.return_value = ([{"id": 1, "title": "T", "description": "D"}], True)

        response = self.client.get(reverse("catalog:course-search"), {"q": "python"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"results": [{"id": 1, "title": "T", "description": "D"}], "degraded": True},
        )
        mock_search.assert_called_once_with("python")

    @patch("catalog.views.search.search_courses")
    def test_blank_query_short_circuits(self, mock_search):
        response = self.client.get(reverse("catalog:course-search"), {"q": "  "})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"results": [], "degraded": False})
        mock_search.assert_not_called()
