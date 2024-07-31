from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, SerializerMethodField

from .models import Account

# near social profile data serializers (for Swagger schema)


class NFTSerializer(serializers.Serializer):
    media = serializers.URLField(required=False)
    baseUri = serializers.URLField(required=False)
    tokenId = serializers.CharField(required=False)
    contractId = serializers.CharField(required=False)


class ImageSerializer(serializers.Serializer):
    url = serializers.URLField(required=False)
    ipfs_cid = serializers.CharField(required=False)
    nft = NFTSerializer(required=False)


class LinktreeSerializer(serializers.Serializer):
    github = serializers.CharField(required=False, allow_blank=True)
    twitter = serializers.CharField(required=False, allow_blank=True)
    website = serializers.CharField(required=False, allow_blank=True)
    telegram = serializers.CharField(required=False, allow_blank=True)


class NearSocialProfileDataSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    image = ImageSerializer(required=False)
    backgroundImage = ImageSerializer(required=False)
    description = serializers.CharField(required=False)
    linktree = LinktreeSerializer(required=False)
    plPublicGoodReason = serializers.CharField(required=False)
    plCategories = serializers.CharField(
        required=False, help_text="JSON-stringified array of category strings"
    )
    plGithubRepos = serializers.CharField(
        required=False, help_text="JSON-stringified array of URLs"
    )
    plSmartContracts = serializers.CharField(
        required=False,
        help_text="JSON-stringified object with chain names as keys that map to nested objects of contract addresses",
    )
    plFundingSources = serializers.CharField(
        required=False, help_text="JSON-stringified array of funding source objects"
    )
    plTeam = serializers.CharField(
        required=False,
        help_text="JSON-stringified array of team member account ID strings",
    )


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

    total_donations_in_usd = serializers.DecimalField(
        max_digits=20, decimal_places=2, coerce_to_string=False
    )
    total_donations_out_usd = serializers.DecimalField(
        max_digits=20, decimal_places=2, coerce_to_string=False
    )
    total_matching_pool_allocations_usd = serializers.DecimalField(
        max_digits=20, decimal_places=2, coerce_to_string=False
    )
    donors_count = serializers.IntegerField()
    near_social_profile_data = NearSocialProfileDataSerializer(required=False)


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

PAGINATED_ACCOUNT_EXAMPLE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [SIMPLE_ACCOUNT_EXAMPLE],
}


class PaginatedAccountsResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = AccountSerializer(many=True)
