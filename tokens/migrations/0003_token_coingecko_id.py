# Generated by Django 5.0.6 on 2024-07-17 17:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tokens", "0002_token_icon_token_name_token_symbol"),
    ]

    operations = [
        migrations.AddField(
            model_name="token",
            name="coingecko_id",
            field=models.CharField(
                default="near",
                help_text="Token id on coingecko.",
                max_length=255,
                verbose_name="coingecko_id",
            ),
            preserve_default=False,
        ),
    ]
