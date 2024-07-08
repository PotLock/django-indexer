# Generated by Django 5.0.4 on 2024-07-08 13:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pots", "0009_remove_potpayout_ft_alter_potpayout_token"),
    ]

    operations = [
        migrations.AlterField(
            model_name="potpayout",
            name="paid_at",
            field=models.DateTimeField(
                db_index=True,
                help_text="Payout date.",
                null=True,
                verbose_name="paid at",
            ),
        ),
    ]