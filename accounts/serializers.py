from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, SerializerMethodField

from .models import Account


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "id",
            "total_donations_in_usd",
            "total_donations_out_usd",
            "total_matching_pool_allocations_usd",
            "donors_count",
            "near_social_profile_data",
        ]


SIMPLE_ACCOUNT_EXAMPLE = {
    "id": "user.near",
    "total_donations_in_usd": "740.00",
    "total_donations_out_usd": "1234.56",
    "total_matching_pool_allocations_usd": "800.01",
    "donors_count": 321,
    "near_social_profile_data": {
        "name": "Illia",
        "image": {
            "nft": {
                "media": "https://ipfs.nftstorage.link/ipfs/bafybeie6mpnk6iya3wvwtxtogzmzpprw5734dydoeujo5esqqxmmirug6y",
                "baseUri": "https://arweave.net/q8IenkSo5aogF-bIphzedrom24OFYGECZYUs9gEfM0A",
                "tokenId": "8120",
                "contractId": "citizen.bodega-lab.near",
            }
        },
        "linktree": {
            "github": "ilblackdragon",
            "twitter": "ilblackdragon",
            "website": "near.org",
            "telegram": "",
        },
        "description": "Bringing 1B users to web3",
        "horizon_tnc": "true",
        "backgroundImage": {
            "ipfs_cid": "bafkreiemktmsdhpdoomwlvfi2ztm7c5sdqdmb2z5mg4bjssoqkz7wunaoi"
        },
    },
}
