from rest_framework.serializers import ModelSerializer

from tokens.models import Token


class TokenSerializer(ModelSerializer):

    class Meta:
        model = Token
        fields = "__all__"


SIMPLE_TOKEN_EXAMPLE = {"id": "near", "decimals": 24}
