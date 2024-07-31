import re

from django.conf import settings

BASE_PATTERN = (
    r"potlock\.testnet"
    if settings.ENVIRONMENT == "testnet"
    else r"v\d+\.potfactory\.potlock\.near"
)


def match_pot_factory_pattern(receiver):
    """Matches the base pot factory version pattern without a subaccount. NB: does not currently handle testnet factory."""
    pattern = f"^{BASE_PATTERN}$"
    return bool(re.match(pattern, receiver))


def match_pot_subaccount_pattern(receiver):
    """Matches the pot factory version pattern with a subaccount. NB: does not currently handle testnet factory."""
    pattern = f"^[a-zA-Z0-9_-]+\.{BASE_PATTERN}$"
    return bool(re.match(pattern, receiver))
