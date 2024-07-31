from django.contrib import admin

from .models import BlockHeight


@admin.register(BlockHeight)
class BlockHeightAdmin(admin.ModelAdmin):
    list_display = ("id", "block_height", "block_timestamp", "updated_at")
    ordering = ("-updated_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
