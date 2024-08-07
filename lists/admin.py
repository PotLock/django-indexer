from django.contrib import admin

from .models import Account, List, ListRegistration, ListUpvote


@admin.register(List)
class ListAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "on_chain_id",
        "name",
        "description",
        "cover_image_url",
        "owner",
        "admin_only_registrations",
        "default_registration_status",
        "created_at",
        "updated_at",
    )
    list_filter = ("created_at", "updated_at", "default_registration_status")
    search_fields = ("name", "owner__id")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ListUpvote)
class ListUpvoteAdmin(admin.ModelAdmin):
    list_display = ("id", "list", "account", "created_at")
    list_filter = ("created_at",)
    search_fields = ("list__name", "account__id")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ListRegistration)
class ListRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "list",
        "registrant",
        "registered_by",
        "status",
        "submitted_at",
        "updated_at",
    )
    list_filter = ("status", "submitted_at", "updated_at")
    search_fields = ("list__name", "registrant__id", "registered_by__id")
    ordering = ("-submitted_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
