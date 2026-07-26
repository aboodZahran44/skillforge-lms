from django.apps import apps
from django.db import IntegrityError, transaction

from .models import Order, Payment


class InvalidOrderAmountError(Exception):
    """Raised when the requested seat quantity is invalid."""


def create_pending_order(organization, seat_quantity, price_per_seat_cents, currency="usd"):
    if seat_quantity <= 0:
        raise InvalidOrderAmountError("Seat quantity must be positive.")

    return Order.objects.create(
        organization=organization,
        seat_quantity=seat_quantity,
        amount_cents=seat_quantity * price_per_seat_cents,
        currency=currency,
    )


def mark_order_paid(order, *, stripe_event_id, stripe_payment_intent_id, amount_cents):
    SeatLicense = apps.get_model("orgs", "SeatLicense")

    try:
        with transaction.atomic():
            Payment.objects.create(
                order=order,
                stripe_event_id=stripe_event_id,
                stripe_payment_intent_id=stripe_payment_intent_id,
                amount_cents=amount_cents,
                status="succeeded",
            )

            order.refresh_from_db()
            if order.status != Order.Status.PAID:
                seat_license = SeatLicense.objects.create(
                    organization=order.organization,
                    total_seats=order.seat_quantity,
                    seats_used=0,
                )
                order.seat_license = seat_license
                order.status = Order.Status.PAID
                order.save(update_fields=["status", "seat_license"])
    except IntegrityError:
        # نفس حدث Stripe وصل مرة ثانية — القيد رفض الإدخال المكرر، ما في شي نعمله.
        pass

    return order