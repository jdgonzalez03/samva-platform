from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from farmer.models import Farmer

User = get_user_model()


class MeApiSecretTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="juan",
            email="juan@example.com",
            password="testpass123",
        )
        cls.farmer = Farmer.objects.create(user=cls.user, first_name="Juan")

    def test_me_exposes_the_farmer_api_secret(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("accounts:me"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["farmer"]["api_secret"], self.farmer.api_secret)
        self.assertTrue(response.data["farmer"]["api_secret"].startswith("smv_"))

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("accounts:me"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_cannot_overwrite_the_api_secret(self):
        original_secret = self.farmer.api_secret
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse("accounts:me"),
            {"api_secret": "hacked", "first_name": "Juan Carlos"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.farmer.refresh_from_db()
        self.assertEqual(self.farmer.api_secret, original_secret)
        self.assertEqual(response.data["farmer"]["api_secret"], original_secret)
        self.assertEqual(response.data["farmer"]["first_name"], "Juan Carlos")
