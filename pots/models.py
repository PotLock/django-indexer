from datetime import timedelta
from decimal import Decimal

import requests
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.models import Account
from base.logging import logger
from base.utils import format_date
from tokens.models import Token, TokenHistoricalPrice


class PotFactory(models.Model):
    id = models.OneToOneField(
        Account,
        primary_key=True,
        related_name="pot_factory",
        on_delete=models.CASCADE,
        help_text=_("Pot factory account ID."),
    )
    owner = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="owned_pot_factories",
        null=False,
        help_text=_("Pot factory owner."),
    )
    admins = models.ManyToManyField(
        Account,
        related_name="admin_pot_factories",
        help_text=_("Pot factory admins."),
    )
    whitelisted_deployers = models.ManyToManyField(
        Account,
        related_name="whitelisted_pot_factories",
        help_text=_("Pot factory whitelisted deployers."),
    )
    deployed_at = models.DateTimeField(
        _("deployed at"),
        null=False,
        help_text=_("Pot factory deployment date."),
    )
    source_metadata = models.JSONField(
        _("source metadata"),
        null=True,
        blank=True,
        help_text=_("Pot factory source metadata."),
    )
    protocol_fee_basis_points = models.PositiveIntegerField(
        _("protocol fee basis points"),
        null=False,
        help_text=_("Pot factory protocol fee basis points."),
    )
    protocol_fee_recipient = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="pot_factories_protocol_fee_recipient",
        null=False,
        help_text=_("Pot factory protocol fee recipient."),
    )
    require_whitelist = models.BooleanField(
        _("require whitelist"),
        null=False,
        help_text=_("Require whitelist."),
    )

    class Meta:
        verbose_name_plural = "Pot Factories"


class Pot(models.Model):
    id = models.OneToOneField(
        Account,
        primary_key=True,
        related_name="pot",
        on_delete=models.CASCADE,
        help_text=_("Pot account ID."),
    )
    pot_factory = models.ForeignKey(
        PotFactory,
        on_delete=models.CASCADE,
        related_name="pots",
        null=False,
        help_text=_("Pot factory."),
    )
    deployer = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="deployed_pots",
        null=False,
        help_text=_("Pot deployer."),
        db_index=True,
    )
    deployed_at = models.DateTimeField(
        _("deployed at"),
        null=False,
        help_text=_("Pot deployment date."),
        db_index=True,
    )
    source_metadata = models.JSONField(
        _("source metadata"),
        null=False,
        help_text=_("Pot source metadata."),
    )
    owner = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="owned_pots",
        null=False,
        help_text=_("Pot owner."),
    )
    admins = models.ManyToManyField(
        Account,
        related_name="admin_pots",
        help_text=_("Pot admins."),
    )
    chef = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="chef_pots",
        null=True,
        blank=True,
        help_text=_("Pot chef."),
    )
    name = models.TextField(
        _("name"),
        null=False,
        help_text=_("Pot name."),
    )
    description = models.TextField(
        _("description"),
        null=False,
        help_text=_("Pot description."),
    )
    max_approved_applicants = models.PositiveIntegerField(
        _("max approved applicants"),
        null=False,
        help_text=_("Max approved applicants."),
    )
    base_currency = models.CharField(
        _("base currency"),
        max_length=64,
        null=True,
        blank=True,
        help_text=_("Base currency."),
    )
    application_start = models.DateTimeField(
        _("application start"),
        null=False,
        help_text=_("Pot application start date."),
    )
    application_end = models.DateTimeField(
        _("application end"),
        null=False,
        help_text=_("Pot application end date."),
    )
    matching_round_start = models.DateTimeField(
        _("matching round start"),
        null=False,
        help_text=_("Pot matching round start date."),
    )
    matching_round_end = models.DateTimeField(
        _("matching round end"),
        null=False,
        help_text=_("Pot matching round end date."),
    )
    registry_provider = models.CharField(
        _("registry provider"),
        null=True,
        blank=True,
        help_text=_("Registry provider."),
    )
    min_matching_pool_donation_amount = models.CharField(
        _("min matching pool donation amount"),
        null=False,
        help_text=_("Min matching pool donation amount."),
    )
    sybil_wrapper_provider = models.CharField(
        _("sybil wrapper provider"),
        null=True,
        blank=True,
        help_text=_("Sybil wrapper provider."),
    )
    custom_sybil_checks = models.CharField(
        _("custom sybil checks"),
        null=True,
        blank=True,
        help_text=_("Custom sybil checks."),
    )
    custom_min_threshold_score = models.PositiveIntegerField(
        _("custom min threshold score"),
        null=True,
        blank=True,
        help_text=_("Custom min threshold score."),
    )
    referral_fee_matching_pool_basis_points = models.PositiveIntegerField(
        _("referral fee matching pool basis points"),
        null=False,
        help_text=_("Referral fee matching pool basis points."),
    )
    referral_fee_public_round_basis_points = models.PositiveIntegerField(
        _("referral fee public round basis points"),
        null=False,
        help_text=_("Referral fee public round basis points."),
    )
    chef_fee_basis_points = models.PositiveIntegerField(
        _("chef fee basis points"),
        null=False,
        help_text=_("Chef fee basis points."),
    )
    total_matching_pool = models.CharField(
        _("total matching pool"),
        null=False,
        help_text=_("Total matching pool."),
    )
    total_matching_pool_usd = models.DecimalField(
        _("total matching pool in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Total matching pool in USD."),
    )
    matching_pool_balance = models.CharField(
        _("matching pool balance"),
        null=False,
        help_text=_("Matching pool balance."),
    )
    matching_pool_donations_count = models.PositiveIntegerField(
        _("matching pool donations count"),
        null=False,
        help_text=_("Matching pool donations count."),
    )
    total_public_donations = models.CharField(
        _("total public donations"),
        null=False,
        help_text=_("Total public donations."),
    )
    total_public_donations_usd = models.DecimalField(
        _("total public donations in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Total public donations in USD."),
    )
    public_donations_count = models.PositiveIntegerField(
        _("public donations count"),
        null=False,
        help_text=_("Public donations count."),
    )
    cooldown_end = models.DateTimeField(
        _("cooldown end"),
        null=True,
        blank=True,
        help_text=_("Pot cooldown end date."),
    )
    cooldown_period_ms = models.PositiveIntegerField(
        _("cooldown period in ms"),
        null=True,
        blank=True,
        help_text=_("Pot cooldown period in ms."),
    )
    all_paid_out = models.BooleanField(
        _("all paid out"),
        null=False,
        help_text=_("All paid out."),
    )
    protocol_config_provider = models.CharField(
        _("protocol config provider"),
        null=True,
        blank=True,
        help_text=_("Protocol config provider."),
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["application_start", "application_end"],
                name="idx_application_period",
            ),
            models.Index(
                fields=["matching_round_start", "matching_round_end"],
                name="idx_matching_period",
            ),
        ]


class PotApplicationStatus(models.TextChoices):
    PENDING = "Pending", "Pending"
    APPROVED = "Approved", "Approved"
    REJECTED = "Rejected", "Rejected"
    INREVIEW = "InReview", "InReview"


class PotApplication(models.Model):
    id = models.AutoField(
        _("application id"),
        primary_key=True,
        help_text=_("Application id."),
    )
    pot = models.ForeignKey(
        Pot,
        on_delete=models.CASCADE,
        related_name="applications",
        null=False,
        help_text=_("Pot applied to."),
        db_index=True,
    )
    applicant = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="pot_applications",
        null=False,
        help_text=_("Account that applied to the pot."),
        db_index=True,
    )
    message = models.TextField(
        _("message"),
        max_length=1024,
        null=True,
        blank=True,
        help_text=_("Application message."),
    )
    status = models.CharField(
        _("status"),
        max_length=32,
        null=False,
        choices=PotApplicationStatus.choices,
        help_text=_("Application status."),
    )
    submitted_at = models.DateTimeField(
        _("submitted at"),
        null=False,
        help_text=_("Application submission date."),
        db_index=True,
    )
    updated_at = models.DateTimeField(
        _("updated at"),
        null=True,
        blank=True,
        help_text=_("Application last update date."),
    )
    tx_hash = models.CharField(
        _("transaction hash"),
        null=True,
        blank=True,
        help_text=_("Transaction hash."),
    )

    class Meta:
        verbose_name_plural = "Pot Applications"

        unique_together = (("pot", "applicant"),)

    def __str__(self):
        return f"{self.applicant.id} - {self.pot}"


class PotApplicationReview(models.Model):
    id = models.AutoField(
        _("review id"),
        primary_key=True,
        help_text=_("Review id."),
    )
    application = models.ForeignKey(
        PotApplication,
        on_delete=models.CASCADE,
        related_name="reviews",
        null=False,
        help_text=_("Application reviewed."),
    )
    reviewer = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="pot_application_reviews",
        null=False,
        help_text=_("Account that reviewed the application."),
    )
    notes = models.TextField(
        _("notes"),
        max_length=1024,
        null=True,
        blank=True,
        help_text=_("Review notes."),
    )
    status = models.CharField(
        _("status"),
        max_length=32,
        null=False,
        choices=PotApplicationStatus.choices,
        help_text=_("Application status for this review."),
    )
    reviewed_at = models.DateTimeField(
        _("reviewed at"),
        null=False,
        help_text=_("Review date."),
    )
    tx_hash = models.CharField(
        _("transaction hash"),
        null=True,
        blank=True,
        help_text=_("Transaction hash."),
    )

    class Meta:
        verbose_name_plural = "Pot Application Reviews"

        unique_together = (("application", "reviewer", "reviewed_at"),)


class PotPayout(models.Model):
    id = models.AutoField(
        _("payout id"),
        primary_key=True,
        help_text=_("Payout id."),
    )
    pot = models.ForeignKey(
        Pot,
        on_delete=models.CASCADE,
        related_name="payouts",
        null=False,
        help_text=_("Pot that this payout is for."),
        db_index=True,
    )
    recipient = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="pot_payouts",
        null=False,
        help_text=_("Payout recipient."),
        db_index=True,
    )
    amount = models.CharField(
        _("amount"),
        null=False,
        help_text=_("Payout amount."),
    )
    amount_paid_usd = models.DecimalField(
        _("amount paid in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Payout amount in USD."),
    )
    token = models.ForeignKey(
        Token,
        on_delete=models.CASCADE,
        related_name="pot_payouts",
        null=False,
        help_text=_("Payout token."),
    )
    paid_at = models.DateTimeField(
        _("paid at"),
        null=True,
        blank=True,
        help_text=_("Payout date."),
        db_index=True,
    )
    tx_hash = models.CharField(
        _("transaction hash"),
        null=True,
        blank=True,
        help_text=_("Transaction hash."),
    )

    ### Fetches USD prices for the Donation record and saves USD totals
    def fetch_usd_prices(self):
        # first, see if there is a TokenHistoricalPrice within 1 day (or HISTORICAL_PRICE_QUERY_HOURS) of self.paid_at
        try:
            token = self.token
            price_usd = token.fetch_usd_prices_common(self.paid_at)
            if not price_usd:
                logger.info(
                    f"No USD price found for token {self.token.symbol} at {self.paid_at}"
                )
                return
            self.amount_paid_usd = token.format_price(self.amount) * price_usd
            self.save()
            logger.info(f"Saved USD prices for pot payout for pot id: {self.pot.id}")
        except Exception as e:
            logger.error(f"Failed to calculate and save USD prices: {e}")


class PotPayoutChallenge(models.Model):
    id = models.AutoField(
        _("challenge id"),
        primary_key=True,
        help_text=_("Challenge id."),
    )
    challenger = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="pot_payout_challenges",
        null=False,
        help_text=_("Payout challenger."),
    )
    pot = models.ForeignKey(
        Pot,
        on_delete=models.CASCADE,
        related_name="challenges",
        null=False,
        help_text=_("Pot challenged."),
    )
    created_at = models.DateTimeField(
        _("created at"),
        null=False,
        help_text=_("Challenge creation date."),
    )
    message = models.TextField(
        _("message"),
        max_length=1024,
        null=False,
        help_text=_("Challenge message."),
    )

    class Meta:
        verbose_name_plural = "Payout Challenges"

        unique_together = (("challenger", "pot"),)


class PotPayoutChallengeAdminResponse(models.Model):
    id = models.AutoField(
        _("Admin response id"),
        primary_key=True,
        help_text=_("Admin response id."),
    )
    challenger = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="payout_admin_responses",
        null=True,
        blank=True,
        help_text=_("challenger being responded to."),
    )

    pot = models.ForeignKey(
        Pot,
        on_delete=models.CASCADE,
        related_name="payout_responses",
        null=True,
        blank=True,
        help_text=_("Pot being challenged."),
    )

    admin = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="pot_payout_challenge_admin_responses",
        null=False,
        help_text=_("Admin that responded to the challenge."),
    )
    created_at = models.DateTimeField(
        _("created at"),
        null=False,
        help_text=_("Admin response creation date."),
    )
    message = models.TextField(
        _("message"),
        max_length=1024,
        null=False,
        help_text=_("Admin response message."),
    )
    resolved = models.BooleanField(
        _("resolved"),
        null=False,
        help_text=_("Admin response resolution status."),
    )
    tx_hash = models.CharField(
        _("transaction hash"),
        null=True,
        blank=True,
        help_text=_("Transaction hash."),
    )

    class Meta:
        verbose_name_plural = "Payout Challenge Responses"

        unique_together = (("challenger", "pot", "created_at"),)
