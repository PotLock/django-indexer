from rest_framework.serializers import ModelSerializer, SerializerMethodField

from .models import Pot


class PotSerializer(ModelSerializer):
    class Meta:
        model = Pot
        fields = "__all__"  # TODO: potentially adjust this e.g. for formatting of datetimes, adding convenience fields etc
