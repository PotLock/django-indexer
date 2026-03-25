from django.contrib import admin

from .models import OrganizationVerification


@admin.register(OrganizationVerification)
class OrganizationVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "account",
        "legal_name",
        "ein",
        "subsection_code",
        "status",
        "submitted_at",
    )
    list_filter = ("status", "submitted_at")
    search_fields = ("account__id", "legal_name", "ein")
    readonly_fields = (
        "id",
        "account",
        "ein",
        "legal_name",
        "address",
        "city",
        "state",
        "zip_code",
        "subsection_code",
        "ntee_code",
        "ruling_date",
        "status",
        "rejection_reason",
        "submitted_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
