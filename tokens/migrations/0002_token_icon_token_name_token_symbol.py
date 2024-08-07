# Generated by Django 5.0.4 on 2024-06-20 17:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tokens", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="token",
            name="icon",
            field=models.TextField(
                help_text="Token icon (base64 data URL).",
                null=True,
                verbose_name="icon",
            ),
        ),
        migrations.AddField(
            model_name="token",
            name="name",
            field=models.CharField(
                help_text="Token name.", max_length=255, null=True, verbose_name="name"
            ),
        ),
        migrations.AddField(
            model_name="token",
            name="symbol",
            field=models.CharField(
                help_text="Token symbol.",
                max_length=255,
                null=True,
                verbose_name="symbol",
            ),
        ),
    ]
