from django.contrib import admin, messages

from .models import Order, Payment
from .services import OrderNotRefundableError, RefundWindowExpiredError, refund_order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "organization", "seat_quantity", "amount_cents", "status", "created_at"]
    list_filter = ["status"]
    actions = ["refund_selected_orders"]

    @admin.action(description="Refund selected orders")
    def refund_selected_orders(self, request, queryset):
        refunded = 0
        skipped = 0

        for order in queryset:
            try:
                revoked_count = refund_order(order)
                refunded += 1
                self.message_user(
                    request,
                    f"Order #{order.id}: refunded, {revoked_count} seat(s) revoked.",
                    level=messages.SUCCESS,
                )
            except (OrderNotRefundableError, RefundWindowExpiredError) as e:
                skipped += 1
                self.message_user(
                    request, f"Order #{order.id}: skipped — {e}", level=messages.WARNING
                )

        self.message_user(
            request,
            f"Done: {refunded} refunded, {skipped} skipped.",
            level=messages.INFO,
        )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["order", "stripe_event_id", "amount_cents", "status", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False