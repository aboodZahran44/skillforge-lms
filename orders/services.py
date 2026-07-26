import stripe
from django.apps import apps
from django.conf import settings
from django.db import IntegrityError, transaction

from .models import Order, Payment

stripe.api_key = settings.STRIPE_SECRET_KEY


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


def create_checkout_session(order, success_url, cancel_url):
    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": order.currency,
                    "unit_amount": order.amount_cents,
                    "product_data": {
                        "name": f"{order.seat_quantity} seat(s) — {order.organization.name}",
                    },
                },
                "quantity": 1,
            }
        ],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"order_id": str(order.id)},
    )

    order.stripe_checkout_session_id = session.id
    order.save(update_fields=["stripe_checkout_session_id"])

    return session


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
        pass

    return order