from datetime import datetime


def format_date(date: datetime):
    year = date.year
    month = str(date.month).zfill(2)
    day = str(date.day).zfill(2)
    return f"{day}-{month}-{year}"


def format_to_near(yocto_amount: str):
    near_amount = int(yocto_amount) / (10**24)
    return near_amount

def convert_ns_to_utc(ns_timestamp):
    # Convert nanoseconds to seconds (float)
    seconds = ns_timestamp / 1e9
    
    # Create a datetime object from the seconds (UTC)
    utc_datetime = datetime.utcfromtimestamp(seconds)
    
    # Format the datetime object as a string
    formatted_date = utc_datetime.strftime('%Y-%m-%d %H:%M:%S')
    
    return formatted_date