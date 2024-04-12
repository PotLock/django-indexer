from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.models import Account

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
