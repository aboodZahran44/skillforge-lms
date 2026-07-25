from django.db import transaction

from .models import SeatAssignment, SeatLicense


class NoSeatsAvailable(Exception):
    pass


def assign_seat(seat_license_id, user):
    with transaction.atomic():
        seat_license = SeatLicense.objects.select_for_update().get(id=seat_license_id)

        if seat_license.seats_used >= seat_license.total_seats:
            raise NoSeatsAvailable

        SeatAssignment.objects.create(seat_license=seat_license, user=user)
        seat_license.seats_used += 1
        seat_license.save()

        return seat_license