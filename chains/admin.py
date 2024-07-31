from django.contrib import admin

from .models import Chain


@admin.register(Chain)
class ChainAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "name_slug",
        "rpc_url",
        "explorer_url",
        "evm_compat",
        "evm_chain_id",
    )
    search_fields = ("name", "name_slug", "rpc_url", "explorer_url", "evm_chain_id")
    list_filter = ("evm_compat",)
    ordering = ("name",)
