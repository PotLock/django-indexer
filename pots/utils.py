import re


def match_pot_factory_version_pattern(receiver):
    pattern = r"^v\d+\.potfactory\.potlock\.near$"
    return bool(re.match(pattern, receiver))
