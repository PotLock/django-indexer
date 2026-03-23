from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.models import Account


class VerificationStatus(models.TextChoices):
    PENDING = "Pending", "Pending"
    APPROVED = "Approved", "Approved"
    REJECTED = "Rejected", "Rejected"


class OrganizationVerification(models.Model):
    id = models.AutoField(
        _("verification id"),
        primary_key=True,
    )
    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name="org_verification",
        help_text=_("NEAR account for this organization."),
    )
    ein = models.CharField(
        _("EIN"),
        max_length=10,
        help_text=_("Employer Identification Number (XX-XXXXXXX)."),
    )
    legal_name = models.CharField(
        _("legal name"),
        max_length=255,
        help_text=_("Organization legal name as registered with IRS."),
    )
    address_line1 = models.CharField(
        _("address line 1"),
        max_length=255,
    )
    address_line2 = models.CharField(
        _("address line 2"),
        max_length=255,
        null=True,
        blank=True,
    )
    city = models.CharField(
        _("city"),
        max_length=100,
    )
    state = models.CharField(
        _("state"),
        max_length=2,
        help_text=_("US state code (e.g. CA, NY)."),
    )
    zip_code = models.CharField(
        _("zip code"),
        max_length=10,
    )
    signer_name = models.CharField(
        _("authorized signer name"),
        max_length=255,
        help_text=_("Name of person authorized to sign tax receipts."),
    )
    signer_title = models.CharField(
        _("authorized signer title"),
        max_length=100,
        help_text=_("Title of authorized signer (e.g. Executive Director)."),
    )
    status = models.CharField(
        _("verification status"),
        max_length=32,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True,
    )
    admin_notes = models.TextField(
        _("admin notes"),
        max_length=1024,
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(
        _("submitted at"),
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        _("updated at"),
        auto_now=True,
    )

    class Meta:
        verbose_name = "Organization Verification"
        verbose_name_plural = "Organization Verifications"

    def __str__(self):
        return f"{self.legal_name} ({self.account_id}) - {self.status}"
