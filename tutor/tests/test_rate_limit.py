from django.conf import settings
from django.test import TestCase

import redis as redis_lib

from tutor.services import RateLimitExceededError, check_and_increment_rate_limit


class RateLimitTest(TestCase):
    def setUp(self):
        self.user_id = 999999
        client = redis_lib.from_url(settings.REDIS_URL)
        client.delete(f"tutor_rate_limit:{self.user_id}")

    def test_exceeding_limit_raises(self):
        for _ in range(10):
            check_and_increment_rate_limit(self.user_id, limit=10, window_seconds=3600)

        with self.assertRaises(RateLimitExceededError):
            check_and_increment_rate_limit(self.user_id, limit=10, window_seconds=3600)