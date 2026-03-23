from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrganizationVerification",
            fields=[
                (
                    "id",
                    models.AutoField(
                        primary_key=True,
                        serialize=False,
                        verbose_name="verification id",
                    ),
                ),
                (
                    "ein",
                    models.CharField(
                        help_text="Employer Identification Number (XX-XXXXXXX).",
                        max_length=10,
                        verbose_name="EIN",
                    ),
                ),
                (
                    "legal_name",
                    models.CharField(
                        help_text="Organization legal name as registered with IRS.",
                        max_length=255,
                        verbose_name="legal name",
                    ),
                ),
                (
                    "address_line1",
                    models.CharField(
                        max_length=255,
                        verbose_name="address line 1",
                    ),
                ),
                (
                    "address_line2",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        verbose_name="address line 2",
                    ),
                ),
                (
                    "city",
                    models.CharField(
                        max_length=100,
                        verbose_name="city",
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        help_text="US state code (e.g. CA, NY).",
                        max_length=2,
                        verbose_name="state",
                    ),
                ),
                (
                    "zip_code",
                    models.CharField(
                        max_length=10,
                        verbose_name="zip code",
                    ),
                ),
                (
                    "signer_name",
                    models.CharField(
                        help_text="Name of person authorized to sign tax receipts.",
                        max_length=255,
                        verbose_name="authorized signer name",
                    ),
                ),
                (
                    "signer_title",
                    models.CharField(
                        help_text="Title of authorized signer (e.g. Executive Director).",
                        max_length=100,
                        verbose_name="authorized signer title",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("Pending", "Pending"),
                            ("Approved", "Approved"),
                            ("Rejected", "Rejected"),
                        ],
                        db_index=True,
                        default="Pending",
                        max_length=32,
                        verbose_name="verification status",
                    ),
                ),
                (
                    "admin_notes",
                    models.TextField(
                        blank=True,
                        max_length=1024,
                        null=True,
                        verbose_name="admin notes",
                    ),
                ),
                (
                    "submitted_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="submitted at",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="updated at",
                    ),
                ),
                (
                    "account",
                    models.OneToOneField(
                        help_text="NEAR account for this organization.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="org_verification",
                        to="accounts.account",
                    ),
                ),
            ],
            options={
                "verbose_name": "Organization Verification",
                "verbose_name_plural": "Organization Verifications",
            },
        ),
    ]
