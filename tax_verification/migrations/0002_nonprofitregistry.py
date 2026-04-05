# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tax_verification", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="NonprofitRegistry",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("ein", models.CharField(db_index=True, max_length=9, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("ico", models.CharField(blank=True, max_length=255)),
                ("street", models.CharField(blank=True, max_length=255)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("state", models.CharField(blank=True, max_length=2)),
                ("zip", models.CharField(blank=True, max_length=10)),
                ("group", models.CharField(blank=True, max_length=4)),
                ("subsection", models.CharField(blank=True, max_length=2)),
                ("affiliation", models.CharField(blank=True, max_length=1)),
                ("classification", models.CharField(blank=True, max_length=10)),
                ("ruling", models.CharField(blank=True, max_length=6)),
                ("deductibility", models.CharField(blank=True, max_length=1)),
                ("foundation", models.CharField(blank=True, max_length=2)),
                ("activity", models.CharField(blank=True, max_length=9)),
                ("organization", models.CharField(blank=True, max_length=1)),
                ("status", models.CharField(blank=True, max_length=2)),
                ("tax_period", models.CharField(blank=True, max_length=6)),
                ("asset_cd", models.CharField(blank=True, max_length=1)),
                ("income_cd", models.CharField(blank=True, max_length=1)),
                ("filing_req_cd", models.CharField(blank=True, max_length=2)),
                ("pf_filing_req_cd", models.CharField(blank=True, max_length=1)),
                ("acct_pd", models.CharField(blank=True, max_length=2)),
                ("asset_amt", models.CharField(blank=True, max_length=20)),
                ("income_amt", models.CharField(blank=True, max_length=20)),
                ("revenue_amt", models.CharField(blank=True, max_length=20)),
                ("ntee_cd", models.CharField(blank=True, max_length=4)),
                ("sort_name", models.CharField(blank=True, max_length=255)),
                ("data_hash", models.CharField(blank=True, max_length=32)),
                ("last_updated", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Nonprofit Registry Entry",
                "verbose_name_plural": "Nonprofit Registry",
                "db_table": "nonprofit_registry",
                "indexes": [
                    models.Index(
                        fields=["subsection", "deductibility"],
                        name="nonprofit_re_subsect_idx",
                    ),
                ],
            },
        ),
    ]
