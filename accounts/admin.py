from django.contrib import admin

from .models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "total_donations_in_usd",
        "total_donations_out_usd",
        "total_matching_pool_allocations_usd",
        "donors_count",
        "near_social_profile_data",
    )
    search_fields = ("id",)  # Allow searching by account address
    list_filter = (
        "total_donations_in_usd",
        "total_donations_out_usd",
    )  # Filter by donation amounts
    ordering = ("-total_donations_in_usd",)  # Default ordering

    # Optionally, format decimal fields for better readability in the admin
    def total_donations_in_usd_display(self, obj):
        return "${:,.2f}".format(obj.total_donations_in_usd)

    total_donations_in_usd_display.admin_order_field = "total_donations_in_usd"
    total_donations_in_usd_display.short_description = "Total Donations Received (USD)"

    def total_donations_out_usd_display(self, obj):
        return "${:,.2f}".format(obj.total_donations_out_usd)

    total_donations_out_usd_display.admin_order_field = "total_donations_out_usd"
    total_donations_out_usd_display.short_description = "Total Donations Sent (USD)"

    def total_matching_pool_allocations_usd_display(self, obj):
        return "${:,.2f}".format(obj.total_matching_pool_allocations_usd)

    total_matching_pool_allocations_usd_display.admin_order_field = (
        "total_matching_pool_allocations_usd"
    )
    total_matching_pool_allocations_usd_display.short_description = (
        "Total Matching Pool Allocations (USD)"
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
