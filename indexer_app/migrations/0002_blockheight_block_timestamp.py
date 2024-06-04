# Generated by Django 5.0.4 on 2024-05-03 10:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("indexer_app", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="blockheight",
            name="block_timestamp",
            field=models.DateTimeField(
                help_text="date equivalent of the block height.",
                null=True,
                verbose_name="block timestamp",
            ),
        ),
    ]
