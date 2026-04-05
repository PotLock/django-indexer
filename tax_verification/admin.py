from django.contrib import admin

from .models import NonprofitRegistry, OrganizationVerification


@admin.register(NonprofitRegistry)
class NonprofitRegistryAdmin(admin.ModelAdmin):
    list_display = ("ein", "name", "city", "state", "subsection", "deductibility", "status")
    list_filter = ("subsection", "deductibility", "status", "state")
    search_fields = ("ein", "name", "city")
    readonly_fields = [f.name for f in NonprofitRegistry._meta.get_fields()]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


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
