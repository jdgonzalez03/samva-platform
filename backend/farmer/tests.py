from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from farmer.models import Farmer

User = get_user_model()

API_SECRET_PREFIX = "smv_"
# token_urlsafe(32) produce 43 caracteres; con el prefijo "smv_" son 47.
API_SECRET_LENGTH = 47


class FarmerApiSecretTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="juan",
            email="juan@example.com",
            password="testpass123",
        )
        cls.farmer = Farmer.objects.create(user=cls.user, first_name="Juan")

        cls.other_user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="testpass123",
        )
        cls.other_farmer = Farmer.objects.create(user=cls.other_user, first_name="María")

    def test_creating_farmer_generates_api_secret(self):
        self.assertTrue(self.farmer.api_secret.startswith(API_SECRET_PREFIX))
        self.assertEqual(len(self.farmer.api_secret), API_SECRET_LENGTH)

    def test_each_farmer_gets_a_distinct_api_secret(self):
        self.assertNotEqual(self.farmer.api_secret, self.other_farmer.api_secret)

    def test_saving_other_fields_does_not_rotate_api_secret(self):
        original_secret = self.farmer.api_secret
        self.farmer.first_name = "Juan Carlos"
        self.farmer.save()
        self.farmer.refresh_from_db()
        self.assertEqual(self.farmer.api_secret, original_secret)

    def test_regenerate_api_secret_rotates_to_a_new_valid_token(self):
        original_secret = self.farmer.api_secret
        self.farmer.regenerate_api_secret()
        self.farmer.refresh_from_db()
        self.assertNotEqual(self.farmer.api_secret, original_secret)
        self.assertTrue(self.farmer.api_secret.startswith(API_SECRET_PREFIX))
        self.assertEqual(len(self.farmer.api_secret), API_SECRET_LENGTH)


class FarmerAdminRegenerateActionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
        )
        cls.farmer_user = User.objects.create_user(
            username="juan",
            email="juan@example.com",
            password="testpass123",
        )
        cls.farmer = Farmer.objects.create(user=cls.farmer_user, first_name="Juan")

        cls.untouched_user = User.objects.create_user(
            username="maria",
            email="maria@example.com",
            password="testpass123",
        )
        cls.untouched_farmer = Farmer.objects.create(
            user=cls.untouched_user, first_name="María"
        )

    def test_admin_action_rotates_only_selected_farmers(self):
        selected_original = self.farmer.api_secret
        untouched_original = self.untouched_farmer.api_secret

        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse("admin:farmer_farmer_changelist"),
            {
                "action": "regenerate_api_secret",
                "_selected_action": [str(self.farmer.pk)],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.farmer.refresh_from_db()
        self.untouched_farmer.refresh_from_db()
        self.assertNotEqual(self.farmer.api_secret, selected_original)
        self.assertTrue(self.farmer.api_secret.startswith(API_SECRET_PREFIX))
        self.assertEqual(self.untouched_farmer.api_secret, untouched_original)
