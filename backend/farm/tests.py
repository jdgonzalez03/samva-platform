from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from farm.models import Farm, Plot
from farmer.models import Farmer

User = get_user_model()


class FarmAPITestCase(APITestCase):
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

        cls.farm = Farm.objects.create(
            owner=cls.farmer,
            name="Finca El Tesoro",
            address="Vereda La Esperanza",
        )
        cls.empty_farm = Farm.objects.create(
            owner=cls.farmer,
            name="Finca San Vicente",
            address="Vereda El Carmen",
        )
        cls.other_farm = Farm.objects.create(
            owner=cls.other_farmer,
            name="Finca La Montaña",
            address="Vereda El Roble",
        )

        cls.plot = Plot.objects.create(farm=cls.farm, name="Lote Norte")
        Plot.objects.create(farm=cls.farm, name="Lote Sur")
        Plot.objects.create(farm=cls.other_farm, name="Lote Ajeno")

    def test_farm_list_returns_only_farms_owned_by_the_user(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("farm:farm-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [farm["name"] for farm in response.data],
            ["Finca El Tesoro", "Finca San Vicente"],
        )

    def test_farm_list_serializes_the_agreed_fields(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("farm:farm-list"))

        self.assertEqual(
            set(response.data[0].keys()),
            {"id", "name", "address", "created_at"},
        )

    def test_farm_list_requires_authentication(self):
        response = self.client.get(reverse("farm:farm-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_farm_list_is_empty_for_a_user_without_a_farmer_row(self):
        user_without_farmer = User.objects.create_user(
            username="sin-farmer",
            email="sin-farmer@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=user_without_farmer)

        response = self.client.get(reverse("farm:farm-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_plot_list_returns_only_the_plots_of_the_requested_farm(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("farm:farm-plot-list", args=[self.farm.pk]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [plot["name"] for plot in response.data],
            ["Lote Norte", "Lote Sur"],
        )
        self.assertEqual(
            set(response.data[0].keys()),
            {"id", "name", "description", "area_hectares"},
        )

    def test_plot_list_is_empty_for_an_owned_farm_without_plots(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("farm:farm-plot-list", args=[self.empty_farm.pk]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_plot_list_hides_farms_owned_by_someone_else(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("farm:farm-plot-list", args=[self.other_farm.pk]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_plot_list_returns_404_for_an_unknown_farm(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("farm:farm-plot-list", args=[999999]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_plot_list_requires_authentication(self):
        response = self.client.get(reverse("farm:farm-plot-list", args=[self.farm.pk]))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
