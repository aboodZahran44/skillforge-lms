
# Create your tests here.
from django.apps import apps
from django.test import TestCase

from orders.models import Order, Payment
from orders.services import create_pending_order, mark_order_paid

Organization = apps.get_model("orgs", "Organization")
SeatLicense = apps.get_model("orgs", "SeatLicense")


class MarkOrderPaidIdempotencyTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Acme", slug="acme")
        self.order = create_pending_order(
            self.org, seat_quantity=5, price_per_seat_cents=1000
        )

    def test_processing_same_stripe_event_twice_creates_one_license(self):
        mark_order_paid(
            self.order,
            stripe_event_id="evt_test_123",
            stripe_payment_intent_id="pi_test_123",
            amount_cents=5000,
        )
        mark_order_paid(
            self.order,
            stripe_event_id="evt_test_123",  # نفس الحدث بالضبط، مرة ثانية
            stripe_payment_intent_id="pi_test_123",
            amount_cents=5000,
        )

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertEqual(Payment.objects.filter(order=self.order).count(), 1)
        self.assertEqual(SeatLicense.objects.filter(organization=self.org).count(), 1)

    def test_new_order_starts_pending_with_correct_amount(self):
        self.assertEqual(self.order.status, Order.Status.PENDING)
        self.assertEqual(self.order.amount_cents, 5000)
        self.assertIsNone(self.order.seat_license)