from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        REFUNDED = "refunded", "Refunded"
        CANCELED = "canceled", "Canceled"

    organization = models.ForeignKey(
        "orgs.Organization", on_delete=models.PROTECT, related_name="orders"
    )
    seat_license = models.OneToOneField(
        "orgs.SeatLicense",
        on_delete=models.PROTECT,
        related_name="order",
        null=True,
        blank=True,
    )
    seat_quantity = models.PositiveIntegerField()
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="usd")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    stripe_checkout_session_id = models.CharField(
        max_length=255, unique=True, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} — {self.organization.name} ({self.status})"


class Payment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments")
    stripe_event_id = models.CharField(max_length=255, unique=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    amount_cents = models.PositiveIntegerField()
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for {self.order} ({self.status})"