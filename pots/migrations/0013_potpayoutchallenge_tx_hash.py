# Generated by Django 5.0.6 on 2024-07-29 21:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pots", "0012_alter_pot_base_currency_alter_pot_chef_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="potpayoutchallenge",
            name="tx_hash",
            field=models.CharField(
                blank=True,
                help_text="Transaction hash.",
                null=True,
                verbose_name="transaction hash",
            ),
        ),
    ]
