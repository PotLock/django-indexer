import token
from datetime import timedelta
from decimal import Decimal

import requests
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import models
from django.forms.models import model_to_dict
from django.utils.translation import gettext_lazy as _

from accounts.models import Account
from base.logging import logger
from base.utils import format_date
from pots.models import Pot
from tokens.models import Token, TokenHistoricalPrice


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
    # ft = models.ForeignKey(
    #     Account,  # should probably be Token
    #     on_delete=models.CASCADE,
    #     related_name="ft_donations",
    #     null=False,
    #     help_text=_("Donation FT."),
    # )
    token = models.ForeignKey(
        Token,
        on_delete=models.CASCADE,
        related_name="donations",
        null=False,
        help_text=_("Donation token."),
        db_index=True,
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
        null=True,
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
        null=True,
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

    def to_dict(self):
        return model_to_dict(self)

    async def fetch_usd_prices_async(self):
        fetch_prices = sync_to_async(self.fetch_usd_prices)
        await fetch_prices()

    ### Fetches USD prices for the Donation record and saves USD totals
    def fetch_usd_prices(self):
        # TODO: remove duplicate logic with PotPayout.fetch_usd_prices
        # get existing values for stats adjustments later
        existing_total_amount_usd = self.total_amount_usd
        existing_net_amount_usd = self.net_amount_usd
        existing_protocol_fee_usd = self.protocol_fee_usd
        existing_referrer_fee_usd = self.referrer_fee_usd
        existing_chef_fee_usd = self.chef_fee_usd
        # first, see if there is a TokenHistoricalPrice within 1 day (or HISTORICAL_PRICE_QUERY_HOURS) of self.donated_at

        try:
            token = self.token
            price_usd = token.fetch_usd_prices_common(self.donated_at)
            if not price_usd:
                logger.error(
                    f"No USD price found for token {token.symbol} at {self.donated_at}"
                )
                return
            total_amount = token.format_price(self.total_amount)
            net_amount = token.format_price(self.net_amount)
            protocol_amount = token.format_price(self.protocol_fee)
            referrer_amount = (
                None if not self.referrer_fee else token.format_price(self.referrer_fee)
            )
            chef_amount = None if not self.chef_fee else token.format_price(self.chef_fee)
            self.total_amount_usd = total_amount * price_usd
            self.net_amount_usd = net_amount * price_usd
            self.protocol_fee_usd = protocol_amount * price_usd
            self.referrer_fee_usd = (
                None if not referrer_amount else referrer_amount * price_usd
            )
            self.chef_fee_usd = None if not chef_amount else chef_amount * price_usd
            self.save()
            logger.info(
                f"Saved USD prices for donation: {self.on_chain_id}"
            )
        except Exception as e:
            logger.error(
                f"Failed to calculate and save USD prices: {e}"
            )
        # chef_amount = token.format_price(self.chef_fee or "0")
        # TODO: update totals for relevant accounts
