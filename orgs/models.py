from django.conf import settings
from django.db import models
from django.db.models import Q


class Organization(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class SeatLicense(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="seat_licenses"
    )
    total_seats = models.PositiveIntegerField()
    seats_used = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(seats_used__lte=models.F("total_seats")),
                name="seats_used_not_over_total",
            ),
        ]

    def __str__(self):
        return f"{self.organization.name}: {self.seats_used}/{self.total_seats}"


class SeatAssignment(models.Model):
    seat_license = models.ForeignKey(
        SeatLicense, on_delete=models.CASCADE, related_name="assignments"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seat_assignments"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["seat_license", "user"], name="unique_user_per_license"
            ),
        ]