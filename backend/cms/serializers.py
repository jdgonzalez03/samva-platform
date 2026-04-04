from rest_framework import serializers
from cms.models import LandingPage


class LandingPageSerializer(serializers.ModelSerializer):
    body = serializers.SerializerMethodField()

    class Meta:
        model = LandingPage
        fields = ["title", "body"]
    
    def get_body(self, obj):
        return obj.body.stream_block.get_api_representation(
            obj.body,
            context=self.context
        )