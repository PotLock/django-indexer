# Generated by Django 5.0.4 on 2024-07-18 13:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tokens", "0003_token_coingecko_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="token",
            name="coingecko_id",
            field=models.CharField(
                help_text="Token id on coingecko.",
                max_length=255,
                null=True,
                verbose_name="coingecko_id",
            ),
        ),
    ]
