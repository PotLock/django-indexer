from django.contrib import admin
from django.utils.dateformat import format
from django.utils.timezone import localtime

from .models import Donation


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Donation._meta.get_fields()]
    list_display.extend(
        [
            "donor_address",
            "recipient_address",
            "token_address",
            "referrer_address",
            "chef_address",
        ]
    )  # Add custom methods for addresses
    search_fields = (
        "message",
        "donor__id",
    )  # Correct field name from 'donor__address' to 'donor__id' if 'id' is used in the model
    list_filter = ("donated_at", "donor", "pot", "pot__account")
    date_hierarchy = "donated_at"
    ordering = ("-donated_at",)

    def get_queryset(self, request):
        # Prefetch related donor, recipient, token, referrer, and chef to prevent N+1 queries
        return (
            super()
            .get_queryset(request)
            .prefetch_related("donor", "recipient", "token", "referrer", "chef")
        )

    def donor_address(self, obj):
        return obj.donor.id

    donor_address.admin_order_field = "donor__id"
    donor_address.short_description = "Donor Address"

    def recipient_address(self, obj):
        return obj.recipient.id if obj.recipient else None

    def token_address(self, obj):
        return obj.token.account

    def referrer_address(self, obj):
        return obj.referrer.id if obj.referrer else None

    def chef_address(self, obj):
        return obj.chef.id if obj.chef else None

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super(DonationAdmin, self).formfield_for_dbfield(
            db_field, request, **kwargs
        )
        if db_field.name == "donated_at":
            field.widget.format = "%d-%m-%Y %H:%M"
            field.widget.attrs.update({"class": "vDateField", "size": "20"})
        return field

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
