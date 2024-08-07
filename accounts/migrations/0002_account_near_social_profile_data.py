# Generated by Django 5.0.4 on 2024-06-05 14:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="near_social_profile_data",
            field=models.JSONField(
                help_text="NEAR social data contained under 'profile' key.",
                null=True,
                verbose_name="NEAR social profile data",
            ),
        ),
    ]
