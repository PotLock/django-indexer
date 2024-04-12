from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.models import Account

## DONATIONS


class Donation(models.Model):
    id = models.AutoField(
        _("donation id"),
        primary_key=True,
        help_text=_("Donation id."),
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


## ACTIVITIES


class ActivityType(models.TextChoices):
    DONATE_DIRECT = "Donate_Direct", "Donate Direct"
    DONATE_POT_PUBLIC = "Donate_Pot_Public", "Donate Pot Public"
    DONATE_POT_MATCHING_POOL = "Donate_Pot_Matching_Pool", "Donate Pot Matching Pool"
    REGISTER = "Register", "Register"
    REGISTER_BATCH = "Register_Batch", "Register Batch"
    DEPLOY_POT = "Deploy_Pot", "Deploy Pot"
    PROCESS_PAYOUTS = "Process_Payouts", "Process Payouts"
    CHALLENGE_PAYOUT = "Challenge_Payout", "Challenge Payout"
    SUBMIT_APPLICATION = "Submit_Application", "Submit Application"
    UPDATE_POT_CONFIG = "Update_Pot_Config", "Update Pot Config"
    ADD_LIST_ADMIN = "Add_List_Admin", "Add List Admin"
    REMOVE_LIST_ADMIN = "Remove_List_Admin", "Remove List Admin"


class Activity(models.Model):
    id = models.AutoField(
        _("activity id"),
        primary_key=True,
        help_text=_("Activity id."),
    )
    signer = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="signed_activities",
        null=False,
        help_text=_("Signer."),
    )
    receiver = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="received_activities",
        null=False,
        help_text=_("Receiver."),
    )
    timestamp = models.DateTimeField(
        _("timestamp"),
        null=False,
        help_text=_("Activity timestamp."),
        db_index=True,
    )
    action_result = models.JSONField(
        _("action result"),
        null=True,
        help_text=_("Activity action result."),
    )
    tx_hash = models.CharField(
        _("transaction hash"),
        max_length=64,
        null=False,
        help_text=_("Transaction hash."),
    )
    type = models.CharField(
        _("type"),
        max_length=32,
        null=False,
        choices=ActivityType.choices,
        help_text=_("Activity type."),
    )


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
