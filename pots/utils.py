import re

BASE_PATTERN = r"v\d+\.potfactory\.potlock\.near$"


def match_pot_factory_version_pattern(receiver):
    """Matches the base pot factory version pattern without a subaccount."""
    pattern = f"^{BASE_PATTERN}"
    return bool(re.match(pattern, receiver))


def match_pot_subaccount_version_pattern(receiver):
    """Matches the pot factory version pattern with a subaccount."""
    pattern = f"^[a-zA-Z0-9_]+\.{BASE_PATTERN}"
    return bool(re.match(pattern, receiver))
