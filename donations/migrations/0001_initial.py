# Generated by Django 5.0.4 on 2024-04-12 14:47

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        ("pots", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Donation",
            fields=[
                (
                    "id",
                    models.AutoField(
                        help_text="Donation id.",
                        primary_key=True,
                        serialize=False,
                        verbose_name="donation id",
                    ),
                ),
                (
                    "total_amount",
                    models.CharField(
                        help_text="Total amount.",
                        max_length=64,
                        verbose_name="total amount",
                    ),
                ),
                (
                    "total_amount_usd",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Total amount in USD.",
                        max_digits=20,
                        null=True,
                        verbose_name="total amount in USD",
                    ),
                ),
                (
                    "net_amount",
                    models.CharField(
                        help_text="Net amount.",
                        max_length=64,
                        verbose_name="net amount",
                    ),
                ),
                (
                    "net_amount_usd",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Net amount in USD.",
                        max_digits=20,
                        null=True,
                        verbose_name="net amount in USD",
                    ),
                ),
                (
                    "matching_pool",
                    models.BooleanField(
                        db_index=True,
                        help_text="Matching pool.",
                        verbose_name="matching pool",
                    ),
                ),
                (
                    "message",
                    models.TextField(
                        help_text="Donation message.",
                        max_length=1024,
                        null=True,
                        verbose_name="message",
                    ),
                ),
                (
                    "donated_at",
                    models.DateTimeField(
                        db_index=True,
                        help_text="Donation date.",
                        verbose_name="donated at",
                    ),
                ),
                (
                    "protocol_fee",
                    models.CharField(
                        help_text="Protocol fee.",
                        max_length=64,
                        verbose_name="protocol fee",
                    ),
                ),
                (
                    "protocol_fee_usd",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Protocol fee in USD.",
                        max_digits=20,
                        null=True,
                        verbose_name="protocol fee in USD",
                    ),
                ),
                (
                    "referrer_fee",
                    models.CharField(
                        help_text="Referrer fee.",
                        max_length=64,
                        null=True,
                        verbose_name="referrer fee",
                    ),
                ),
                (
                    "referrer_fee_usd",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Referrer fee in USD.",
                        max_digits=20,
                        null=True,
                        verbose_name="referrer fee in USD",
                    ),
                ),
                (
                    "chef_fee",
                    models.CharField(
                        help_text="Chef fee.", max_length=64, verbose_name="chef fee"
                    ),
                ),
                (
                    "chef_fee_usd",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Chef fee in USD.",
                        max_digits=20,
                        null=True,
                        verbose_name="chef fee in USD",
                    ),
                ),
                (
                    "tx_hash",
                    models.CharField(
                        help_text="Transaction hash.",
                        max_length=64,
                        verbose_name="transaction hash",
                    ),
                ),
                (
                    "chef",
                    models.ForeignKey(
                        help_text="Donation chef.",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chef_donations",
                        to="accounts.account",
                    ),
                ),
                (
                    "donor",
                    models.ForeignKey(
                        help_text="Donor.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="donations",
                        to="accounts.account",
                    ),
                ),
                (
                    "ft",
                    models.ForeignKey(
                        help_text="Donation FT.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ft_donations",
                        to="accounts.account",
                    ),
                ),
                (
                    "pot",
                    models.ForeignKey(
                        help_text="Donation pot.",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="donations",
                        to="pots.pot",
                    ),
                ),
                (
                    "recipient",
                    models.ForeignKey(
                        help_text="Donation recipient.",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="received_donations",
                        to="accounts.account",
                    ),
                ),
                (
                    "referrer",
                    models.ForeignKey(
                        help_text="Donation referrer.",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referral_donations",
                        to="accounts.account",
                    ),
                ),
            ],
        ),
    ]
