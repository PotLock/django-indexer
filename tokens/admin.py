from django.contrib import admin

from .models import Token, TokenHistoricalPrice


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ("id", "decimals", "get_most_recent_price")
    search_fields = ("id",)

    def get_most_recent_price(self, obj):
        price = obj.get_most_recent_price()
        return price.price_usd if price else None

    get_most_recent_price.short_description = "Most Recent Price (USD)"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TokenHistoricalPrice)
class TokenHistoricalPriceAdmin(admin.ModelAdmin):
    list_display = ("token", "timestamp", "price_usd")
    search_fields = ("token__id",)
    list_filter = ("timestamp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
