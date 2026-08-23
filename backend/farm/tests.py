from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.contrib.gis import forms as gis_forms
from django.contrib.gis.geos import Point, Polygon
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from leaflet.forms.widgets import LeafletWidget
from rest_framework import status
from rest_framework.test import APITestCase

from farm.forms import FarmAdminForm
from farm.models import Farm, Plot
from farm.wagtail_hooks import WagtailFarmAdmin
from farmer.models import Farmer
from sensors.models import (
    EnvironmentalVariable,
    FieldSensor,
    SemanticKey,
    WeatherMeasurement,
    WeatherSnapshot,
    WeatherStation,
    WeatherStationVariableConfiguration,
)

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
            {"id", "name", "address", "location", "boundary", "created_at"},
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
            {
                "id",
                "name",
                "description",
                "geometry",
                "centroid",
                "label_point",
                "area_hectares",
                "sensor_count",
            },
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
        self.assertEqual(response.json(), {"detail": "Not found."})
        self.assertNotIn("Finca La Montaña", response.content.decode())

    def test_plot_list_returns_404_for_an_unknown_farm(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("farm:farm-plot-list", args=[999999]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_plot_list_requires_authentication(self):
        response = self.client.get(reverse("farm:farm-plot-list", args=[self.farm.pk]))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


def a_polygon(west=-74.105, south=4.595, east=-74.103, north=4.597):
    """A closed Colombian ring: negative longitude first, positive latitude second."""
    return Polygon(
        (
            (west, south),
            (east, south),
            (east, north),
            (west, north),
            (west, south),
        ),
        srid=4326,
    )


def an_l_shaped_polygon(west=-74.105, south=4.595, step=0.001):
    """A concave (L-shaped) ring whose centroid and bounding-box centre both fall in the notch."""
    corners = ((0, 0), (3, 0), (3, 1), (1, 1), (1, 3), (0, 3), (0, 0))
    return Polygon(
        tuple((west + x * step, south + y * step) for x, y in corners),
        srid=4326,
    )


class GeoAPITestCaseMixin:
    @classmethod
    def create_farmer(cls, username):
        user = get_user_model().objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpass123",
        )
        return user, Farmer.objects.create(user=user, first_name=username.title())


class FarmListSerializationTests(GeoAPITestCaseMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user, cls.farmer = cls.create_farmer("juan")
        cls.mapped_farm = Farm.objects.create(
            owner=cls.farmer,
            name="Finca El Tesoro",
            address="Vereda El Tesoro",
            location=a_polygon().centroid,
            boundary=a_polygon(),
        )
        cls.unmapped_farm = Farm.objects.create(
            owner=cls.farmer,
            name="Finca San Vicente",
            address="Vereda El Carmen",
        )

    def test_farm_list_serializes_geometry_as_geojson(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("farm:farm-list"))
        mapped, unmapped = response.json()

        self.assertEqual(mapped["boundary"]["type"], "Polygon")
        self.assertEqual(set(mapped["boundary"].keys()), {"type", "coordinates"})
        self.assertEqual(
            mapped["boundary"]["coordinates"][0][0],
            mapped["boundary"]["coordinates"][0][-1],
        )
        self.assertEqual(mapped["location"]["type"], "Point")
        self.assertEqual(set(mapped["location"].keys()), {"type", "coordinates"})
        self.assertIsNone(unmapped["boundary"])
        self.assertIsNone(unmapped["location"])

    def test_farm_list_keeps_the_existing_fields_untouched(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("farm:farm-list"))
        payload = response.json()

        self.assertIsInstance(payload, list)
        self.assertEqual(payload[0]["id"], self.mapped_farm.pk)
        self.assertEqual(payload[0]["name"], "Finca El Tesoro")
        self.assertEqual(payload[0]["address"], "Vereda El Tesoro")
        self.assertTrue(payload[0]["created_at"].endswith("Z"))


class PlotListSerializationTests(GeoAPITestCaseMixin, APITestCase):
    """AC31 — geometry, centroid, area and sensor count on every plot row."""

    @classmethod
    def setUpTestData(cls):
        cls.user, cls.farmer = cls.create_farmer("juan")
        cls.farm = Farm.objects.create(
            owner=cls.farmer, name="Finca El Tesoro", address="Vereda El Tesoro"
        )
        cls.mapped_plot = Plot.objects.create(
            farm=cls.farm,
            name="Lote Norte",
            description="Arroz de riego",
            geometry=a_polygon(),
        )
        cls.unmapped_plot = Plot.objects.create(farm=cls.farm, name="Lote Sin Mapear")
        FieldSensor.objects.create(plot=cls.mapped_plot, name="Sensor 1", is_active=True)

    def plots(self):
        self.client.force_authenticate(user=self.user)
        return self.client.get(reverse("farm:farm-plot-list", args=[self.farm.pk])).json()

    def test_a_mapped_plot_serializes_geometry_centroid_area_and_count(self):
        mapped = self.plots()[0]

        self.assertEqual(mapped["geometry"]["type"], "Polygon")
        self.assertEqual(set(mapped["geometry"].keys()), {"type", "coordinates"})
        self.assertEqual(
            mapped["geometry"]["coordinates"][0][0],
            mapped["geometry"]["coordinates"][0][-1],
        )
        self.assertEqual(mapped["centroid"]["type"], "Point")
        self.assertIsInstance(mapped["area_hectares"], str)
        self.assertEqual(mapped["area_hectares"], str(self.mapped_plot.area_hectares))
        self.assertIsInstance(mapped["sensor_count"], int)
        self.assertEqual(mapped["sensor_count"], 1)

    def test_coordinates_are_longitude_first(self):
        longitude, latitude = self.plots()[0]["geometry"]["coordinates"][0][0]

        self.assertLess(longitude, 0)
        self.assertGreater(latitude, 0)

    def test_an_unmapped_plot_serializes_nulls_and_a_zero_count(self):
        unmapped = self.plots()[1]

        self.assertIsNone(unmapped["geometry"])
        self.assertIsNone(unmapped["centroid"])
        self.assertIsNone(unmapped["area_hectares"])
        self.assertEqual(unmapped["sensor_count"], 0)

    def test_an_unset_description_is_an_empty_string_not_null(self):
        self.assertEqual(self.plots()[1]["description"], "")


class PlotSensorCountTests(GeoAPITestCaseMixin, APITestCase):
    """AC32 — active sensors only, and a constant number of queries."""

    @classmethod
    def setUpTestData(cls):
        cls.user, cls.farmer = cls.create_farmer("juan")
        cls.small_farm = Farm.objects.create(
            owner=cls.farmer, name="Finca Pequeña", address="Vereda A"
        )
        cls.big_farm = Farm.objects.create(
            owner=cls.farmer, name="Finca Grande", address="Vereda B"
        )

        cls.counted_plot = Plot.objects.create(farm=cls.small_farm, name="Lote A")
        Plot.objects.create(farm=cls.small_farm, name="Lote B")
        for index in range(3):
            FieldSensor.objects.create(
                plot=cls.counted_plot, name=f"Activo {index}", is_active=True
            )
        for index in range(2):
            FieldSensor.objects.create(
                plot=cls.counted_plot, name=f"Inactivo {index}", is_active=False
            )

        for index in range(12):
            plot = Plot.objects.create(farm=cls.big_farm, name=f"Lote {index:02d}")
            FieldSensor.objects.create(plot=plot, name=f"Sensor {index}", is_active=True)
            FieldSensor.objects.create(
                plot=plot, name=f"Sensor apagado {index}", is_active=False
            )

    def test_sensor_count_ignores_inactive_sensors(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse("farm:farm-plot-list", args=[self.small_farm.pk])
        )

        self.assertEqual(response.json()[0]["sensor_count"], 3)

    def test_query_count_does_not_grow_with_the_number_of_plots(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("farm:farm-plot-list", args=[self.small_farm.pk])
        big_url = reverse("farm:farm-plot-list", args=[self.big_farm.pk])

        # The two queries are the farm ownership lookup and the annotated plot list.
        # If this number changes, a query was added — do not just bump it.
        with self.assertNumQueries(2):
            two_plots = self.client.get(url)
        with self.assertNumQueries(2):
            twelve_plots = self.client.get(big_url)

        self.assertEqual(len(two_plots.json()), 2)
        self.assertEqual(len(twelve_plots.json()), 12)


class PlotLabelPointTests(GeoAPITestCaseMixin, APITestCase):
    """label_point must lie on the plot itself, which the centroid does not for a concave shape."""

    @classmethod
    def setUpTestData(cls):
        cls.user, cls.farmer = cls.create_farmer("juan")
        cls.farm = Farm.objects.create(
            owner=cls.farmer, name="Finca El Tesoro", address="Vereda El Tesoro"
        )
        cls.concave_plot = Plot.objects.create(
            farm=cls.farm, name="Lote En Ele", geometry=an_l_shaped_polygon()
        )
        cls.unmapped_plot = Plot.objects.create(farm=cls.farm, name="Lote Sin Mapear")

    def plots(self):
        self.client.force_authenticate(user=self.user)
        return self.client.get(reverse("farm:farm-plot-list", args=[self.farm.pk])).json()

    def a_point(self, geojson):
        return Point(geojson["coordinates"], srid=4326)

    def test_label_point_is_inside_a_concave_plot_but_the_centroid_is_not(self):
        shape = an_l_shaped_polygon()
        concave = self.plots()[0]

        self.assertEqual(concave["label_point"]["type"], "Point")
        self.assertEqual(set(concave["label_point"].keys()), {"type", "coordinates"})
        self.assertTrue(shape.contains(self.a_point(concave["label_point"])))
        self.assertFalse(shape.contains(self.a_point(concave["centroid"])))
        # The anchor the frontend used before label_point existed lands in the notch too.
        self.assertFalse(shape.contains(shape.envelope.centroid))

    def test_label_point_coordinates_are_longitude_first(self):
        longitude, latitude = self.plots()[0]["label_point"]["coordinates"]

        self.assertLess(longitude, 0)
        self.assertGreater(latitude, 0)

    def test_label_point_is_null_exactly_when_geometry_is_null(self):
        concave, unmapped = self.plots()

        self.assertIsNotNone(concave["label_point"])
        self.assertIsNone(unmapped["geometry"])
        self.assertIsNone(unmapped["label_point"])

    def test_plot_detail_carries_the_same_label_point(self):
        self.client.force_authenticate(user=self.user)

        detail = self.client.get(
            reverse("farm:plot-detail", args=[self.concave_plot.pk])
        ).json()

        self.assertEqual(detail["label_point"], self.plots()[0]["label_point"])


class PlotDetailTests(GeoAPITestCaseMixin, APITestCase):
    """AC29/AC33 — single object, byte-identical shared fields, 404 on someone else's plot."""

    @classmethod
    def setUpTestData(cls):
        cls.user, cls.farmer = cls.create_farmer("juan")
        cls.other_user, cls.other_farmer = cls.create_farmer("maria")

        cls.farm = Farm.objects.create(
            owner=cls.farmer, name="Finca El Tesoro", address="Vereda El Tesoro"
        )
        cls.plot = Plot.objects.create(
            farm=cls.farm,
            name="Lote Norte",
            description="Arroz de riego",
            geometry=a_polygon(),
        )
        FieldSensor.objects.create(plot=cls.plot, name="Sensor 1", is_active=True)
        FieldSensor.objects.create(plot=cls.plot, name="Sensor 2", is_active=False)

        cls.other_farm = Farm.objects.create(
            owner=cls.other_farmer, name="Finca La Montaña", address="Vereda El Roble"
        )
        cls.other_plot = Plot.objects.create(farm=cls.other_farm, name="Lote Ajeno")

    def test_detail_returns_a_single_object_with_the_farm_and_timestamps(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("farm:plot-detail", args=[self.plot.pk]))
        payload = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload["farm"], {"id": self.farm.pk, "name": self.farm.name})
        self.assertEqual(payload["sensor_count"], 1)
        self.assertTrue(payload["created_at"].endswith("Z"))
        self.assertTrue(payload["updated_at"].endswith("Z"))

    def test_the_shared_fields_are_identical_to_the_list_row(self):
        self.client.force_authenticate(user=self.user)

        list_row = self.client.get(
            reverse("farm:farm-plot-list", args=[self.farm.pk])
        ).json()[0]
        detail = self.client.get(reverse("farm:plot-detail", args=[self.plot.pk])).json()

        self.assertEqual({key: detail[key] for key in list_row}, list_row)

    def test_another_farmers_plot_is_404_and_leaks_nothing(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("farm:plot-detail", args=[self.other_plot.pk]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {"detail": "Not found."})
        self.assertNotIn(self.other_plot.name, response.content.decode())

    def test_an_unknown_plot_is_404(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("farm:plot-detail", args=[999999]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_requires_authentication(self):
        response = self.client.get(reverse("farm:plot-detail", args=[self.plot.pk]))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detail_is_a_single_query(self):
        self.client.force_authenticate(user=self.user)

        with self.assertNumQueries(1):
            self.client.get(reverse("farm:plot-detail", args=[self.plot.pk]))


class FarmWeatherTests(GeoAPITestCaseMixin, APITestCase):
    """AC22/AC33 plus the absent-key semantics of the weather endpoint."""

    @classmethod
    def setUpTestData(cls):
        cls.user, cls.farmer = cls.create_farmer("juan")
        cls.other_user, cls.other_farmer = cls.create_farmer("maria")

        cls.farm = Farm.objects.create(
            owner=cls.farmer, name="Finca El Tesoro", address="Vereda El Tesoro"
        )
        cls.stationless_farm = Farm.objects.create(
            owner=cls.farmer, name="Finca Sin Lotes", address="Vereda C"
        )
        cls.other_farm = Farm.objects.create(
            owner=cls.other_farmer, name="Finca La Montaña", address="Vereda El Roble"
        )

        cls.temperature = EnvironmentalVariable.objects.create(
            name="Temperatura del aire",
            semantic_key=SemanticKey.AIR_TEMPERATURE,
            unit="°C",
        )
        cls.radiation = EnvironmentalVariable.objects.create(
            name="Radiación solar",
            semantic_key=SemanticKey.SOLAR_RADIATION,
            unit="W/m²",
        )
        cls.pressure = EnvironmentalVariable.objects.create(
            name="Presión barométrica",
            semantic_key=SemanticKey.OTHER,
            unit="hPa",
        )
        cls.now = timezone.now()

    @classmethod
    def make_station(cls, farm=None, name="Estación", is_active=True):
        return WeatherStation.objects.create(
            farm=farm or cls.farm,
            name=name,
            station_id=f"seed-{name}",
            api_key="seed-not-a-real-key",
            is_active=is_active,
        )

    @classmethod
    def configure(cls, station, variable, is_active=True):
        return WeatherStationVariableConfiguration.objects.create(
            station=station,
            env_variable=variable,
            field_key=f"{variable.semantic_key}-{station.pk}",
            is_active=is_active,
        )

    @classmethod
    def record(cls, station_variable, value, minutes_ago=0):
        snapshot, _ = WeatherSnapshot.objects.get_or_create(
            station=station_variable.station,
            recorded_at=cls.now - timedelta(minutes=minutes_ago),
        )
        return WeatherMeasurement.objects.create(
            snapshot=snapshot, station_variable=station_variable, value=value
        )

    def weather(self, farm=None):
        self.client.force_authenticate(user=self.user)
        return self.client.get(reverse("farm:farm-weather", args=[(farm or self.farm).pk]))

    def test_an_entry_carries_exactly_value_unit_and_recorded_at(self):
        self.record(self.configure(self.make_station(), self.temperature), "27.40")

        payload = self.weather().json()

        self.assertEqual(set(payload.keys()), {"air_temperature"})
        entry = payload["air_temperature"]
        self.assertEqual(set(entry.keys()), {"value", "unit", "recorded_at"})
        self.assertIsInstance(entry["value"], float)
        self.assertEqual(entry["value"], 27.4)
        self.assertEqual(entry["unit"], "°C")
        self.assertTrue(entry["recorded_at"].endswith("Z"))

    def test_the_newest_reading_across_active_stations_wins(self):
        old = self.configure(self.make_station(name="Vieja"), self.temperature)
        new = self.configure(self.make_station(name="Nueva"), self.temperature)
        self.record(old, "18.00", minutes_ago=60)
        self.record(new, "27.40", minutes_ago=3)

        self.assertEqual(self.weather().json()["air_temperature"]["value"], 27.4)

    def test_a_tie_on_recorded_at_breaks_on_the_highest_station_id(self):
        first = self.configure(self.make_station(name="Primera"), self.temperature)
        second = self.configure(self.make_station(name="Segunda"), self.temperature)
        self.record(first, "18.00", minutes_ago=5)
        self.record(second, "27.40", minutes_ago=5)

        self.assertEqual(self.weather().json()["air_temperature"]["value"], 27.4)

    def test_an_inactive_station_is_ignored_even_with_the_newest_reading(self):
        active = self.configure(self.make_station(name="Activa"), self.temperature)
        inactive = self.configure(
            self.make_station(name="Apagada", is_active=False), self.temperature
        )
        self.record(active, "18.00", minutes_ago=60)
        self.record(inactive, "27.40", minutes_ago=1)

        self.assertEqual(self.weather().json()["air_temperature"]["value"], 18.0)

    def test_an_inactive_variable_configuration_is_ignored(self):
        station = self.make_station()
        self.record(self.configure(station, self.temperature, is_active=False), "27.40")

        self.assertEqual(self.weather().json(), {})

    def test_a_null_value_leaves_the_key_absent(self):
        station = self.make_station()
        self.record(self.configure(station, self.temperature), None)

        payload = self.weather().json()

        self.assertEqual(payload, {})
        self.assertNotIn("air_temperature", payload)

    def test_a_null_value_does_not_hide_an_older_usable_reading(self):
        station_variable = self.configure(self.make_station(), self.temperature)
        self.record(station_variable, "27.40", minutes_ago=30)
        self.record(station_variable, None, minutes_ago=1)

        self.assertEqual(self.weather().json()["air_temperature"]["value"], 27.4)

    def test_the_other_semantic_key_never_appears(self):
        station = self.make_station()
        self.record(self.configure(station, self.pressure), "1013.00")
        self.record(self.configure(station, self.temperature), "27.40")

        self.assertEqual(set(self.weather().json().keys()), {"air_temperature"})

    def test_an_unconfigured_variable_is_absent_rather_than_null(self):
        station = self.make_station()
        self.record(self.configure(station, self.temperature), "27.40")

        payload = self.weather().json()

        self.assertNotIn("solar_radiation", payload)
        self.assertEqual(list(payload), ["air_temperature"])

    def test_a_farm_without_stations_returns_an_empty_object(self):
        response = self.weather(farm=self.stationless_farm)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {})

    def test_query_count_does_not_grow_with_the_number_of_stations(self):
        single = self.configure(self.make_station(name="Única"), self.temperature)
        self.record(single, "27.40", minutes_ago=3)
        self.client.force_authenticate(user=self.user)

        # The two queries are the farm ownership lookup and the DISTINCT ON measurement query.
        with self.assertNumQueries(2):
            self.client.get(reverse("farm:farm-weather", args=[self.farm.pk]))

        for index in range(2):
            extra = self.configure(
                self.make_station(name=f"Extra {index}"), self.radiation
            )
            self.record(extra, "612.00", minutes_ago=index + 1)

        with self.assertNumQueries(2):
            response = self.client.get(reverse("farm:farm-weather", args=[self.farm.pk]))

        self.assertEqual(set(response.json().keys()), {"air_temperature", "solar_radiation"})

    def test_another_farmers_farm_is_404(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("farm:farm-weather", args=[self.other_farm.pk]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {"detail": "Not found."})

    def test_an_unknown_farm_is_404(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("farm:farm-weather", args=[999999]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_weather_requires_authentication(self):
        response = self.client.get(reverse("farm:farm-weather", args=[self.farm.pk]))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SeedDataContractTests(APITestCase):
    """The dev/E2E seed must expose the unhappy paths, not only the happy one.

    Without a null-boundary farm, a plotless farm, an unmapped plot, a farm whose station
    configures a single variable and a farm with no station at all, the dashboard's empty,
    stale and no-data states have nothing to render against.
    """

    fixtures = [
        "initial_users.json",
        "initial_farmers.json",
        "initial_farms_with_plots.json",
        "initial_sensors.json",
    ]

    @classmethod
    def setUpTestData(cls):
        call_command("seed_weather_readings", verbosity=0)
        cls.user = get_user_model().objects.get(email="juan.perez@email.com")

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_the_seeded_farmer_owns_a_mapped_farm_and_an_unmapped_one(self):
        farms = {farm["name"]: farm for farm in self.client.get(reverse("farm:farm-list")).json()}

        self.assertEqual(
            list(farms), ["Finca El Tesoro", "Finca San Vicente", "Finca Sin Lotes"]
        )
        self.assertEqual(farms["Finca El Tesoro"]["boundary"]["type"], "Polygon")
        self.assertIsNone(farms["Finca San Vicente"]["boundary"])
        self.assertIsNotNone(farms["Finca Sin Lotes"]["location"])

    def test_the_seeded_farm_has_a_plot_that_cannot_be_drawn_on_the_map(self):
        plots = {
            plot["name"]: plot
            for plot in self.client.get(reverse("farm:farm-plot-list", args=[1])).json()
        }

        self.assertIsNone(plots["Lote Sin Mapear"]["geometry"])
        self.assertEqual(plots["Lote Sin Mapear"]["description"], "")
        self.assertEqual(plots["Lote Sin Mapear"]["sensor_count"], 0)
        self.assertIsNotNone(plots["Lote La Colina"]["geometry"])
        self.assertEqual(plots["Lote La Colina"]["sensor_count"], 3)

    def test_the_seeded_farmer_owns_a_farm_without_plots(self):
        response = self.client.get(reverse("farm:farm-plot-list", args=[13]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_the_seeded_weather_covers_fresh_stale_and_missing_readings(self):
        fresh = self.client.get(reverse("farm:farm-weather", args=[1])).json()
        stale = self.client.get(reverse("farm:farm-weather", args=[2])).json()
        stationless = self.client.get(reverse("farm:farm-weather", args=[13])).json()

        self.assertEqual(set(fresh), {"air_temperature", "solar_radiation"})
        self.assertLess(self.age_minutes(fresh["air_temperature"]), 30)

        self.assertEqual(set(stale), {"air_temperature"})
        self.assertGreater(self.age_minutes(stale["air_temperature"]), 30)

        self.assertEqual(stationless, {})

    def test_the_seeded_readings_never_come_from_an_inactive_station(self):
        inactive_station_variables = WeatherStationVariableConfiguration.objects.filter(
            station__is_active=False
        )

        self.assertTrue(inactive_station_variables.exists())
        self.assertFalse(
            WeatherMeasurement.objects.filter(
                station_variable__in=inactive_station_variables
            ).exists()
        )

    def age_minutes(self, reading):
        recorded_at = datetime.fromisoformat(reading["recorded_at"])
        return (timezone.now() - recorded_at).total_seconds() / 60


class PlotListOrderingTests(GeoAPITestCaseMixin, APITestCase):
    """Contract §2 — plots come back alphabetically so the map tab order matches the list."""

    @classmethod
    def setUpTestData(cls):
        cls.user, cls.farmer = cls.create_farmer("juan")
        cls.farm = Farm.objects.create(
            owner=cls.farmer, name="Finca El Tesoro", address="Vereda El Tesoro"
        )
        # Insertion order is deliberately not alphabetical: rows created in the
        # expected order would come back sorted even with no ORDER BY at all.
        for name in ("Lote Sur", "Lote Ancla", "Lote Norte"):
            Plot.objects.create(farm=cls.farm, name=name)

    def test_the_plot_list_is_ordered_by_name(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("farm:farm-plot-list", args=[self.farm.pk]))

        self.assertEqual(
            [plot["name"] for plot in response.json()],
            ["Lote Ancla", "Lote Norte", "Lote Sur"],
        )

    def test_the_annotated_queryset_carries_an_explicit_order_by(self):
        # `Meta.ordering` is dropped from GROUP BY queries, so without an explicit
        # `order_by` the database is free to return any order it likes.
        queryset = self.farm.plots.with_sensor_count()

        self.assertTrue(queryset.ordered)
        self.assertEqual(queryset.query.order_by, ("name",))

    def test_the_farm_list_is_ordered_by_name(self):
        Farm.objects.create(
            owner=self.farmer, name="Finca Abanico", address="Vereda Abanico"
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("farm:farm-list"))

        self.assertEqual(
            [farm["name"] for farm in response.json()],
            ["Finca Abanico", "Finca El Tesoro"],
        )


class FarmAdminFormTests(TestCase):
    """The snippet edit page builds its form from `FarmAdminForm`, polygon widget included."""

    @classmethod
    def setUpTestData(cls):
        user = get_user_model().objects.create_user(
            username="admin-farmer", email="admin@example.com", password="testpass123"
        )
        cls.farmer = Farmer.objects.create(user=user, first_name="Admin")

    def test_the_snippet_viewset_builds_the_farm_admin_form(self):
        self.assertIs(WagtailFarmAdmin().get_form_class(), FarmAdminForm)
        self.assertIs(WagtailFarmAdmin().get_form_class(for_update=True), FarmAdminForm)

    def test_boundary_is_an_optional_polygon_drawn_on_a_leaflet_widget(self):
        form = FarmAdminForm()

        boundary = form.fields["boundary"]
        self.assertIsInstance(boundary, gis_forms.PolygonField)
        self.assertIsInstance(boundary.widget, LeafletWidget)
        self.assertFalse(boundary.required)

    def test_a_submitted_polygon_is_persisted_on_the_farm(self):
        form = FarmAdminForm(
            data={
                "owner": self.farmer.pk,
                "name": "Finca El Tesoro",
                "address": "Vereda El Tesoro",
                "boundary": a_polygon().wkt,
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        farm = form.save()

        self.assertEqual(farm.boundary.srid, 4326)
        self.assertTrue(farm.boundary.equals(a_polygon()))

    def test_a_farm_saves_without_a_boundary(self):
        form = FarmAdminForm(
            data={
                "owner": self.farmer.pk,
                "name": "Finca San Vicente",
                "address": "Vereda El Carmen",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.save().boundary)
