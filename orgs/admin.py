from django.contrib import admin

from .models import OrgAdmin, Organization, SeatAssignment, SeatLicense

admin.site.register(Organization)
admin.site.register(SeatLicense)
admin.site.register(SeatAssignment)

@admin.register(OrgAdmin)
class OrgAdminAdmin(admin.ModelAdmin):
    list_display = ["user", "organization"]