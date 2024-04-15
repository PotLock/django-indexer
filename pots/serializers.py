from rest_framework.serializers import ModelSerializer, SerializerMethodField

from .models import Pot, PotApplication, PotPayout


class PotSerializer(ModelSerializer):
    class Meta:
        model = Pot
        fields = "__all__"  # TODO: potentially adjust this e.g. for formatting of datetimes, adding convenience fields etc


class PotApplicationSerializer(ModelSerializer):
    class Meta:
        model = PotApplication
        fields = "__all__"  # TODO: potentially adjust this e.g. for formatting of datetimes, adding convenience fields etc
        # TODO: add reviews


class PotPayoutSerializer(ModelSerializer):
    class Meta:
        model = PotPayout
        fields = "__all__"  # TODO: potentially adjust this e.g. for formatting of datetimes, adding convenience fields etc
