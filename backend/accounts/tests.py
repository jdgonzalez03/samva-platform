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


class ApiSecretRegenerateTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="juan", email="juan@example.com", password="testpass123"
        )
        cls.farmer = Farmer.objects.create(user=cls.user, first_name="Juan")
        other_user = User.objects.create_user(
            username="maria", email="maria@example.com", password="testpass123"
        )
        cls.other_farmer = Farmer.objects.create(user=other_user, first_name="María")

    def regenerate(self):
        return self.client.post(reverse("accounts:api-secret-regenerate"))

    def test_it_replaces_the_secret_and_returns_the_new_one(self):
        original_secret = self.farmer.api_secret
        self.client.force_authenticate(user=self.user)

        response = self.regenerate()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.farmer.refresh_from_db()
        self.assertNotEqual(self.farmer.api_secret, original_secret)
        self.assertTrue(self.farmer.api_secret.startswith("smv_"))
        self.assertEqual(response.data, {"api_secret": self.farmer.api_secret})

    def test_the_old_secret_stops_authenticating_sensors(self):
        original_secret = self.farmer.api_secret
        self.client.force_authenticate(user=self.user)
        self.regenerate()
        self.client.force_authenticate(user=None)

        response = self.client.post(
            reverse("sensors:ingest"), {}, format="json", headers={"X-API-Key": original_secret}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_it_leaves_other_farmers_untouched(self):
        other_secret = self.other_farmer.api_secret
        self.client.force_authenticate(user=self.user)

        self.regenerate()

        self.other_farmer.refresh_from_db()
        self.assertEqual(self.other_farmer.api_secret, other_secret)

    def test_it_requires_authentication(self):
        response = self.regenerate()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_a_user_without_a_farmer_profile_gets_not_found(self):
        self.client.force_authenticate(
            user=User.objects.create_user(
                username="admin", email="admin@example.com", password="testpass123"
            )
        )

        response = self.regenerate()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class OpenApiSchemaTestCase(APITestCase):
    def test_schema_generates_and_documents_the_api_secret(self):
        response = self.client.get(reverse("schema"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("api_secret", response.content.decode())
