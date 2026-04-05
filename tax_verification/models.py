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
    # Fields auto-populated from IRS data via ProPublica
    legal_name = models.CharField(
        _("legal name"),
        max_length=255,
        help_text=_("Organization legal name from IRS records."),
    )
    address = models.CharField(
        _("address"),
        max_length=255,
        null=True,
        blank=True,
    )
    city = models.CharField(
        _("city"),
        max_length=100,
        null=True,
        blank=True,
    )
    state = models.CharField(
        _("state"),
        max_length=2,
        null=True,
        blank=True,
        help_text=_("US state code (e.g. CA, NY)."),
    )
    zip_code = models.CharField(
        _("zip code"),
        max_length=10,
        null=True,
        blank=True,
    )
    subsection_code = models.IntegerField(
        _("subsection code"),
        null=True,
        blank=True,
        help_text=_("IRS subsection code. 3 = 501(c)(3)."),
    )
    ntee_code = models.CharField(
        _("NTEE code"),
        max_length=10,
        null=True,
        blank=True,
        help_text=_("National Taxonomy of Exempt Entities code."),
    )
    ruling_date = models.CharField(
        _("ruling date"),
        max_length=20,
        null=True,
        blank=True,
        help_text=_("Date IRS granted tax-exempt status."),
    )
    status = models.CharField(
        _("verification status"),
        max_length=32,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True,
    )
    rejection_reason = models.CharField(
        _("rejection reason"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Reason for rejection if verification failed."),
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


class NonprofitRegistry(models.Model):
    ein = models.CharField(max_length=9, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    ico = models.CharField(max_length=255, blank=True)
    street = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, blank=True)
    zip = models.CharField(max_length=10, blank=True)
    group = models.CharField(max_length=4, blank=True)
    subsection = models.CharField(max_length=2, blank=True)
    affiliation = models.CharField(max_length=1, blank=True)
    classification = models.CharField(max_length=10, blank=True)
    ruling = models.CharField(max_length=6, blank=True)
    deductibility = models.CharField(max_length=1, blank=True)
    foundation = models.CharField(max_length=2, blank=True)
    activity = models.CharField(max_length=9, blank=True)
    organization = models.CharField(max_length=1, blank=True)
    status = models.CharField(max_length=2, blank=True)
    tax_period = models.CharField(max_length=6, blank=True)
    asset_cd = models.CharField(max_length=1, blank=True)
    income_cd = models.CharField(max_length=1, blank=True)
    filing_req_cd = models.CharField(max_length=2, blank=True)
    pf_filing_req_cd = models.CharField(max_length=1, blank=True)
    acct_pd = models.CharField(max_length=2, blank=True)
    asset_amt = models.CharField(max_length=20, blank=True)
    income_amt = models.CharField(max_length=20, blank=True)
    revenue_amt = models.CharField(max_length=20, blank=True)
    ntee_cd = models.CharField(max_length=4, blank=True)
    sort_name = models.CharField(max_length=255, blank=True)
    data_hash = models.CharField(max_length=32, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nonprofit_registry"
        verbose_name = "Nonprofit Registry Entry"
        verbose_name_plural = "Nonprofit Registry"
        indexes = [
            models.Index(fields=["subsection", "deductibility"]),
        ]

    def __str__(self):
        return f"{self.ein} - {self.name}"
