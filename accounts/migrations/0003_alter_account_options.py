# Generated by Django 5.0.6 on 2024-07-12 12:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_account_near_social_profile_data"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="account",
            options={"ordering": ["id"]},
        ),
    ]