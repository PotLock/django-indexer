# Generated by Django 5.0.6 on 2024-07-25 17:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("indexer_app", "0002_blockheight_block_timestamp"),
    ]

    operations = [
        migrations.AlterField(
            model_name="blockheight",
            name="block_timestamp",
            field=models.DateTimeField(
                blank=True,
                help_text="date equivalent of the block height.",
                null=True,
                verbose_name="block timestamp",
            ),
        ),
    ]
