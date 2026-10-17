from datetime import timedelta
from decimal import Decimal

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
from predictions.models import IrrigationPrediction
from sensors.models import (
    EnvironmentalVariable,
    FieldSensor,
    FieldSensorVariable,
    SemanticKey,
    SensorMeasurement,
    WeatherMeasurement,
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

    def test_the_seeded_stations_cover_online_stale_inactive_and_missing(self):
        def statuses(farm_id):
            stations = self.client.get(reverse("sensors:farm-stations", args=[farm_id])).json()
            return {station["name"]: station["status"] for station in stations}

        self.assertEqual(
            statuses(1),
            {
                "Estación El Tesoro Antigua": "inactive",
                "Estación El Tesoro Norte": "online",
                "Estación El Tesoro Sur": "online",
            },
        )
        self.assertEqual(statuses(2), {"Estación San Vicente": "stale"})
        self.assertEqual(statuses(13), {})

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


class PlotOverviewTests(GeoAPITestCaseMixin, APITestCase):
    """Current conditions, hourly series, sensors and last irrigation of one plot."""

    @classmethod
    def setUpTestData(cls):
        cls.user, farmer = cls.create_farmer("juan")
        _, other_farmer = cls.create_farmer("maria")
        farm = Farm.objects.create(owner=farmer, name="Finca El Tesoro", address="Vereda")
        other_farm = Farm.objects.create(owner=other_farmer, name="Finca Ajena", address="Vereda")
        cls.plot = Plot.objects.create(farm=farm, name="Lote Norte")
        cls.other_plot = Plot.objects.create(farm=other_farm, name="Lote Ajeno")

        cls.sensor = FieldSensor.objects.create(plot=cls.plot, name="Sensor 1")
        cls.inactive_sensor = FieldSensor.objects.create(
            plot=cls.plot, name="Sensor apagado", is_active=False
        )
        cls.channels = {}
        for key, unit in (
            (SemanticKey.SOIL_MOISTURE, "%"),
            (SemanticKey.AIR_TEMPERATURE, "°C"),
            (SemanticKey.RELATIVE_HUMIDITY, "%"),
        ):
            variable = EnvironmentalVariable.objects.create(name=key, semantic_key=key, unit=unit)
            cls.channels[key] = FieldSensorVariable.objects.create(
                sensor=cls.sensor, env_variable=variable
            )
        cls.inactive_moisture = FieldSensorVariable.objects.create(
            sensor=cls.inactive_sensor,
            env_variable=cls.channels[SemanticKey.SOIL_MOISTURE].env_variable,
        )
        cls.now = timezone.now().replace(microsecond=0)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def record(self, key, value, minutes_ago, channel=None):
        SensorMeasurement.objects.create(
            sensor_variable=channel or self.channels[key],
            value=Decimal(str(value)),
            recorded_at=self.now - timedelta(minutes=minutes_ago),
        )

    def overview(self, plot=None):
        return self.client.get(reverse("farm:plot-overview", args=[(plot or self.plot).pk]))

    def conditions_by_key(self, response):
        return {row["semantic_key"]: row for row in response.json()["conditions"]}

    def test_conditions_hold_the_latest_reading_and_its_24h_change(self):
        self.record(SemanticKey.SOIL_MOISTURE, 25, minutes_ago=5)
        self.record(SemanticKey.SOIL_MOISTURE, 40, minutes_ago=60)
        self.record(SemanticKey.SOIL_MOISTURE, 31, minutes_ago=24 * 60 + 10)

        condition = self.conditions_by_key(self.overview())[SemanticKey.SOIL_MOISTURE]

        self.assertEqual(condition["value"], 25.0)
        self.assertEqual(condition["unit"], "%")
        self.assertEqual(condition["change_24h"], -6.0)

    def test_change_is_null_without_a_reading_around_24h_ago(self):
        self.record(SemanticKey.SOIL_MOISTURE, 25, minutes_ago=5)
        self.record(SemanticKey.SOIL_MOISTURE, 31, minutes_ago=3 * 24 * 60)

        condition = self.conditions_by_key(self.overview())[SemanticKey.SOIL_MOISTURE]

        self.assertIsNone(condition["change_24h"])

    def test_model_inputs_are_classified_with_the_fuzzy_terms(self):
        self.record(SemanticKey.SOIL_MOISTURE, 40, minutes_ago=5)
        self.record(SemanticKey.AIR_TEMPERATURE, 17, minutes_ago=5)
        self.record(SemanticKey.RELATIVE_HUMIDITY, 80, minutes_ago=5)

        conditions = self.conditions_by_key(self.overview())

        moisture = conditions[SemanticKey.SOIL_MOISTURE]
        self.assertEqual(moisture["level"], "high")
        self.assertEqual(moisture["level_degrees"], {"low": 0.0, "medium": 0.333, "high": 0.667})
        self.assertEqual(conditions[SemanticKey.AIR_TEMPERATURE]["level"], "medium")
        self.assertIsNone(conditions[SemanticKey.RELATIVE_HUMIDITY]["level"])
        self.assertIsNone(conditions[SemanticKey.RELATIVE_HUMIDITY]["level_degrees"])

    def test_conditions_follow_the_display_order(self):
        for key in self.channels:
            self.record(key, 10, minutes_ago=5)

        keys = [row["semantic_key"] for row in self.overview().json()["conditions"]]

        self.assertEqual(
            keys,
            [SemanticKey.SOIL_MOISTURE, SemanticKey.AIR_TEMPERATURE, SemanticKey.RELATIVE_HUMIDITY],
        )

    def test_inactive_sensors_do_not_feed_the_conditions(self):
        self.record(SemanticKey.SOIL_MOISTURE, 25, minutes_ago=30)
        self.record(SemanticKey.SOIL_MOISTURE, 99, minutes_ago=1, channel=self.inactive_moisture)

        condition = self.conditions_by_key(self.overview())[SemanticKey.SOIL_MOISTURE]

        self.assertEqual(condition["value"], 25.0)

    def test_series_are_hourly_over_the_last_week(self):
        self.record(SemanticKey.SOIL_MOISTURE, 20, minutes_ago=10)
        self.record(SemanticKey.SOIL_MOISTURE, 30, minutes_ago=3 * 24 * 60)
        self.record(SemanticKey.SOIL_MOISTURE, 50, minutes_ago=8 * 24 * 60)

        series = self.overview().json()["series"]

        self.assertEqual(len(series), 1)
        self.assertEqual(series[0]["bucket_seconds"], 3600)
        self.assertEqual([point["value"] for point in series[0]["points"]], [30.0, 20.0])
        for point in series[0]["points"]:
            self.assertRegex(point["t"], r":00:00Z$")

    def test_lists_the_plot_sensors_with_their_status(self):
        response = self.overview()

        sensors = {row["name"]: row["status"] for row in response.json()["sensors"]}
        self.assertEqual(sensors, {"Sensor 1": "never_seen", "Sensor apagado": "inactive"})

    def test_includes_the_latest_irrigation_prediction(self):
        self.assertIsNone(self.overview().json()["irrigation"])
        for minutes in (5, 12):
            IrrigationPrediction.objects.create(
                plot=self.plot,
                avg_moisture=1,
                avg_temperature=1,
                avg_radiation=1,
                irrigation_time_minutes=minutes,
            )

        irrigation = self.overview().json()["irrigation"]

        self.assertEqual(irrigation["irrigation_time_minutes"], 12.0)

    def test_empty_plot_returns_empty_sections(self):
        payload = self.overview().json()

        self.assertEqual(payload["conditions"], [])
        self.assertEqual(payload["series"], [])

    def test_plot_of_another_user_returns_404(self):
        self.assertEqual(self.overview(self.other_plot).status_code, status.HTTP_404_NOT_FOUND)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)

        self.assertEqual(self.overview().status_code, status.HTTP_401_UNAUTHORIZED)


class FarmOverviewTests(GeoAPITestCaseMixin, APITestCase):
    """Farm-wide conditions, per-plot summaries and sensors behind the dashboard."""

    @classmethod
    def setUpTestData(cls):
        cls.user, farmer = cls.create_farmer("juan")
        _, other_farmer = cls.create_farmer("maria")
        cls.farm = Farm.objects.create(owner=farmer, name="Finca El Tesoro", address="Vereda")
        cls.other_farm = Farm.objects.create(
            owner=other_farmer, name="Finca Ajena", address="Vereda"
        )
        cls.north = Plot.objects.create(farm=cls.farm, name="Lote Norte")
        cls.south = Plot.objects.create(farm=cls.farm, name="Lote Sur")
        cls.empty = Plot.objects.create(farm=cls.farm, name="Lote Vacío")
        foreign_plot = Plot.objects.create(farm=cls.other_farm, name="Lote Ajeno")

        cls.moisture = EnvironmentalVariable.objects.create(
            name="Humedad del suelo", semantic_key=SemanticKey.SOIL_MOISTURE, unit="%"
        )
        cls.channels = {}
        for plot in (cls.north, cls.south, foreign_plot):
            sensor = FieldSensor.objects.create(plot=plot, name=f"Sensor {plot.name}")
            cls.channels[plot.pk] = FieldSensorVariable.objects.create(
                sensor=sensor, env_variable=cls.moisture
            )
        cls.now = timezone.now().replace(microsecond=0)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def record(self, plot, value, minutes_ago):
        SensorMeasurement.objects.create(
            sensor_variable=self.channels[plot.pk],
            value=Decimal(str(value)),
            recorded_at=self.now - timedelta(minutes=minutes_ago),
        )

    def overview(self, farm=None):
        return self.client.get(reverse("farm:farm-overview", args=[(farm or self.farm).pk]))

    def plots_by_name(self, payload):
        return {plot["name"]: plot for plot in payload["plots"]}

    def test_farm_conditions_average_the_latest_reading_of_each_plot(self):
        self.record(self.north, 20, minutes_ago=5)
        self.record(self.north, 90, minutes_ago=60)
        self.record(self.south, 40, minutes_ago=10)

        [moisture] = self.overview().json()["conditions"]

        self.assertEqual(moisture["value"], 30.0)
        self.assertEqual(moisture["level"], "medium")

    def test_farm_change_averages_the_plots_that_have_one(self):
        self.record(self.north, 20, minutes_ago=5)
        self.record(self.north, 30, minutes_ago=24 * 60 + 10)
        self.record(self.south, 40, minutes_ago=5)

        [moisture] = self.overview().json()["conditions"]

        self.assertEqual(moisture["change_24h"], -10.0)

    def test_every_plot_is_summarised_even_without_readings(self):
        self.record(self.north, 20, minutes_ago=5)
        IrrigationPrediction.objects.create(
            plot=self.south,
            avg_moisture=1,
            avg_temperature=1,
            avg_radiation=1,
            irrigation_time_minutes=7,
        )

        plots = self.plots_by_name(self.overview().json())

        self.assertEqual(list(plots), ["Lote Norte", "Lote Sur", "Lote Vacío"])
        self.assertEqual(plots["Lote Norte"]["conditions"][0]["value"], 20.0)
        self.assertIsNotNone(plots["Lote Norte"]["latest_reading_at"])
        self.assertEqual(plots["Lote Sur"]["irrigation"]["irrigation_time_minutes"], 7.0)
        self.assertEqual(plots["Lote Vacío"]["conditions"], [])
        self.assertIsNone(plots["Lote Vacío"]["latest_reading_at"])
        self.assertIsNone(plots["Lote Vacío"]["irrigation"])

    def test_plot_series_are_hourly_per_variable(self):
        self.record(self.north, 20, minutes_ago=10)
        self.record(self.north, 30, minutes_ago=3 * 60)

        plots = self.plots_by_name(self.overview().json())

        [series] = plots["Lote Norte"]["series"]
        self.assertEqual(series["semantic_key"], SemanticKey.SOIL_MOISTURE)
        self.assertEqual([point["value"] for point in series["points"]], [30.0, 20.0])
        self.assertEqual(plots["Lote Sur"]["series"], [])

    def test_lists_the_farm_sensors_only(self):
        names = [sensor["name"] for sensor in self.overview().json()["sensors"]]

        self.assertEqual(names, ["Sensor Lote Norte", "Sensor Lote Sur"])

    def test_farm_of_another_user_returns_404(self):
        self.assertEqual(self.overview(self.other_farm).status_code, status.HTTP_404_NOT_FOUND)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)

        self.assertEqual(self.overview().status_code, status.HTTP_401_UNAUTHORIZED)


class PlotSummaryListTests(GeoAPITestCaseMixin, APITestCase):
    """"Mis lotes": every plot the user owns, across farms, with light stats."""

    @classmethod
    def setUpTestData(cls):
        cls.user, farmer = cls.create_farmer("juan")
        _, other_farmer = cls.create_farmer("maria")
        tesoro = Farm.objects.create(owner=farmer, name="Finca El Tesoro", address="Vereda")
        vicente = Farm.objects.create(owner=farmer, name="Finca San Vicente", address="Vereda")
        foreign = Farm.objects.create(owner=other_farmer, name="Finca Ajena", address="Vereda")
        cls.north = Plot.objects.create(farm=tesoro, name="Lote Norte", geometry=a_polygon())
        cls.vicente_plot = Plot.objects.create(farm=vicente, name="Lote Alto")
        Plot.objects.create(farm=foreign, name="Lote Ajeno")

        moisture = EnvironmentalVariable.objects.create(
            name="Humedad del suelo", semantic_key=SemanticKey.SOIL_MOISTURE, unit="%"
        )
        sensor = FieldSensor.objects.create(plot=cls.north, name="Sensor 1")
        FieldSensor.objects.create(plot=cls.north, name="Sensor apagado", is_active=False)
        cls.channel = FieldSensorVariable.objects.create(sensor=sensor, env_variable=moisture)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def summaries(self):
        return self.client.get(reverse("farm:plot-summary-list")).json()

    def test_lists_the_user_plots_of_every_farm_ordered_by_farm(self):
        names = [(row["farm"]["name"], row["name"]) for row in self.summaries()]

        self.assertEqual(
            names, [("Finca El Tesoro", "Lote Norte"), ("Finca San Vicente", "Lote Alto")]
        )

    def test_each_plot_carries_its_stats_and_latest_readings(self):
        SensorMeasurement.objects.create(
            sensor_variable=self.channel,
            value=Decimal("12"),
            recorded_at=timezone.now() - timedelta(minutes=5),
        )

        north, alto = self.summaries()

        self.assertEqual(north["sensor_count"], 1)
        # The model derives the area from the polygon on save.
        self.north.refresh_from_db()
        self.assertEqual(north["area_hectares"], f"{self.north.area_hectares:.2f}")
        self.assertTrue(north["has_geometry"])
        self.assertEqual(north["conditions"][0]["value"], 12.0)
        self.assertEqual(north["conditions"][0]["level"], "low")
        self.assertIsNotNone(north["latest_reading_at"])
        self.assertEqual(alto["conditions"], [])
        self.assertIsNone(alto["latest_reading_at"])
        self.assertFalse(alto["has_geometry"])
        self.assertIsNone(alto["irrigation"])

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(reverse("farm:plot-summary-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

