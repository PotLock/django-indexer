# Add custom migration to donations app that uses run_python to update net_amount for all Donations where net_amount="0".

from django.db import migrations
from django.db.models import F


def update_donations_net_amount(apps, schema_editor):
    Donation = apps.get_model("donations", "Donation")
    for donation in Donation.objects.filter(net_amount="0"):
        total_amount = int(donation.total_amount)
        protocol_fee = int(donation.protocol_fee)
        referrer_fee = int(donation.referrer_fee or 0)

        net_amount = total_amount - protocol_fee - referrer_fee
        donation.net_amount = net_amount
        donation.save()


class Migration(migrations.Migration):

    dependencies = [
        ("donations", "0011_remove_donation_ft_alter_donation_token"),
    ]

    operations = [
        migrations.RunPython(update_donations_net_amount),
    ]
