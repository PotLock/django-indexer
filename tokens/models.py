from decimal import Decimal
from os import name

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import Account


class Token(models.Model):
    id = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        primary_key=True,
        help_text=_("Token ID (address)."),
    )
    name = models.CharField(
        _("name"),
        max_length=255,
        null=True,
        help_text=_("Token name."),
    )
    symbol = models.CharField(
        _("symbol"),
        max_length=255,
        null=True,
        help_text=_("Token symbol."),
    )
    icon = models.TextField(
        _("icon"),
        null=True,
        help_text=_("Token icon (base64 data URL)."),
    )
    decimals = models.PositiveIntegerField(
        _("decimals"),
        null=False,
        help_text=_("Token decimals."),
    )

    def get_most_recent_price(self):
        return self.historical_prices.order_by("-timestamp").first()

    def format_price(self, amount_str: str):
        # Convert the string amount to a Decimal, then adjust by the token's decimal places
        formatted_amount = Decimal(amount_str) / (Decimal("10") ** self.decimals)
        return formatted_amount


class TokenHistoricalPrice(models.Model):
    token = models.ForeignKey(
        Token,
        on_delete=models.CASCADE,
        related_name="historical_prices",
        null=False,
        help_text=_("Token."),
    )
    timestamp = models.DateTimeField(
        _("timestamp"),
        null=False,
        help_text=_("Price timestamp."),
        db_index=True,
        default=timezone.now,
    )
    price_usd = models.DecimalField(
        _("price USD"),
        max_digits=20,
        decimal_places=2,
        null=False,
        help_text=_("Price in USD."),
    )
