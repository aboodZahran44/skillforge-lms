import threading

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase

from orgs.models import Organization, SeatAssignment, SeatLicense
from orgs.services import NoSeatsAvailable, assign_seat

User = get_user_model()

class SeatRaceConditionTest(TransactionTestCase):
    def test_concurrent_assign_seat_does_not_oversell(self):
        org = Organization.objects.create(name="Acme Corp", slug="acme")
        seat_license = SeatLicense.objects.create(
            organization=org, total_seats=1, seats_used=0
        )
        user_a = User.objects.create_user(email="a@example.com", password="x")
        user_b = User.objects.create_user(email="b@example.com", password="x")

        results = {}
        barrier = threading.Barrier(2)

        def worker(name, user):
            barrier.wait()
            try:
                assign_seat(seat_license.id, user)
                results[name] = "success"
            except NoSeatsAvailable:
                results[name] = "no_seats"
            finally:
                connection.close()

        thread_a = threading.Thread(target=worker, args=("a", user_a))
        thread_b = threading.Thread(target=worker, args=("b", user_b))

        thread_a.start()
        thread_b.start()
        thread_a.join()
        thread_b.join()

        seat_license.refresh_from_db()

        self.assertEqual(seat_license.seats_used, 1)
        self.assertEqual(SeatAssignment.objects.count(), 1)
        self.assertEqual(list(results.values()).count("success"), 1)
        self.assertEqual(list(results.values()).count("no_seats"), 1)