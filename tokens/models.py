from datetime import timedelta
from decimal import Decimal
from os import name

import requests
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import Account
from base.logging import logger
from base.utils import format_date


class Token(models.Model):
    id = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        primary_key=True,
        help_text=_("Token ID (address)."),
    )
    name = models.CharField(
        _("name"),
        max_length=255,
        null=True,
        help_text=_("Token name."),
    )
    symbol = models.CharField(
        _("symbol"),
        max_length=255,
        null=True,
        help_text=_("Token symbol."),
    )
    icon = models.TextField(
        _("icon"),
        null=True,
        help_text=_("Token icon (base64 data URL)."),
    )
    decimals = models.PositiveIntegerField(
        _("decimals"),
        null=False,
        help_text=_("Token decimals."),
    )
    coingecko_id = models.CharField(
        _("coingecko_id"),
        max_length=255,
        help_text=_("Token id on coingecko."),
    )

    def get_most_recent_price(self):
        return self.historical_prices.order_by("-timestamp").first()

    def format_price(self, amount_str: str):
        # Convert the string amount to a Decimal, then adjust by the token's decimal places
        formatted_amount = Decimal(amount_str) / (Decimal("10") ** self.decimals)
        return formatted_amount

    def fetch_usd_prices_common(self, timestamp):

        time_window = timedelta(hours=settings.HISTORICAL_PRICE_QUERY_HOURS or 24)
        token_prices = TokenHistoricalPrice.objects.filter(
            token=self,
            timestamp__gte=timestamp - time_window,
            timestamp__lte=timestamp + time_window,
        )
        existing_token_price = token_prices.first()
        if existing_token_price:
            return existing_token_price.price_usd

        price_data = {}
        if self.coingecko_id:
            try:
                logger.info(
                    "No existing price within acceptable time period; fetching historical pricefrom gecko..."
                )
                endpoint = f"{settings.COINGECKO_URL}/coins/{self.coingecko_id}/history?date={format_date(timestamp)}&localization=false"
                if settings.COINGECKO_API_KEY:
                    endpoint += f"&x_cg_pro_api_key={settings.COINGECKO_API_KEY}"
                logger.info(f"coingecko endpoint: {endpoint}")
                response = requests.get(endpoint)
                logger.info(f"coingecko response: {response}")
                if response.status_code == 429:
                    logger.warning("Coingecko rate limit exceeded")
                price_data = response.json()
            except Exception as e:
                logger.warning(f"Failed to fetch coingecko price data: {e}")
                return None
            price_usd = (
                price_data.get("market_data", {}).get("current_price", {}).get("usd")
            )
            if price_usd:
                TokenHistoricalPrice.objects.create(
                    token=self,
                    timestamp=timestamp,
                    price_usd=price_usd,
                )
                return Decimal(price_usd)
        return None

    def save(self, *args, **kwargs):
        try:
            if self._state.adding:
                endpoint = f"{settings.COINGECKO_URL}/coins/list?include_platform=true"
                if settings.COINGECKO_API_KEY:
                    endpoint += f"&x_cg_pro_api_key={settings.COINGECKO_API_KEY}"
                response = requests.get(endpoint)
                logger.info(f"coingecko response: {response}")
                if response.status_code == 429:
                    logger.warning("Coingecko rate limit exceeded")
                price_data = response.json()
                coin_data = list(
                    filter(
                        lambda x: x["symbol"] == kwargs["symbol"]
                        and x["platforms"].get("near-protocol"),
                        price_data,
                    )
                )
                if coin_data:
                    self.coingecko_id = coin_data[0]["id"]
        except Exception as e:
            logger.error(f"Failed to fetch token id from coingecko: {e}")
        super().save(*args, **kwargs)


class TokenHistoricalPrice(models.Model):
    token = models.ForeignKey(
        Token,
        on_delete=models.CASCADE,
        related_name="historical_prices",
        null=False,
        help_text=_("Token."),
    )
    timestamp = models.DateTimeField(
        _("timestamp"),
        null=False,
        help_text=_("Price timestamp."),
        db_index=True,
        default=timezone.now,
    )
    price_usd = models.DecimalField(
        _("price USD"),
        max_digits=20,
        decimal_places=2,
        null=False,
        help_text=_("Price in USD."),
    )
