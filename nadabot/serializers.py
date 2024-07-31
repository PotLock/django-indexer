from rest_framework.serializers import ModelSerializer, SerializerMethodField

from .models import NadabotRegistry, Provider, Stamp


class NadabotSerializer(ModelSerializer):
    class Meta:
        model = NadabotRegistry
        fields = "__all__"  # TODO: potentially adjust this e.g. for formatting of datetimes, adding convenience fields etc


class ProviderSerializer(ModelSerializer):
    class Meta:
        model = Provider
        fields = "__all__"  # TODO: potentially adjust this e.g. for formatting of datetimes, adding convenience fields etc
