from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase

from orgs.models import Organization, SeatAssignment, SeatLicense
from orgs.services import assign_seat, revoke_seats_for_order

Order = apps.get_model("orders", "Order")
User = get_user_model()


class SeatRevocationTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Revoke Test Org", slug="revoke-test-org")
        self.license = SeatLicense.objects.create(
            organization=self.org, total_seats=3, seats_used=0
        )
        self.order = Order.objects.create(
            organization=self.org, seat_quantity=3, amount_cents=3000
        )
        self.user_a = User.objects.create_user(email="a@example.com", password="x")
        self.user_b = User.objects.create_user(email="b@example.com", password="x")

    def test_revoking_order_frees_up_seats_and_marks_assignments(self):
        assign_seat(self.license.id, self.user_a, order=self.order)
        assign_seat(self.license.id, self.user_b, order=self.order)

        self.license.refresh_from_db()
        self.assertEqual(self.license.seats_used, 2)

        revoked_count = revoke_seats_for_order(self.order)

        self.assertEqual(revoked_count, 2)
        self.license.refresh_from_db()
        self.assertEqual(self.license.seats_used, 0)

        assignment_a = SeatAssignment.objects.get(seat_license=self.license, user=self.user_a)
        self.assertIsNotNone(assignment_a.revoked_at)

    def test_revoking_does_not_affect_seats_from_other_orders(self):
        other_order = Order.objects.create(
            organization=self.org, seat_quantity=1, amount_cents=1000
        )
        assign_seat(self.license.id, self.user_a, order=self.order)
        assign_seat(self.license.id, self.user_b, order=other_order)

        revoke_seats_for_order(self.order)

        self.license.refresh_from_db()
        self.assertEqual(self.license.seats_used, 1)  # user_b باقي، user_a انلغى بس