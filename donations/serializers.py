from rest_framework.serializers import ModelSerializer, SerializerMethodField

from .models import Donation


class DonationSerializer(ModelSerializer):
    class Meta:
        model = Donation
        fields = "__all__"  # TODO: potentially adjust this e.g. for formatting of datetimes, adding convenience fields etc
