from django import db
from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.models import Account
from pots.models import Pot


class Donation(models.Model):
    id = models.AutoField(
        _("donation id"),
        primary_key=True,
        help_text=_("Donation id."),
    )
    on_chain_id = models.IntegerField(
        _("contract donation id"),
        null=False,
        help_text=_("Donation id in contract"),
    )
    donor = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="donations",
        null=False,
        help_text=_("Donor."),
        db_index=True,
    )
    total_amount = models.CharField(
        _("total amount"),
        max_length=64,
        null=False,
        help_text=_("Total amount."),
    )
    # TODO: consider adding formatted total_amount (would need to fetch decimals for FTs)
    total_amount_usd = models.DecimalField(
        _("total amount in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        help_text=_("Total amount in USD."),
        db_index=True,
    )
    net_amount = models.CharField(
        _("net amount"),
        max_length=64,
        null=False,
        help_text=_("Net amount."),
    )
    net_amount_usd = models.DecimalField(
        _("net amount in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        help_text=_("Net amount in USD."),
    )
    ft = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="ft_donations",
        null=False,
        help_text=_("Donation FT."),
    )
    pot = models.ForeignKey(
        Pot,
        on_delete=models.CASCADE,
        related_name="donations",
        null=True,
        help_text=_("Donation pot."),
        db_index=True,
    )
    matching_pool = models.BooleanField(
        _("matching pool"),
        null=False,
        help_text=_("Matching pool."),
        db_index=True,
    )
    message = models.TextField(
        _("message"),
        max_length=1024,
        null=True,
        help_text=_("Donation message."),
    )
    donated_at = models.DateTimeField(
        _("donated at"),
        null=False,
        help_text=_("Donation date."),
        db_index=True,
    )
    recipient = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="received_donations",
        null=True,
        help_text=_("Donation recipient."),
        db_index=True,
    )
    protocol_fee = models.CharField(
        _("protocol fee"),
        max_length=64,
        null=False,
        help_text=_("Protocol fee."),
    )
    protocol_fee_usd = models.DecimalField(
        _("protocol fee in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        help_text=_("Protocol fee in USD."),
    )
    referrer = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="referral_donations",
        null=True,
        help_text=_("Donation referrer."),
    )
    referrer_fee = models.CharField(
        _("referrer fee"),
        max_length=64,
        null=True,
        help_text=_("Referrer fee."),
    )
    referrer_fee_usd = models.DecimalField(
        _("referrer fee in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        help_text=_("Referrer fee in USD."),
    )
    chef = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="chef_donations",
        null=True,
        help_text=_("Donation chef."),
    )
    chef_fee = models.CharField(
        _("chef fee"),
        max_length=64,
        null=False,
        help_text=_("Chef fee."),
    )
    chef_fee_usd = models.DecimalField(
        _("chef fee in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        help_text=_("Chef fee in USD."),
    )
    tx_hash = models.CharField(
        _("transaction hash"),
        max_length=64,
        null=False,
        help_text=_("Transaction hash."),
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["on_chain_id"],
                condition=models.Q(pot__isnull=True),
                name="unique_on_chain_id_when_pot_is_null",
            ),
            models.UniqueConstraint(
                fields=["on_chain_id", "pot"],
                condition=models.Q(pot__isnull=False),
                name="unique_on_chain_id_with_pot",
            ),
        ]
