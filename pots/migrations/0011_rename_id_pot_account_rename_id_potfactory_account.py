# Generated by Django 5.0.6 on 2024-07-19 22:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("pots", "0010_alter_potpayout_paid_at"),
    ]

    operations = [
        migrations.RenameField(
            model_name="pot",
            old_name="id",
            new_name="account",
        ),
        migrations.RenameField(
            model_name="potfactory",
            old_name="id",
            new_name="account",
        ),
    ]
