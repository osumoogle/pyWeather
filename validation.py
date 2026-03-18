import re


class ValidationError(Exception):
    pass


def validate_zipcode(zipcode: str) -> str:
    zipcode = zipcode.strip()
    if not zipcode:
        raise ValidationError("Please enter a zip code.")
    if not re.match(r'^\d{5}$', zipcode):
        raise ValidationError("Please enter a valid 5-digit US zip code.")
    return zipcode
