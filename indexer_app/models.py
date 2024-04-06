from django.db import models
from django.utils.translation import gettext_lazy as _


class Account(models.Model):
    id = models.CharField(
        _("address"),
        primary_key=True,
        max_length=64,
        db_index=True,
        validators=[],
        help_text=_("On-chain account address."),
    )
    total_donations_received_usd = models.DecimalField(
        _("total donations received in USD"),
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text=_("Total donations received in USD."),
    )
