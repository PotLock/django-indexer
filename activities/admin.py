from django.contrib import admin
from django.utils.html import format_html

from .models import Account, Activity


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "signer_address",
        "receiver_address",
        "timestamp",
        "type",
        "transaction_link",
        "action_result",
    )
    list_filter = ("timestamp", "type", "signer", "receiver")
    search_fields = ("signer__id", "receiver__id", "tx_hash")
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)

    def signer_address(self, obj):
        return obj.signer.id

    signer_address.admin_order_field = "signer"
    signer_address.short_description = "Signer Address"

    def receiver_address(self, obj):
        return obj.receiver.id

    receiver_address.admin_order_field = "receiver"
    receiver_address.short_description = "Receiver Address"

    def transaction_link(self, obj):
        url = f"https://nearblocks.io?query={obj.tx_hash}"
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.tx_hash)

    transaction_link.short_description = "Transaction Hash"  # Sets the column header

    # def action_result_summary(self, obj):
    #     return "Has Result" if obj.action_result else "No Result"
    # action_result_summary.short_description = 'Action Result'

    # def has_add_permission(self, request):
    #     return False

    # def has_change_permission(self, request, obj=None):
    #     return False

    # def has_delete_permission(self, request, obj=None):
    #     return False
