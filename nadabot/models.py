from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.models import Account


class ProviderStatus(models.TextChoices):
    PENDING = "Pending", "Pending"
    ACTIVE = "Active", "Active"
    DEACTIVATED = "Deactivated", "Deactivated"


class RuleType(models.TextChoices):
    HIGHEST = 'Highest'
    LOWEST = 'Lowest'
    SUM = 'Sum'
    DIMINISHING_RETURNS = 'Diminishing_returns'
    INCREASING_RETURNS = 'Increasing_returns'



class NadabotRegistry(models.Model):
    account = models.OneToOneField(
        Account,
        related_name="registry_id",
        on_delete=models.CASCADE,
        primary_key=True,
        help_text=_("Nadabot registry id."),
    )
    owner = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="nadabot_owner_registries",
        null=False,
        help_text=_("Nadabot Registry owner."),
    )
    default_human_threshold = models.PositiveIntegerField(
        _("default human threshold"),
        default=0,
        help_text=_("default human threshold."),
    )
    created_at = models.DateTimeField(
        _("created at"),
        null=False,
        help_text=_("Registry creation date."),
    )
    updated_at = models.DateTimeField(
        _("updated at"),
        help_text=_("Registry last update date."),
    )
    admins = models.ManyToManyField(
        Account,
        related_name="nadabot_admin_registries",
        help_text=_("registry admins."),
    )
    blacklisted_accounts = models.ManyToManyField(
        Account,
        related_name="registry_blacklisted_in",
        help_text=_("registry blacklisted accounts."),
    )
    source_metadata = models.JSONField(
        _("source metadata"),
        null=False,
        help_text=_("nadabot registry source metadata."),
    )


class BlackList(models.Model):
    registry = models.ForeignKey(
        NadabotRegistry,
        on_delete=models.CASCADE,
        related_name="blacklists",
        verbose_name=_("registry"),
        help_text=_("blacklist entries by this registry")
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="registries_blacklisted_from",
        null=False,
        help_text=_("Nadabot Registry Blacklisted from."),
    )
    reason = models.TextField(
        _("blacklist reason"),
        blank=True,
        null=True,
        help_text=_("Reason account is blacklisted")
    )
    date_blacklisted = models.DateTimeField(
        _("blacklisted on"),
        null=False,
        help_text=_("Blacklist Entry Date."),
    )

    class Meta:
        unique_together = ['registry', 'account']

class Provider(models.Model):
    id = models.AutoField(
        _("provider id"),
        primary_key=True,
        help_text=_("Provider id.")
    )
    on_chain_id = models.IntegerField(
        _("contract provider id"),
        null=False,
        help_text=_("Provider id in contract"),
    )
    contract = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="provider_instances",
        verbose_name=_("contract ID"),
        max_length=100,
        null=False,
        help_text=_("Contract ID of the external contract that is the source of this provider.")
    )
    method_name = models.CharField(
        _("method name"),
        max_length=100,
        null=False,
        help_text=_("Method name of the external contract that is the source of this provider.")
    )
    name = models.CharField(
        _("provider name"),
        max_length=64,
        null=False,
        help_text=_("Name of the provider, e.g. 'I Am Human'.")
    )
    description = models.TextField(
        _("description"),
        blank=True,
        null=True,
        help_text=_("Description of the provider.")
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=ProviderStatus,
        null=False,
        db_index=True,
        help_text=_("Status of the provider.")
    )
    admin_notes = models.TextField(
        _("admin notes"),
        blank=True,
        null=True,
        help_text=_("Admin notes, e.g. reason for flagging or marking inactive.")
    )
    default_weight = models.PositiveIntegerField(
        _("default weight"),
        null=False,
        help_text=_("Default weight for this provider, e.g. 100.")
    )
    gas = models.BigIntegerField(
        _("gas"),
        blank=True,
        null=True,
        help_text=_("Custom gas amount required.")
    )
    tags = models.JSONField(
        _("tags"),
        blank=True,
        null=True,
        help_text=_("Optional tags.")
    )
    icon_url = models.URLField(
        _("icon URL"),
        blank=True,
        null=True,
        help_text=_("Optional icon URL.")
    )
    external_url = models.URLField(
        _("external URL"),
        blank=True,
        null=True,
        help_text=_("Optional external URL.")
    )
    submitted_by = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="providers_submitted",
        verbose_name=_("submitted by"),
        max_length=100,
        null=False,
        help_text=_("User who submitted this provider.")
    )
    submitted_at = models.DateTimeField(
        _("submitted at (milliseconds)"),
        null=False,
        db_index=True,
        help_text=_("Timestamp of when this provider was submitted.")
    )
    stamp_validity_ms = models.BigIntegerField(
        _("stamp validity"),
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Milliseconds that stamps from this provider are valid for before they expire.")
    )
    account_id_arg_name = models.CharField(
        _("account ID argument name"),
        max_length=100,
        null=False,
        help_text=_("Name of account ID argument, e.g. 'account_id' or 'accountId' or 'account'.")
    )
    custom_args = models.CharField(
        _("custom args"),
        null=True,
        blank=True,
        help_text=_("Custom args as Base64VecU8.")
    )
    registry = models.ForeignKey(
        NadabotRegistry,
        on_delete=models.CASCADE,
        related_name="providers",
        verbose_name=_("registry"),
        help_text=_("registry under which provider was registered")
    )

class Stamp(models.Model):
    user = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="stamps",
        verbose_name=_("user"),
        help_text=_("The user who earned the stamp.")
    )
    provider = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        related_name="stamps",
        verbose_name=_("provider"),
        help_text=_("The provider the user verified with.")
    )
    verified_at = models.DateField(
        _("verification date"),
        help_text=_("The date of verification.")
    )

class Group(models.Model):
    id = models.PositiveIntegerField(
        _("group id"),
        primary_key=True,
        help_text=_("Group id."),
    )
    name = models.CharField(
        _("group name"),
        max_length=100,
        null=False,
        help_text=_("name given to the group")
    )
    rule_type = models.CharField(
        _("rule type"),
        choices=RuleType,
        max_length=100,
        null=True,
        blank=True,
        help_text=_("The rule this group uses.")
    )
    rule_val = models.PositiveIntegerField(
        _("rule value"),
        null=True,
        blank=True,
        help_text=_("An optional value that the group's rule choices might carry."),
    )
    providers = models.ManyToManyField(
        Provider,
        related_name="groups",
        help_text=_("group providers."),
    )
    created_at = models.DateTimeField(
        _("created at"),
        null=False,
        help_text=_("Group creation date."),
    )
    updated_at = models.DateTimeField(
        _("updated at"),
        help_text=_("Group last update date."),
    )
