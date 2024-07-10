import re

from django.conf import settings

BASE_PATTERN = (
    r"nadabot\.testnet"
    if settings.ENVIRONMENT == "testnet"
    else r"v\d+\.[a-zA-Z]+\.nadabot\.near"
)


def match_nadabot_registry_pattern(receiver):
    """Matches nadabot subaccounts for registry."""
    pattern = f"^{BASE_PATTERN}$"
    return bool(re.match(pattern, receiver))
