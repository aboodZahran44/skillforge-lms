from django.contrib import admin

from .models import Organization, SeatAssignment, SeatLicense

admin.site.register(Organization)
admin.site.register(SeatLicense)
admin.site.register(SeatAssignment)