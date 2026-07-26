import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Order
from .services import mark_order_paid


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order_id = session["metadata"]["order_id"]

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return HttpResponse(status=200)

        mark_order_paid(
            order,
            stripe_event_id=event["id"],
            stripe_payment_intent_id=session["payment_intent"] or "",
            amount_cents=session["amount_total"],
        )

    return HttpResponse(status=200)