from django.db import transaction

from .models import SeatAssignment, SeatLicense


class NoSeatsAvailable(Exception):
    pass


class SeatLicenseInactiveError(Exception):
    pass


def assign_seat(seat_license_id, user, order=None):
    with transaction.atomic():
        seat_license = SeatLicense.objects.select_for_update().get(id=seat_license_id)

        owning_order = getattr(seat_license, "order", None)
        if owning_order is not None and owning_order.status != owning_order.Status.PAID:
            raise SeatLicenseInactiveError(
                f"Seat license belongs to an order with status '{owning_order.status}', "
                "not 'paid'."
            )

        if seat_license.seats_used >= seat_license.total_seats:
            raise NoSeatsAvailable

        SeatAssignment.objects.create(seat_license=seat_license, user=user, order=order)
        seat_license.seats_used += 1
        seat_license.save()

        return seat_license


def revoke_seats_for_order(order):
    from django.utils import timezone

    assignments = SeatAssignment.objects.filter(order=order, revoked_at__isnull=True)

    with transaction.atomic():
        seat_license_ids = set(assignments.values_list("seat_license_id", flat=True))
        revoked_count = assignments.update(revoked_at=timezone.now())

        for seat_license_id in seat_license_ids:
            seat_license = SeatLicense.objects.select_for_update().get(id=seat_license_id)
            active_count = SeatAssignment.objects.filter(
                seat_license=seat_license, revoked_at__isnull=True
            ).count()
            seat_license.seats_used = active_count
            seat_license.save(update_fields=["seats_used"])

    return revoked_count