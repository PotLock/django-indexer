from django.contrib import admin
from django.utils.dateformat import format
from django.utils.timezone import localtime

from .models import Campaign, CampaignDonation


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = [
        "on_chain_id",
        "name",
        "owner_address",
        "recipient_address",
        "token_address",
        "target_amount",
        "total_raised_amount",
        "net_raised_amount",
        "start_at",
        "end_at",
        "created_at",
        "allow_fee_avoidance",
    ]
    list_filter = (
        "start_at",
        "end_at",
        "created_at",
        "allow_fee_avoidance",
        "owner",
        "recipient",
        "token",
    )
    search_fields = (
        "name",
        "description",
        "owner__id",
        "recipient__id",
        "on_chain_id",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = (
        "on_chain_id",
        "created_at",
        "total_raised_amount",
        "total_raised_amount_usd",
        "net_raised_amount",
        "net_raised_amount_usd",
        "escrow_balance",
        "escrow_balance_usd",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("owner", "recipient", "token")
            .prefetch_related("donations")
        )

    def owner_address(self, obj):
        return obj.owner.id
    owner_address.admin_order_field = "owner__id"
    owner_address.short_description = "Owner Address"

    def recipient_address(self, obj):
        return obj.recipient.id
    recipient_address.admin_order_field = "recipient__id"
    recipient_address.short_description = "Recipient Address"

    def token_address(self, obj):
        return obj.token.account.id if obj.token else "NEAR"
    token_address.admin_order_field = "token__account__id"
    token_address.short_description = "Token"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # Allow viewing but restrict editing of calculated fields
        return True

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CampaignDonation)
class CampaignDonationAdmin(admin.ModelAdmin):
    list_display = [
        "on_chain_id",
        "campaign_id_display",
        "campaign_name",
        "donor_address",
        "token_address",
        "total_amount",
        "total_amount_usd",
        "net_amount",
        "net_amount_usd",
        "donated_at",
        "returned_at",
        "tx_hash",
    ]
    list_filter = (
        "donated_at",
        "returned_at",
        "campaign",
        "donor",
        "token",
        "referrer",
    )
    search_fields = (
        "message",
        "donor__id",
        "campaign__name",
        "campaign__on_chain_id",
        "on_chain_id",
        "tx_hash",
    )
    date_hierarchy = "donated_at"
    ordering = ("-donated_at",)
    readonly_fields = (
        "on_chain_id",
        "total_amount_usd",
        "net_amount_usd",
        "protocol_fee_usd",
        "referrer_fee_usd",
        "creator_fee_usd",
        "donated_at",
        "returned_at",
        "tx_hash",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("campaign", "donor", "token", "referrer")
        )

    def campaign_id_display(self, obj):
        return obj.campaign.on_chain_id
    campaign_id_display.admin_order_field = "campaign__on_chain_id"
    campaign_id_display.short_description = "Campaign ID"

    def campaign_name(self, obj):
        return obj.campaign.name
    campaign_name.admin_order_field = "campaign__name"
    campaign_name.short_description = "Campaign Name"

    def donor_address(self, obj):
        return obj.donor.id
    donor_address.admin_order_field = "donor__id"
    donor_address.short_description = "Donor Address"

    def token_address(self, obj):
        return obj.token.account.id if obj.token else "NEAR"
    token_address.admin_order_field = "token__account__id"
    token_address.short_description = "Token"

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super(CampaignDonationAdmin, self).formfield_for_dbfield(
            db_field, request, **kwargs
        )
        if db_field.name in ["donated_at", "returned_at"]:
            field.widget.format = "%d-%m-%Y %H:%M"
            field.widget.attrs.update({"class": "vDateField", "size": "20"})
        return field

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
