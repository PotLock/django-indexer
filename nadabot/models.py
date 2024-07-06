from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.models import Account


class ProviderStatus(models.TextChoices):
    PENDING = "Pending", "Pending"
    ACTIVE = "Active", "Active"
    DEACTIVATED = "Deactivated", "Deactivated"


class NadabotRegistry(models.Model):
    id = models.OneToOneField(
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
    source_metadata = models.JSONField(
        _("source metadata"),
        null=False,
        help_text=_("nadabot registry source metadata."),
    )

class Provider(models.Model):
    id = models.PositiveIntegerField(
        _("provider id"),
        primary_key=True,
        help_text=_("Provider id."),
    )
    contract_id = models.CharField(
        _("contract ID"),
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
    provider_name = models.CharField(
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
        verbose_name=_("submitted by"),
        max_length=100,
        null=False,
        help_text=_("User who submitted this provider.")
    )
    submitted_at_ms = models.DateTimeField(
        _("submitted at (milliseconds)"),
        null=False,
        help_text=_("Timestamp of when this provider was submitted.")
    )
    stamp_validity_ms = models.BigIntegerField(
        _("stamp validity"),
        blank=True,
        null=True,
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
        help_text=_("Custom args as Base64VecU8.")
    )
    registry = models.ForeignKey(
        NadabotRegistry,
        on_delete=models.CASCADE,
        verbose_name=_("registry"),
        help_text=_("registry under which provider was registered")
    )

    class Meta:
        indexes = [models.Index(fields=["id", "status"], name="idx_provider_id_status")]


class Stamp(models.Model):
    user = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        verbose_name=_("user"),
        help_text=_("The user who earned the stamp.")
    )
    provider = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        verbose_name=_("provider"),
        help_text=_("The provider the user verified with.")
    )
    verification_date = models.DateField(
        _("verification date"),
        auto_now_add=True,
        help_text=_("The date of verification.")
    )

class Rule(models.Model):
    id = models.AutoField(
        _("rule id"),
        primary_key=True,
        help_text=_("rule id for group rules"),
    )
    rule = models.CharField(
        _("rule enum choice"),
        max_length=50,
        null=False,
        help_text=_("particular rule choice from the rule enum")
    )
    value = models.PositiveIntegerField(
        _("rule value"),
        null=True,
        help_text=_("An optional value that rule choices might carry."),
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
    group_rule = models.ForeignKey(
        Rule,
        on_delete=models.CASCADE,
        verbose_name=_("rule"),
        help_text=_("The rule this group uses.")
    )
    providers = models.ManyToManyField(
        Provider,
        related_name="group_provider",
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
