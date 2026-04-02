from django.contrib.auth import get_user_model
from farmer.serializers import FarmerSerializer


# Create your models here.
User = get_user_model()


class MeSerializer(models.Model):
    farmer = FarmerSerializer(read_only=True)
    class Meta:
        model = User
        fields = ['id', 'email', 'farmer']