from rest_framework.serializers import ModelSerializer, SerializerMethodField

from .models import List, ListRegistration


class ListSerializer(ModelSerializer):
    class Meta:
        model = List
        fields = "__all__"  # TODO: potentially adjust this e.g. for formatting of datetimes, adding convenience fields etc


class ListRegistrationSerializer(ModelSerializer):
    class Meta:
        model = ListRegistration
        fields = "__all__"  # TODO: potentially adjust this e.g. for formatting of datetimes, adding convenience fields etc
