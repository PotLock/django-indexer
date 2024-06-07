import requests
from asgiref.sync import sync_to_async
from django import db
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from base.logging import logger


class Account(models.Model):
    id = models.CharField(
        _("address"),
        primary_key=True,
        max_length=64,
        db_index=True,
        validators=[],
        help_text=_("On-chain account address."),
    )
    total_donations_in_usd = models.DecimalField(
        _("total donations received in USD"),
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text=_("Total donations received in USD."),
    )
    total_donations_out_usd = models.DecimalField(
        _("total donations sent in USD"),
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text=_("Total donated in USD."),
        db_index=True,
    )
    total_matching_pool_allocations_usd = models.DecimalField(
        _("total matching pool allocations in USD"),
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text=_("Total matching pool allocations in USD."),
    )
    donors_count = models.PositiveIntegerField(
        _("donors count"),
        default=0,
        help_text=_("Number of donors."),
    )
    near_social_profile_data = models.JSONField(
        _("NEAR social profile data"),
        null=True,
        help_text=_("NEAR social data contained under 'profile' key."),
    )

    async def fetch_near_social_profile_data_async(self):
        fetch_profile_data = sync_to_async(self.fetch_near_social_profile_data)
        await fetch_profile_data()

    def fetch_near_social_profile_data(self, should_save=True):
        # Fetch social profile data from NEAR blockchain
        try:
            url = f"{settings.FASTNEAR_RPC_URL}/account/{settings.NEAR_SOCIAL_CONTRACT_ADDRESS}/view/get"
            keys_value = f'["{self.id}/profile/**"]'
            params = {"keys.json": keys_value}
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if self.id in data and "profile" in data[self.id]:
                    profile_data = data[self.id][
                        "profile"
                    ]  # TODO: validate/sanitize profile data?
                    # fetch NFT URLs if applicable
                    for image_type in ["image", "backgroundImage"]:
                        if (
                            image_type in profile_data
                            and "nft" in profile_data[image_type]
                            and "contractId" in profile_data[image_type]["nft"]
                            and "tokenId" in profile_data[image_type]["nft"]
                        ):
                            contract_id = profile_data[image_type]["nft"]["contractId"]
                            token_id = profile_data[image_type]["nft"]["tokenId"]
                            # get base_uri
                            url = f"{settings.FASTNEAR_RPC_URL}/account/{contract_id}/view/nft_metadata"
                            response = requests.get(url)
                            if response.status_code == 200:
                                metadata = response.json()
                                if "base_uri" in metadata:
                                    base_uri = metadata["base_uri"]
                                    # store baseUri in profile_data
                                    profile_data[image_type]["nft"][
                                        "baseUri"
                                    ] = base_uri
                            else:
                                logger.error(
                                    f"Request for NFT metadata failed ({response.status_code}) with message: {response.text}"
                                )
                            # get token metadata
                            url = f"{settings.FASTNEAR_RPC_URL}/account/{contract_id}/view/nft_token"
                            json_data = {"token_id": token_id}
                            response = requests.post(
                                url, json=json_data
                            )  # using a POST request here so that token_id is not coerced into an integer on fastnear's side, causing a contract view error
                            if response.status_code == 200:
                                token_metadata = response.json()
                                if (
                                    "metadata" in token_metadata
                                    and "media" in token_metadata["metadata"]
                                ):
                                    # store media in profile_data
                                    profile_data[image_type]["nft"]["media"] = (
                                        token_metadata["metadata"]["media"]
                                    )
                            else:
                                logger.error(
                                    f"Request for NFT metadata failed ({response.status_code}) with message: {response.text}"
                                )
                    self.near_social_profile_data = profile_data
                    if should_save:
                        self.save()
            else:
                logger.error(
                    f"Request for NEAR Social profile data failed ({response.status_code}) with message: {response.text}"
                )
        except Exception as e:
            logger.error(f"Error fetching NEAR social profile data: {e}")

    def save(self, *args, **kwargs):
        if self._state.adding:  # If the account is being created (not updated)
            self.fetch_near_social_profile_data(
                False  # don't save yet as we want to avoid infinite loop
            )
        super().save(*args, **kwargs)
