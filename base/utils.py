from datetime import datetime


def format_date(date: datetime):
    year = date.year
    month = str(date.month).zfill(2)
    day = str(date.day).zfill(2)
    return f"{day}-{month}-{year}"


def format_to_near(yocto_amount: str):
    near_amount = int(yocto_amount) / (10**24)
    return near_amount
