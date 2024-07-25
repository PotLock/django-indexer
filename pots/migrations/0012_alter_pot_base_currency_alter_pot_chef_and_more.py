# Generated by Django 5.0.6 on 2024-07-25 12:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_alter_account_near_social_profile_data"),
        ("pots", "0011_rename_id_pot_account_rename_id_potfactory_account"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pot",
            name="base_currency",
            field=models.CharField(
                blank=True,
                help_text="Base currency.",
                max_length=64,
                null=True,
                verbose_name="base currency",
            ),
        ),
        migrations.AlterField(
            model_name="pot",
            name="chef",
            field=models.ForeignKey(
                blank=True,
                help_text="Pot chef.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="chef_pots",
                to="accounts.account",
            ),
        ),
        migrations.AlterField(
            model_name="pot",
            name="cooldown_end",
            field=models.DateTimeField(
                blank=True,
                help_text="Pot cooldown end date.",
                null=True,
                verbose_name="cooldown end",
            ),
        ),
        migrations.AlterField(
            model_name="pot",
            name="cooldown_period_ms",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Pot cooldown period in ms.",
                null=True,
                verbose_name="cooldown period in ms",
            ),
        ),
        migrations.AlterField(
            model_name="pot",
            name="custom_min_threshold_score",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Custom min threshold score.",
                null=True,
                verbose_name="custom min threshold score",
            ),
        ),
        migrations.AlterField(
            model_name="pot",
            name="custom_sybil_checks",
            field=models.CharField(
                blank=True,
                help_text="Custom sybil checks.",
                null=True,
                verbose_name="custom sybil checks",
            ),
        ),
        migrations.AlterField(
            model_name="pot",
            name="protocol_config_provider",
            field=models.CharField(
                blank=True,
                help_text="Protocol config provider.",
                null=True,
                verbose_name="protocol config provider",
            ),
        ),
        migrations.AlterField(
            model_name="pot",
            name="registry_provider",
            field=models.CharField(
                blank=True,
                help_text="Registry provider.",
                null=True,
                verbose_name="registry provider",
            ),
        ),
        migrations.AlterField(
            model_name="pot",
            name="sybil_wrapper_provider",
            field=models.CharField(
                blank=True,
                help_text="Sybil wrapper provider.",
                null=True,
                verbose_name="sybil wrapper provider",
            ),
        ),
        migrations.AlterField(
            model_name="pot",
            name="total_matching_pool_usd",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Total matching pool in USD.",
                max_digits=20,
                null=True,
                verbose_name="total matching pool in USD",
            ),
        ),
        migrations.AlterField(
            model_name="pot",
            name="total_public_donations_usd",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Total public donations in USD.",
                max_digits=20,
                null=True,
                verbose_name="total public donations in USD",
            ),
        ),
        migrations.AlterField(
            model_name="potapplication",
            name="message",
            field=models.TextField(
                blank=True,
                help_text="Application message.",
                max_length=1024,
                null=True,
                verbose_name="message",
            ),
        ),
        migrations.AlterField(
            model_name="potapplication",
            name="tx_hash",
            field=models.CharField(
                blank=True,
                help_text="Transaction hash.",
                null=True,
                verbose_name="transaction hash",
            ),
        ),
        migrations.AlterField(
            model_name="potapplication",
            name="updated_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Application last update date.",
                null=True,
                verbose_name="updated at",
            ),
        ),
        migrations.AlterField(
            model_name="potapplicationreview",
            name="notes",
            field=models.TextField(
                blank=True,
                help_text="Review notes.",
                max_length=1024,
                null=True,
                verbose_name="notes",
            ),
        ),
        migrations.AlterField(
            model_name="potapplicationreview",
            name="tx_hash",
            field=models.CharField(
                blank=True,
                help_text="Transaction hash.",
                null=True,
                verbose_name="transaction hash",
            ),
        ),
        migrations.AlterField(
            model_name="potfactory",
            name="source_metadata",
            field=models.JSONField(
                blank=True,
                help_text="Pot factory source metadata.",
                null=True,
                verbose_name="source metadata",
            ),
        ),
        migrations.AlterField(
            model_name="potpayout",
            name="amount_paid_usd",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Payout amount in USD.",
                max_digits=20,
                null=True,
                verbose_name="amount paid in USD",
            ),
        ),
        migrations.AlterField(
            model_name="potpayout",
            name="paid_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text="Payout date.",
                null=True,
                verbose_name="paid at",
            ),
        ),
        migrations.AlterField(
            model_name="potpayout",
            name="tx_hash",
            field=models.CharField(
                blank=True,
                help_text="Transaction hash.",
                null=True,
                verbose_name="transaction hash",
            ),
        ),
        migrations.AlterField(
            model_name="potpayoutchallengeadminresponse",
            name="challenger",
            field=models.ForeignKey(
                blank=True,
                help_text="challenger being responded to.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payout_admin_responses",
                to="accounts.account",
            ),
        ),
        migrations.AlterField(
            model_name="potpayoutchallengeadminresponse",
            name="pot",
            field=models.ForeignKey(
                blank=True,
                help_text="Pot being challenged.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payout_responses",
                to="pots.pot",
            ),
        ),
        migrations.AlterField(
            model_name="potpayoutchallengeadminresponse",
            name="tx_hash",
            field=models.CharField(
                blank=True,
                help_text="Transaction hash.",
                null=True,
                verbose_name="transaction hash",
            ),
        ),
    ]