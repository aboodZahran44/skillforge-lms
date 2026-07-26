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

def get_org_dashboard_data(organization):
    from django.apps import apps

    Enrollment = apps.get_model("learning", "Enrollment")
    LessonEvent = apps.get_model("learning", "LessonEvent")
    Certificate = apps.get_model("learning", "Certificate")

    licenses = organization.seat_licenses.all()
    total_seats = sum(lic.total_seats for lic in licenses)
    seats_used = sum(lic.seats_used for lic in licenses)

    employees = []
    for enrollment in Enrollment.objects.for_org(organization).select_related("user", "course"):
        lessons_completed = LessonEvent.objects.filter(enrollment=enrollment).count()
        has_certificate = Certificate.objects.filter(attempt__enrollment=enrollment).exists()
        employees.append(
            {
                "email": enrollment.user.email,
                "full_name": enrollment.user.full_name,
                "course": enrollment.course.title,
                "lessons_completed": lessons_completed,
                "certificate_earned": has_certificate,
            }
        )

    return {
        "organization": organization.name,
        "seat_usage": {"total_seats": total_seats, "seats_used": seats_used},
        "employees": employees,
    }