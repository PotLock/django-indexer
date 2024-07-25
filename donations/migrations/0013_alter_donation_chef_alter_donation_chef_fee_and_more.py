# Generated by Django 5.0.6 on 2024-07-25 12:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_alter_account_near_social_profile_data"),
        ("donations", "0012_update_donations_net_amount"),
        ("pots", "0012_alter_pot_base_currency_alter_pot_chef_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="donation",
            name="chef",
            field=models.ForeignKey(
                blank=True,
                help_text="Donation chef.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="chef_donations",
                to="accounts.account",
            ),
        ),
        migrations.AlterField(
            model_name="donation",
            name="chef_fee",
            field=models.CharField(
                blank=True,
                help_text="Chef fee.",
                max_length=64,
                null=True,
                verbose_name="chef fee",
            ),
        ),
        migrations.AlterField(
            model_name="donation",
            name="chef_fee_usd",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Chef fee in USD.",
                max_digits=20,
                null=True,
                verbose_name="chef fee in USD",
            ),
        ),
        migrations.AlterField(
            model_name="donation",
            name="message",
            field=models.TextField(
                blank=True,
                help_text="Donation message.",
                max_length=1024,
                null=True,
                verbose_name="message",
            ),
        ),
        migrations.AlterField(
            model_name="donation",
            name="net_amount_usd",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Net amount in USD.",
                max_digits=20,
                null=True,
                verbose_name="net amount in USD",
            ),
        ),
        migrations.AlterField(
            model_name="donation",
            name="pot",
            field=models.ForeignKey(
                blank=True,
                help_text="Donation pot.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="donations",
                to="pots.pot",
            ),
        ),
        migrations.AlterField(
            model_name="donation",
            name="protocol_fee_usd",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Protocol fee in USD.",
                max_digits=20,
                null=True,
                verbose_name="protocol fee in USD",
            ),
        ),
        migrations.AlterField(
            model_name="donation",
            name="recipient",
            field=models.ForeignKey(
                blank=True,
                help_text="Donation recipient.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="received_donations",
                to="accounts.account",
            ),
        ),
        migrations.AlterField(
            model_name="donation",
            name="referrer",
            field=models.ForeignKey(
                blank=True,
                help_text="Donation referrer.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="referral_donations",
                to="accounts.account",
            ),
        ),
        migrations.AlterField(
            model_name="donation",
            name="referrer_fee",
            field=models.CharField(
                blank=True,
                help_text="Referrer fee.",
                max_length=64,
                null=True,
                verbose_name="referrer fee",
            ),
        ),
        migrations.AlterField(
            model_name="donation",
            name="referrer_fee_usd",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Referrer fee in USD.",
                max_digits=20,
                null=True,
                verbose_name="referrer fee in USD",
            ),
        ),
        migrations.AlterField(
            model_name="donation",
            name="total_amount_usd",
            field=models.DecimalField(
                blank=True,
                db_index=True,
                decimal_places=2,
                help_text="Total amount in USD.",
                max_digits=20,
                null=True,
                verbose_name="total amount in USD",
            ),
        ),
        migrations.AlterField(
            model_name="donation",
            name="tx_hash",
            field=models.CharField(
                blank=True,
                help_text="Transaction hash.",
                max_length=64,
                null=True,
                verbose_name="transaction hash",
            ),
        ),
    ]
