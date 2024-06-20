# Generated by Django 5.0.4 on 2024-06-20 13:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("donations", "0008_alter_donation_tx_hash"),
        ("tokens", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="donation",
            name="token",
            field=models.ForeignKey(
                help_text="Donation token.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="donations",
                to="tokens.token",
            ),
        ),
    ]