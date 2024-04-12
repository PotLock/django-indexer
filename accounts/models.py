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
    total_donations_in_usd = models.DecimalField(
        _("total donations received in USD"),
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text=_("Total donations received in USD."),
    )
    total_donations_out_usd = models.DecimalField(
        _("total donations sent in USD"),
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text=_("Total donated in USD."),
    )
    total_matching_pool_allocations_usd = models.DecimalField(
        _("total matching pool allocations in USD"),
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text=_("Total matching pool allocations in USD."),
    )
    donors_count = models.PositiveIntegerField(
        _("donors count"),
        default=0,
        help_text=_("Number of donors."),
    )

    # add Meta, properties & methods as necessary
