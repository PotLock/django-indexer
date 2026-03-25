from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tax_verification", "0001_initial"),
    ]

    operations = [
        # Remove old manual-review fields
        migrations.RemoveField(
            model_name="organizationverification",
            name="address_line1",
        ),
        migrations.RemoveField(
            model_name="organizationverification",
            name="address_line2",
        ),
        migrations.RemoveField(
            model_name="organizationverification",
            name="signer_name",
        ),
        migrations.RemoveField(
            model_name="organizationverification",
            name="signer_title",
        ),
        migrations.RemoveField(
            model_name="organizationverification",
            name="admin_notes",
        ),
        # Add new IRS data fields
        migrations.AddField(
            model_name="organizationverification",
            name="address",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name="address",
            ),
        ),
        migrations.AddField(
            model_name="organizationverification",
            name="subsection_code",
            field=models.IntegerField(
                blank=True,
                help_text="IRS subsection code. 3 = 501(c)(3).",
                null=True,
                verbose_name="subsection code",
            ),
        ),
        migrations.AddField(
            model_name="organizationverification",
            name="ntee_code",
            field=models.CharField(
                blank=True,
                help_text="National Taxonomy of Exempt Entities code.",
                max_length=10,
                null=True,
                verbose_name="NTEE code",
            ),
        ),
        migrations.AddField(
            model_name="organizationverification",
            name="ruling_date",
            field=models.CharField(
                blank=True,
                help_text="Date IRS granted tax-exempt status.",
                max_length=20,
                null=True,
                verbose_name="ruling date",
            ),
        ),
        migrations.AddField(
            model_name="organizationverification",
            name="rejection_reason",
            field=models.CharField(
                blank=True,
                help_text="Reason for rejection if verification failed.",
                max_length=255,
                null=True,
                verbose_name="rejection reason",
            ),
        ),
        # Make city, state, zip_code nullable (populated from IRS, not user)
        migrations.AlterField(
            model_name="organizationverification",
            name="city",
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name="city",
            ),
        ),
        migrations.AlterField(
            model_name="organizationverification",
            name="state",
            field=models.CharField(
                blank=True,
                help_text="US state code (e.g. CA, NY).",
                max_length=2,
                null=True,
                verbose_name="state",
            ),
        ),
        migrations.AlterField(
            model_name="organizationverification",
            name="zip_code",
            field=models.CharField(
                blank=True,
                max_length=10,
                null=True,
                verbose_name="zip code",
            ),
        ),
        # Update legal_name help text
        migrations.AlterField(
            model_name="organizationverification",
            name="legal_name",
            field=models.CharField(
                help_text="Organization legal name from IRS records.",
                max_length=255,
                verbose_name="legal name",
            ),
        ),
    ]
