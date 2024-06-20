from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.models import Account


class ListRegistrationStatus(models.TextChoices):
    PENDING = "Pending", "Pending"
    APPROVED = "Approved", "Approved"
    REJECTED = "Rejected", "Rejected"
    GRAYLISTED = "Graylisted", "Graylisted"
    BLACKLISTED = "Blacklisted", "Blacklisted"


class List(models.Model):
    id = models.AutoField(
        _("list id"),
        primary_key=True,
        help_text=_("List ID in DB (does not necessarily correspond to on-chain ID)."),
    )
    on_chain_id = models.IntegerField(
        _("contract list ID"),
        null=False,
        unique=True,
        help_text=_("List ID in contract"),
    )
    owner = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="lists",
        null=False,
        help_text=_("List owner."),
    )
    admins = models.ManyToManyField(
        Account,
        related_name="admin_lists",
        help_text=_("List admins."),
    )
    name = models.CharField(
        _("name"),
        max_length=64,
        null=False,
        help_text=_("List name."),
    )
    description = models.TextField(
        _("description"),
        max_length=256,
        null=True,
        help_text=_("List description."),
    )
    cover_image_url = models.URLField(
        _("cover image url"),
        null=True,
        help_text=_("Cover image url."),
    )
    admin_only_registrations = models.BooleanField(
        _("admin only registrations"),
        null=False,
        help_text=_("Admin only registrations."),
    )
    default_registration_status = models.CharField(
        _("default registration status"),
        max_length=32,
        null=False,
        choices=ListRegistrationStatus.choices,
        help_text=_("Default registration status."),
    )
    created_at = models.DateTimeField(
        _("created at"),
        null=False,
        help_text=_("List creation date."),
    )
    updated_at = models.DateTimeField(
        _("updated at"),
        help_text=_("List last update date."),
    )

    class Meta:
        indexes = [
            models.Index(fields=["created_at", "updated_at"], name="idx_list_stamps")
        ]


class ListUpvote(models.Model):
    id = models.AutoField(
        _("upvote id"),
        primary_key=True,
        help_text=_("Upvote id."),
    )
    list = models.ForeignKey(
        List,
        on_delete=models.CASCADE,
        related_name="upvotes",
        null=False,
        help_text=_("List upvoted."),
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="upvoted_lists",
        null=False,
        help_text=_("Account that upvoted the list."),
    )
    created_at = models.DateTimeField(
        _("created at"),
        null=False,
        help_text=_("Upvote creation date."),
    )

    class Meta:
        verbose_name_plural = "List Upvotes"

        unique_together = (("list", "account"),)


class ListRegistration(models.Model):
    id = models.AutoField(
        _("registration id"),
        primary_key=True,
        help_text=_("Registration id."),
    )
    list = models.ForeignKey(
        List,
        on_delete=models.CASCADE,
        related_name="registrations",
        null=False,
        help_text=_("List registered."),
    )
    registrant = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="list_registrations",
        null=False,
        help_text=_("Account that registered on the list."),
    )
    registered_by = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="list_registrars",
        null=False,
        help_text=_("Account that did the registration."),
    )
    status = models.CharField(
        _("registration status"),
        max_length=32,
        null=False,
        choices=ListRegistrationStatus.choices,
        help_text=_("Registration status."),
        db_index=True,
    )
    submitted_at = models.DateTimeField(
        _("submitted at"),
        null=False,
        help_text=_("Registration submission date."),
    )
    updated_at = models.DateTimeField(
        _("updated at"),
        help_text=_("Registration last update date."),
    )
    registrant_notes = models.TextField(
        _("registrant notes"),
        max_length=1024,
        null=True,
        help_text=_("Registrant notes."),
    )
    admin_notes = models.TextField(
        _("admin notes"),
        max_length=1024,
        null=True,
        help_text=_("Admin notes."),
    )
    tx_hash = models.CharField(
        _("transaction hash"),
        max_length=64,
        null=True,
        help_text=_("Transaction hash."),
    )

    class Meta:
        indexes = [models.Index(fields=["id", "status"], name="idx_list_id_status")]

        unique_together = (("list", "registrant"),)
