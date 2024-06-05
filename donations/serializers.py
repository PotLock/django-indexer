from rest_framework.serializers import ModelSerializer, SerializerMethodField

from pots.serializers import EXAMPLE_POT_ID

from .models import Donation


class DonationSerializer(ModelSerializer):
    class Meta:
        model = Donation
        fields = "__all__"  # TODO: potentially adjust this e.g. for formatting of datetimes, adding convenience fields etc


SIMPLE_DONATION_EXAMPLE = {
    "id": 100,
    "on_chain_id": 156,
    "total_amount": "1000000000000000000000000",
    "total_amount_usd": "1.17",
    "net_amount": "1000000000000000000000000",
    "net_amount_usd": "1.02",
    "matching_pool": True,
    "message": None,
    "donated_at": "2024-06-05T18:08:40.751Z",
    "protocol_fee": "10000000000000000000000",
    "protocol_fee_usd": "0.27",
    "referrer_fee": "10000000000000000000000",
    "referrer_fee_usd": "0.27",
    "chef_fee": "10000000000000000000000",
    "chef_fee_usd": "0.27",
    "tx_hash": "EVMQsXorrrxPLHfK9UnbzFUy1SVYWvc8hwSGQZs4RbTk",
    "donor": "donor.near",
    "ft": "near",
    "pot": EXAMPLE_POT_ID,
    "recipient": "someproject.near",
    "referrer": "somereferrer.near",
    "chef": "chef.near",
}
