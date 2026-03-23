from django.contrib import admin

from .models import OrganizationVerification


@admin.register(OrganizationVerification)
class OrganizationVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "account",
        "legal_name",
        "ein",
        "status",
        "submitted_at",
        "updated_at",
    )
    list_filter = ("status", "submitted_at", "updated_at")
    search_fields = ("account__id", "legal_name", "ein")
    ordering = ("-submitted_at",)
    readonly_fields = (
        "account",
        "ein",
        "legal_name",
        "address_line1",
        "address_line2",
        "city",
        "state",
        "zip_code",
        "signer_name",
        "signer_title",
        "submitted_at",
        "updated_at",
    )
    fields = (
        "account",
        "legal_name",
        "ein",
        "address_line1",
        "address_line2",
        "city",
        "state",
        "zip_code",
        "signer_name",
        "signer_title",
        "status",
        "admin_notes",
        "submitted_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
