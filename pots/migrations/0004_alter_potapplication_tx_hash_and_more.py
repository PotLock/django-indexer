# Generated by Django 5.0.4 on 2024-06-13 15:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pots", "0003_alter_potapplication_options_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="potapplication",
            name="tx_hash",
            field=models.CharField(
                help_text="Transaction hash.",
                max_length=64,
                null=True,
                verbose_name="transaction hash",
            ),
        ),
        migrations.AlterField(
            model_name="potapplicationreview",
            name="tx_hash",
            field=models.CharField(
                help_text="Transaction hash.",
                max_length=64,
                null=True,
                verbose_name="transaction hash",
            ),
        ),
        migrations.AlterField(
            model_name="potpayout",
            name="tx_hash",
            field=models.CharField(
                help_text="Transaction hash.",
                max_length=64,
                null=True,
                verbose_name="transaction hash",
            ),
        ),
        migrations.AlterField(
            model_name="potpayoutchallengeadminresponse",
            name="tx_hash",
            field=models.CharField(
                help_text="Transaction hash.",
                max_length=64,
                null=True,
                verbose_name="transaction hash",
            ),
        ),
    ]
