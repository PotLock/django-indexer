# Generated by Django 5.0.4 on 2024-04-17 18:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Activity",
            fields=[
                (
                    "id",
                    models.AutoField(
                        help_text="Activity id.",
                        primary_key=True,
                        serialize=False,
                        verbose_name="activity id",
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(
                        db_index=True,
                        help_text="Activity timestamp.",
                        verbose_name="timestamp",
                    ),
                ),
                (
                    "action_result",
                    models.JSONField(
                        help_text="Activity action result.",
                        null=True,
                        verbose_name="action result",
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
                    "type",
                    models.CharField(
                        choices=[
                            ("Donate_Direct", "Donate Direct"),
                            ("Donate_Pot_Public", "Donate Pot Public"),
                            ("Donate_Pot_Matching_Pool", "Donate Pot Matching Pool"),
                            ("Register", "Register"),
                            ("Register_Batch", "Register Batch"),
                            ("Deploy_Pot", "Deploy Pot"),
                            ("Process_Payouts", "Process Payouts"),
                            ("Challenge_Payout", "Challenge Payout"),
                            ("Submit_Application", "Submit Application"),
                            ("Update_Pot_Config", "Update Pot Config"),
                            ("Add_List_Admin", "Add List Admin"),
                            ("Remove_List_Admin", "Remove List Admin"),
                        ],
                        help_text="Activity type.",
                        max_length=32,
                        verbose_name="type",
                    ),
                ),
                (
                    "receiver",
                    models.ForeignKey(
                        help_text="Receiver.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="received_activities",
                        to="accounts.account",
                    ),
                ),
                (
                    "signer",
                    models.ForeignKey(
                        help_text="Signer.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="signed_activities",
                        to="accounts.account",
                    ),
                ),
            ],
        ),
    ]
