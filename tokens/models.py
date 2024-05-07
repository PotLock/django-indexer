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
    decimals = models.PositiveIntegerField(
        _("decimals"),
        null=False,
        help_text=_("Token decimals."),
    )

    def get_most_recent_price(self):
        return self.historical_prices.order_by("-timestamp").first()

    def format_price(self, amount_str: str):
        formatted_amount = int(amount_str) / (10**self.decimals)
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
