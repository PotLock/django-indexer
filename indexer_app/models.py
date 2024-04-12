from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.models import Account


class TokenData(models.Model):
    token_id = models.CharField(
        _("token id"),
        primary_key=True,
        max_length=64,
        db_index=True,
        help_text=_("Token id."),
    )
    decimals = models.PositiveIntegerField(
        _("decimals"),
        null=False,
        help_text=_("Token decimals."),
    )
    last_updated = models.DateTimeField(
        _("last updated"),
        null=False,
        help_text=_("Last updated date."),
        db_index=True,
    )
    historical_price_usd = models.DecimalField(
        _("historical price USD"),
        max_digits=20,
        decimal_places=2,
        null=False,
        help_text=_("Historical price."),
    )
