from rest_framework import serializers


class TwoDecimalPlacesField(serializers.DecimalField):
    def to_representation(self, value):
        if value is None:
            return value
        return format(value, ".2f")  # 2 decimal places
