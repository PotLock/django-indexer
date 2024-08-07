# Generated by Django 5.0.6 on 2024-07-11 14:21

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0002_account_near_social_profile_data"),
    ]

    operations = [
        migrations.CreateModel(
            name="NadabotRegistry",
            fields=[
                (
                    "id",
                    models.OneToOneField(
                        help_text="Nadabot registry id.",
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="registry_id",
                        serialize=False,
                        to="accounts.account",
                    ),
                ),
                (
                    "default_human_threshold",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="default human threshold.",
                        verbose_name="default human threshold",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        help_text="Registry creation date.", verbose_name="created at"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        help_text="Registry last update date.",
                        verbose_name="updated at",
                    ),
                ),
                (
                    "source_metadata",
                    models.JSONField(
                        help_text="nadabot registry source metadata.",
                        verbose_name="source metadata",
                    ),
                ),
                (
                    "admins",
                    models.ManyToManyField(
                        help_text="registry admins.",
                        related_name="nadabot_admin_registries",
                        to="accounts.account",
                    ),
                ),
                (
                    "blacklisted_accounts",
                    models.ManyToManyField(
                        help_text="registry blacklisted accounts.",
                        related_name="registry_blacklisted_in",
                        to="accounts.account",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        help_text="Nadabot Registry owner.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="nadabot_owner_registries",
                        to="accounts.account",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Provider",
            fields=[
                (
                    "id",
                    models.AutoField(
                        help_text="Provider id.",
                        primary_key=True,
                        serialize=False,
                        verbose_name="provider id",
                    ),
                ),
                (
                    "on_chain_id",
                    models.IntegerField(
                        help_text="Provider id in contract",
                        verbose_name="contract provider id",
                    ),
                ),
                (
                    "method_name",
                    models.CharField(
                        help_text="Method name of the external contract that is the source of this provider.",
                        max_length=100,
                        verbose_name="method name",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Name of the provider, e.g. 'I Am Human'.",
                        max_length=64,
                        verbose_name="provider name",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Description of the provider.",
                        null=True,
                        verbose_name="description",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("Pending", "Pending"),
                            ("Active", "Active"),
                            ("Deactivated", "Deactivated"),
                        ],
                        db_index=True,
                        help_text="Status of the provider.",
                        max_length=20,
                        verbose_name="status",
                    ),
                ),
                (
                    "admin_notes",
                    models.TextField(
                        blank=True,
                        help_text="Admin notes, e.g. reason for flagging or marking inactive.",
                        null=True,
                        verbose_name="admin notes",
                    ),
                ),
                (
                    "default_weight",
                    models.PositiveIntegerField(
                        help_text="Default weight for this provider, e.g. 100.",
                        verbose_name="default weight",
                    ),
                ),
                (
                    "gas",
                    models.BigIntegerField(
                        blank=True,
                        help_text="Custom gas amount required.",
                        null=True,
                        verbose_name="gas",
                    ),
                ),
                (
                    "tags",
                    models.JSONField(
                        blank=True,
                        help_text="Optional tags.",
                        null=True,
                        verbose_name="tags",
                    ),
                ),
                (
                    "icon_url",
                    models.URLField(
                        blank=True,
                        help_text="Optional icon URL.",
                        null=True,
                        verbose_name="icon URL",
                    ),
                ),
                (
                    "external_url",
                    models.URLField(
                        blank=True,
                        help_text="Optional external URL.",
                        null=True,
                        verbose_name="external URL",
                    ),
                ),
                (
                    "submitted_at",
                    models.DateTimeField(
                        db_index=True,
                        help_text="Timestamp of when this provider was submitted.",
                        verbose_name="submitted at (milliseconds)",
                    ),
                ),
                (
                    "stamp_validity_ms",
                    models.BigIntegerField(
                        blank=True,
                        db_index=True,
                        help_text="Milliseconds that stamps from this provider are valid for before they expire.",
                        null=True,
                        verbose_name="stamp validity",
                    ),
                ),
                (
                    "account_id_arg_name",
                    models.CharField(
                        help_text="Name of account ID argument, e.g. 'account_id' or 'accountId' or 'account'.",
                        max_length=100,
                        verbose_name="account ID argument name",
                    ),
                ),
                (
                    "custom_args",
                    models.CharField(
                        help_text="Custom args as Base64VecU8.",
                        null=True,
                        verbose_name="custom args",
                    ),
                ),
                (
                    "contract",
                    models.ForeignKey(
                        help_text="Contract ID of the external contract that is the source of this provider.",
                        max_length=100,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="provider_instances",
                        to="accounts.account",
                        verbose_name="contract ID",
                    ),
                ),
                (
                    "registry",
                    models.ForeignKey(
                        help_text="registry under which provider was registered",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="providers",
                        to="nadabot.nadabotregistry",
                        verbose_name="registry",
                    ),
                ),
                (
                    "submitted_by",
                    models.ForeignKey(
                        help_text="User who submitted this provider.",
                        max_length=100,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="providers_submitted",
                        to="accounts.account",
                        verbose_name="submitted by",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Group",
            fields=[
                (
                    "id",
                    models.PositiveIntegerField(
                        help_text="Group id.",
                        primary_key=True,
                        serialize=False,
                        verbose_name="group id",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="name given to the group",
                        max_length=100,
                        verbose_name="group name",
                    ),
                ),
                (
                    "rule_type",
                    models.CharField(
                        choices=[
                            ("Highest", "Highest"),
                            ("Lowest", "Lowest"),
                            ("Sum", "Sum"),
                            ("Diminishing_returns", "Diminishing Returns"),
                            ("Increasing_returns", "Increasing Returns"),
                        ],
                        help_text="The rule this group uses.",
                        max_length=100,
                        null=True,
                        verbose_name="rule type",
                    ),
                ),
                (
                    "rule_val",
                    models.PositiveIntegerField(
                        help_text="An optional value that the group's rule choices might carry.",
                        null=True,
                        verbose_name="rule value",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        help_text="Group creation date.", verbose_name="created at"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        help_text="Group last update date.", verbose_name="updated at"
                    ),
                ),
                (
                    "providers",
                    models.ManyToManyField(
                        help_text="group providers.",
                        related_name="groups",
                        to="nadabot.provider",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Stamp",
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
                (
                    "verified_at",
                    models.DateField(
                        help_text="The date of verification.",
                        verbose_name="verification date",
                    ),
                ),
                (
                    "provider",
                    models.ForeignKey(
                        help_text="The provider the user verified with.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stamps",
                        to="nadabot.provider",
                        verbose_name="provider",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="The user who earned the stamp.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stamps",
                        to="accounts.account",
                        verbose_name="user",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="BlackList",
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
                (
                    "reason",
                    models.TextField(
                        blank=True,
                        help_text="Reason account is blacklisted",
                        null=True,
                        verbose_name="blacklist reason",
                    ),
                ),
                (
                    "date_blacklisted",
                    models.DateTimeField(
                        help_text="Blacklist Entry Date.", verbose_name="blacklisted on"
                    ),
                ),
                (
                    "account",
                    models.ForeignKey(
                        help_text="Nadabot Registry Blacklisted from.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="registries_blacklisted_from",
                        to="accounts.account",
                    ),
                ),
                (
                    "registry",
                    models.ForeignKey(
                        help_text="blacklist entries by this registry",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="blacklists",
                        to="nadabot.nadabotregistry",
                        verbose_name="registry",
                    ),
                ),
            ],
            options={
                "unique_together": {("registry", "account")},
            },
        ),
    ]
