from django.db import models
from accounts.models import Account
from tokens.models import Token
from django.utils.translation import gettext_lazy as _
from django.forms.models import model_to_dict
from asgiref.sync import sync_to_async
from base.logging import logger


class Campaign(models.Model):
    on_chain_id = models.BigIntegerField(unique=True, db_index=True)
    owner = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="owned_campaigns",
        null=False,
        help_text=_("Campaign owner."),
        db_index=True,
    )
    name = models.TextField(
        _("name"),
        null=False,
        help_text=_("Campaign name."),
    )
    description = models.TextField(
        _("description"),
        null=True,
        blank=True,
        help_text=_("Campaign description."),
    )
    cover_image_url = models.TextField(
        _("cover image URL"),
        null=True,
        blank=True,
        help_text=_("Campaign cover image URL."),
    )
    recipient = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="recipient_of_campaign",
        null=False,
        help_text=_("Campaign recipient."),
        db_index=True,
    )
    token = models.ForeignKey(
        Token,
        on_delete=models.CASCADE,
        related_name="campaigns",
        null=True,
        blank=True,
        help_text=_("Campaign token (null for NEAR)."),
        db_index=True,
    )
    start_at = models.DateTimeField(
        _("start at"),
        null=False,
        help_text=_("Campaign start date."),
        db_index=True,
    )
    end_at = models.DateTimeField(
        _("end at"),
        null=True,
        blank=True,
        help_text=_("Campaign end date."),
        db_index=True,
    )
    created_at = models.DateTimeField(
        _("created at"),
        null=False,
        help_text=_("Campaign creation date."),
        db_index=True,
    )
    target_amount = models.CharField(
        _("target amount"),
        max_length=64,
        null=False,
        help_text=_("Campaign target amount."),
    )
    target_amount_usd = models.DecimalField(
        _("target amount in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Target amount in USD."),
    )
    min_amount = models.CharField(
        _("minimum amount"),
        max_length=64,
        null=True,
        blank=True,
        help_text=_("Campaign minimum amount."),
    )
    min_amount_usd = models.DecimalField(
        _("minimum amount in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Minimum amount in USD."),
    )
    max_amount = models.CharField(
        _("maximum amount"),
        max_length=64,
        null=True,
        blank=True,
        help_text=_("Campaign maximum amount."),
    )
    max_amount_usd = models.DecimalField(
        _("maximum amount in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Maximum amount in USD."),
    )
    total_raised_amount = models.CharField(
        _("total raised amount"),
        max_length=64,
        default="0",
        help_text=_("Campaign total raised amount."),
    )
    total_raised_amount_usd = models.DecimalField(
        _("total raised amount in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Total raised amount in USD."),
    )
    net_raised_amount = models.CharField(
        _("net raised amount"),
        max_length=64,
        default="0",
        help_text=_("Campaign net raised amount."),
    )
    net_raised_amount_usd = models.DecimalField(
        _("net raised amount in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Net raised amount in USD."),
    )
    escrow_balance = models.CharField(
        _("escrow balance"),
        max_length=64,
        default="0",
        help_text=_("Campaign escrow balance."),
    )
    escrow_balance_usd = models.DecimalField(
        _("escrow balance in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Escrow balance in USD."),
    )
    referral_fee_basis_points = models.PositiveIntegerField(
        _("referral fee basis points"),
        null=False,
        help_text=_("Referral fee basis points."),
    )
    creator_fee_basis_points = models.PositiveIntegerField(
        _("creator fee basis points"),
        null=False,
        help_text=_("Creator fee basis points."),
    )
    allow_fee_avoidance = models.BooleanField(
        _("allow fee avoidance"),
        null=False,
        default=False,
        help_text=_("Allow fee avoidance."),
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Campaign {self.on_chain_id}: {self.name}"

    def to_dict(self):
        return model_to_dict(self)

    async def fetch_usd_prices_async(self):
        fetch_prices = sync_to_async(self.fetch_usd_prices)
        await fetch_prices()

    def fetch_usd_prices(self):
        """Fetch USD prices for campaign amounts"""
        logger.info(f"fecthing usd price for {self.on_chain_id}")
        if not self.token:
            # For NEAR campaigns, we could fetch NEAR price here
            return

        try:
            token = self.token
            # Use campaign creation date for price lookup
            price_usd = token.fetch_usd_prices_common(self.created_at)
            if not price_usd:
                logger.info(
                    f"No USD price found for token {token.name} ({token.account.id}) at {self.created_at}"
                )
                return

            # Convert amounts to USD
            if self.target_amount:
                target_amount = token.format_price(self.target_amount)
                self.target_amount_usd = target_amount * price_usd

            if self.min_amount:
                min_amount = token.format_price(self.min_amount)
                self.min_amount_usd = min_amount * price_usd

            if self.max_amount:
                max_amount = token.format_price(self.max_amount)
                self.max_amount_usd = max_amount * price_usd

            if self.total_raised_amount:
                total_raised = token.format_price(self.total_raised_amount)
                self.total_raised_amount_usd = total_raised * price_usd

            if self.net_raised_amount:
                net_raised = token.format_price(self.net_raised_amount)
                self.net_raised_amount_usd = net_raised * price_usd

            if self.escrow_balance:
                escrow = token.format_price(self.escrow_balance)
                self.escrow_balance_usd = escrow * price_usd

            self.save()
            logger.info(f"Saved USD prices for campaign: {self.on_chain_id}")
        except Exception as e:
            logger.error(f"Failed to calculate and save USD prices for campaign {self.on_chain_id}: {e}")


class CampaignDonation(models.Model):
    id = models.AutoField(
        _("donation id"),
        primary_key=True,
        help_text=_("Donation id."),
    )
    on_chain_id = models.IntegerField(
        _("campaign donation id"),
        null=False,
        help_text=_("Campaign donation id in contract"),
        db_index=True,
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="donations",
        null=False,
        help_text=_("Campaign donation."),
        db_index=True,
    )
    donor = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="campaign_donations",
        null=False,
        help_text=_("Donor."),
        db_index=True,
    )
    token = models.ForeignKey(
        Token,
        on_delete=models.CASCADE,
        related_name="campaign_donations",
        null=True,
        blank=True,
        help_text=_("Donation token (null for NEAR)."),
        db_index=True,
    )
    total_amount = models.CharField(
        _("total amount"),
        max_length=64,
        null=False,
        help_text=_("Total amount."),
    )
    total_amount_usd = models.DecimalField(
        _("total amount in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
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
        blank=True,
        help_text=_("Net amount in USD."),
    )
    message = models.TextField(
        _("message"),
        max_length=1024,
        null=True,
        blank=True,
        help_text=_("Donation message."),
    )
    donated_at = models.DateTimeField(
        _("donated at"),
        null=False,
        help_text=_("Donation date."),
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
        blank=True,
        help_text=_("Protocol fee in USD."),
    )
    referrer = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="referred_campaign_donations",
        null=True,
        blank=True,
        help_text=_("Donation referrer."),
    )
    referrer_fee = models.CharField(
        _("referrer fee"),
        max_length=64,
        null=True,
        blank=True,
        help_text=_("Referrer fee."),
    )
    referrer_fee_usd = models.DecimalField(
        _("referrer fee in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Referrer fee in USD."),
    )
    creator_fee = models.CharField(
        _("creator fee"),
        max_length=64,
        null=True,
        blank=True,
        help_text=_("Creator fee."),
    )
    creator_fee_usd = models.DecimalField(
        _("creator fee in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Creator fee in USD."),
    )
    returned_at = models.DateTimeField(
        _("donation returned at"),
        null=True,
        blank=True,
        help_text=_("Donation returned date."),
        db_index=True,
    )

    escrowed = models.BooleanField(
        _("escrowed donation"),
        null=False,
        default=False,
        help_text=_("Is Donation Escrowed."),
    )

    tx_hash = models.CharField(
        _("transaction hash"),
        max_length=64,
        null=True,
        blank=True,
        help_text=_("Transaction hash."),
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["on_chain_id", "campaign"],
                name="unique_campaign_donation_id",
            ),
        ]
        ordering = ['-donated_at']

    def __str__(self):
        return f"Donation {self.on_chain_id} to Campaign {self.campaign.on_chain_id}"

    def to_dict(self):
        return model_to_dict(self)

    async def fetch_usd_prices_async(self):
        fetch_prices = sync_to_async(self.fetch_usd_prices)
        await fetch_prices()

    def fetch_usd_prices(self):
        """Fetch USD prices for campaign donation amounts"""
        try:
            # Use campaign token if donation token is not set
            token = self.token or self.campaign.token
            if not token:
                # For NEAR donations, we could fetch NEAR price here
                return

            price_usd = token.fetch_usd_prices_common(self.donated_at)
            if not price_usd:
                logger.info(
                    f"No USD price found for token {token.name} ({token.account.id}) at {self.donated_at}"
                )
                return

            # Calculate USD amounts
            total_amount = token.format_price(self.total_amount)
            net_amount = token.format_price(self.net_amount)
            protocol_amount = token.format_price(self.protocol_fee)
            referrer_amount = (
                None if not self.referrer_fee else token.format_price(self.referrer_fee)
            )
            creator_amount = (
                None if not self.creator_fee else token.format_price(self.creator_fee)
            )

            self.total_amount_usd = total_amount * price_usd
            self.net_amount_usd = net_amount * price_usd
            self.protocol_fee_usd = protocol_amount * price_usd
            self.referrer_fee_usd = (
                None if not referrer_amount else referrer_amount * price_usd
            )
            self.creator_fee_usd = (
                None if not creator_amount else creator_amount * price_usd
            )

            self.save()
            logger.info(f"Saved USD prices for campaign donation: {self.on_chain_id}")
        except Exception as e:
            logger.error(f"Failed to calculate and save USD prices for campaign donation {self.on_chain_id}: {e}")
