import csv
import io
import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import models
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from farm.models import Farm, Plot
from farmer.models import Farmer
from sensors.api import READING_ORDER
from sensors.models import (
    EnvironmentalVariable,
    FieldSensor,
    FieldSensorVariable,
    SemanticKey,
    SensorMeasurement,
    WeatherMeasurement,
    WeatherSnapshot,
    WeatherStation,
    WeatherStationVariableConfiguration,
)

BOM_UTF8 = "\ufeff"


class SeedWeatherReadingsCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = get_user_model().objects.create_user(
            username="juan", email="juan@example.com", password="testpass123"
        )
        farmer = Farmer.objects.create(user=user, first_name="Juan")
        cls.fresh_farm = Farm.objects.create(
            owner=farmer, name="Finca El Tesoro", address="Vereda El Tesoro"
        )
        cls.stale_farm = Farm.objects.create(
            owner=farmer, name="Finca San Vicente", address="Vereda El Carmen"
        )

        cls.temperature = EnvironmentalVariable.objects.create(
            name="Temperatura del aire",
            semantic_key=SemanticKey.AIR_TEMPERATURE,
            unit="°C",
        )
        cls.fresh_station = cls.make_station(cls.fresh_farm, "Activa")
        cls.stale_station = cls.make_station(cls.stale_farm, "Desactualizada")
        cls.inactive_station = cls.make_station(cls.fresh_farm, "Apagada", is_active=False)
        cls.unconfigured_station = cls.make_station(cls.fresh_farm, "Sin variables")

    @classmethod
    def make_station(cls, farm, name, is_active=True):
        station = WeatherStation.objects.create(
            farm=farm,
            name=name,
            station_id=f"seed-{name}",
            api_key="seed-not-a-real-key",
            is_active=is_active,
        )
        if name != "Sin variables":
            WeatherStationVariableConfiguration.objects.create(
                station=station,
                env_variable=cls.temperature,
                field_key="temp_out",
                is_active=True,
            )
        return station

    def newest_recorded_at(self, station):
        return station.snapshots.order_by("-recorded_at").first().recorded_at

    def test_it_seeds_a_recent_snapshot_series_per_active_station(self):
        call_command("seed_weather_readings", verbosity=0)

        self.assertEqual(self.fresh_station.snapshots.count(), 12)
        age = timezone.now() - self.newest_recorded_at(self.fresh_station)
        self.assertLess(age, timedelta(minutes=10))
        self.assertEqual(
            WeatherMeasurement.objects.filter(snapshot__station=self.fresh_station).count(),
            12,
        )

    def test_the_stale_farm_is_seeded_past_the_staleness_threshold(self):
        call_command("seed_weather_readings", stale_farm=self.stale_farm.pk, verbosity=0)

        age = timezone.now() - self.newest_recorded_at(self.stale_station)
        self.assertGreater(age, timedelta(minutes=30))

    def test_stations_without_an_active_configuration_are_skipped(self):
        call_command("seed_weather_readings", verbosity=0)

        self.assertFalse(self.inactive_station.snapshots.exists())
        self.assertFalse(self.unconfigured_station.snapshots.exists())

    def test_running_it_twice_replaces_rather_than_duplicates(self):
        call_command("seed_weather_readings", verbosity=0)
        call_command("seed_weather_readings", verbosity=0)

        self.assertEqual(WeatherSnapshot.objects.count(), 24)

    def test_the_flags_control_the_series(self):
        call_command(
            "seed_weather_readings",
            count=3,
            interval_minutes=10,
            farm=self.fresh_farm.pk,
            verbosity=0,
        )

        recorded = list(
            self.fresh_station.snapshots.order_by("-recorded_at").values_list(
                "recorded_at", flat=True
            )
        )
        self.assertEqual(len(recorded), 3)
        self.assertEqual(recorded[0] - recorded[1], timedelta(minutes=10))
        self.assertFalse(self.stale_station.snapshots.exists())

    def test_seeded_values_stay_inside_the_plausible_range_of_their_variable(self):
        call_command("seed_weather_readings", verbosity=0)

        values = WeatherMeasurement.objects.values_list("value", flat=True)
        self.assertTrue(all(18 <= value <= 30 for value in values))


class SensorHistoryTestCase(APITestCase):
    """Owner, farm, plot and sensor scaffolding shared by the six history endpoints."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="juan", email="juan@example.com", password="testpass123"
        )
        cls.farmer = Farmer.objects.create(user=cls.user, first_name="Juan")
        cls.other_user = get_user_model().objects.create_user(
            username="maria", email="maria@example.com", password="testpass123"
        )
        cls.other_farmer = Farmer.objects.create(user=cls.other_user, first_name="María")

        cls.farm = Farm.objects.create(
            owner=cls.farmer, name="Finca El Tesoro", address="Vereda La Esperanza"
        )
        cls.second_farm = Farm.objects.create(
            owner=cls.farmer, name="Finca San Vicente", address="Vereda El Carmen"
        )
        cls.other_farm = Farm.objects.create(
            owner=cls.other_farmer, name="Finca La Montaña", address="Vereda El Roble"
        )

        cls.plot = Plot.objects.create(farm=cls.farm, name="Lote Norte")
        cls.second_plot = Plot.objects.create(farm=cls.farm, name="Lote Sur")
        # Owned by the same farmer, but hanging off a different farm than the route's.
        cls.plot_of_another_farm = Plot.objects.create(farm=cls.second_farm, name="Lote Vecino")

        cls.temperature = cls.make_variable(
            "Temperatura del aire", SemanticKey.AIR_TEMPERATURE, "°C"
        )
        cls.moisture = cls.make_variable("Humedad del suelo", SemanticKey.SOIL_MOISTURE, "%")

        cls.sensor = FieldSensor.objects.create(plot=cls.plot, name="Sensor 1 — Lote Norte")
        cls.inactive_sensor = FieldSensor.objects.create(
            plot=cls.plot, name="Sensor apagado", is_active=False
        )

        cls.now = timezone.now().replace(microsecond=0)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    @classmethod
    def make_variable(cls, name, semantic_key, unit):
        return EnvironmentalVariable.objects.create(
            name=name, semantic_key=semantic_key, unit=unit
        )

    @classmethod
    def measure(cls, sensor, variable):
        return FieldSensorVariable.objects.create(sensor=sensor, env_variable=variable)

    @classmethod
    def record(cls, sensor_variable, value, minutes_ago=0):
        return SensorMeasurement.objects.create(
            sensor_variable=sensor_variable,
            value=None if value is None else Decimal(str(value)),
            recorded_at=cls.now - timedelta(minutes=minutes_ago),
        )

    def history(self, name, farm=None, **params):
        target = self.farm if farm is None else farm
        return self.client.get(reverse(f"sensors:{name}", args=[target.pk]), params)

    def moment(self, **offset):
        return (self.now - timedelta(**offset)).isoformat()

    def wire_time(self, moment):
        return moment.isoformat().replace("+00:00", "Z")


class SensorHistoryVariablesTests(SensorHistoryTestCase):
    """The variable picker only offers what the active sensors of the scope really measure."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.radiation = cls.make_variable(
            "Radiación solar", SemanticKey.SOLAR_RADIATION, "W/m²"
        )
        cls.measure(cls.sensor, cls.temperature)
        cls.second_sensor = FieldSensor.objects.create(
            plot=cls.second_plot, name="Sensor 1 — Lote Sur"
        )
        cls.measure(cls.second_sensor, cls.moisture)
        cls.measure(cls.inactive_sensor, cls.radiation)

    def test_it_lists_the_variables_measured_by_the_active_sensors_of_the_farm(self):
        response = self.history("history-variables")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [variable["name"] for variable in response.json()],
            ["Humedad del suelo", "Temperatura del aire"],
        )

    def test_a_row_carries_the_identity_and_the_presentation_fields(self):
        response = self.history("history-variables", plot=self.plot.pk)

        self.assertEqual(
            response.json(),
            [
                {
                    "variable_id": self.temperature.pk,
                    "semantic_key": "air_temperature",
                    "name": "Temperatura del aire",
                    "unit": "°C",
                }
            ],
        )

    def test_filtering_by_plot_narrows_the_list(self):
        response = self.history("history-variables", plot=self.second_plot.pk)

        self.assertEqual(
            [variable["name"] for variable in response.json()], ["Humedad del suelo"]
        )

    def test_a_variable_measured_only_by_an_inactive_sensor_is_absent(self):
        names = [variable["name"] for variable in self.history("history-variables").json()]

        self.assertNotIn("Radiación solar", names)

    def test_a_farm_without_sensors_returns_an_empty_list(self):
        response = self.history("history-variables", farm=self.second_farm)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_it_is_a_constant_two_queries(self):
        # The two queries are the farm ownership lookup and the distinct variable list.
        # If this number changes, a query was added — do not just bump it.
        with self.assertNumQueries(2):
            self.history("history-variables")

    def test_a_plot_of_another_farm_of_the_same_owner_is_not_found(self):
        response = self.history("history-variables", plot=self.plot_of_another_farm.pk)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_a_farm_owned_by_someone_else_is_not_found(self):
        response = self.history("history-variables", farm=self.other_farm)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {"detail": "Not found."})

    def test_it_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.history("history-variables")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SensorHistoryReadingsTests(SensorHistoryTestCase):
    """The paginated table: envelope, stable order, filters and range validation."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.temperature_variable = cls.measure(cls.sensor, cls.temperature)
        cls.moisture_variable = cls.measure(cls.sensor, cls.moisture)
        cls.second_sensor = FieldSensor.objects.create(
            plot=cls.second_plot, name="Sensor 1 — Lote Sur"
        )
        cls.second_plot_variable = cls.measure(cls.second_sensor, cls.temperature)

    def record_series(self, count, minutes_ago=None):
        return [
            self.record(
                self.temperature_variable,
                20 + step,
                minutes_ago=step + 1 if minutes_ago is None else minutes_ago,
            )
            for step in range(count)
        ]

    def test_the_first_page_holds_twenty_rows_and_the_total_count(self):
        self.record_series(25)

        body = self.history("history-readings").json()

        self.assertEqual(set(body), {"count", "page", "page_size", "results"})
        self.assertEqual(body["count"], 25)
        self.assertEqual(body["page"], 1)
        self.assertEqual(body["page_size"], 20)
        self.assertEqual(len(body["results"]), 20)

    def test_the_rows_run_from_the_newest_reading_to_the_oldest(self):
        self.record_series(3)

        recorded = [row["recorded_at"] for row in self.history("history-readings").json()["results"]]

        self.assertEqual(recorded, sorted(recorded, reverse=True))

    def test_the_second_page_continues_where_the_first_ended(self):
        self.record_series(25)

        first = self.history("history-readings").json()
        second = self.history("history-readings", page=2).json()

        self.assertEqual(second["page"], 2)
        self.assertEqual(len(second["results"]), 5)
        self.assertEqual(
            set(row["id"] for row in first["results"])
            & set(row["id"] for row in second["results"]),
            set(),
        )

    def test_readings_sharing_a_timestamp_page_deterministically(self):
        # Every row carries the very same `recorded_at`, so the 20/5 page border falls in the
        # middle of one big tie: only the `-id` tie-break decides which rows land on which page.
        readings = self.record_series(25, minutes_ago=5)
        expected = sorted((reading.pk for reading in readings), reverse=True)

        first = self.history("history-readings").json()["results"]
        second = self.history("history-readings", page=2).json()["results"]

        paged = [row["id"] for row in first] + [row["id"] for row in second]
        self.assertEqual(paged, expected)

    def test_the_reading_order_ends_in_a_unique_tie_break(self):
        # The behaviour test above cannot pin this on its own: PostgreSQL is free to return a
        # tie in any order, and for a table this small it happens to pick the same one twice.
        # Assert the ORDER BY itself, so dropping `-id` fails here instead of in production.
        sql = str(SensorMeasurement.objects.order_by(*READING_ORDER).query)

        self.assertEqual(READING_ORDER, ("-recorded_at", "-id"))
        self.assertRegex(sql, r'ORDER BY .*"recorded_at" DESC, .*"id" DESC')

    def test_a_page_beyond_the_last_one_is_not_found(self):
        self.record_series(1)

        response = self.history("history-readings", page=5)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_a_row_names_the_plot_the_sensor_and_the_variable(self):
        reading = self.record(self.temperature_variable, "27.4133", minutes_ago=3)

        row = self.history("history-readings").json()["results"][0]

        self.assertEqual(
            row,
            {
                "id": reading.pk,
                "recorded_at": self.wire_time(reading.recorded_at),
                "plot_id": self.plot.pk,
                "plot_name": "Lote Norte",
                "sensor_id": self.sensor.pk,
                "sensor_name": "Sensor 1 — Lote Norte",
                "variable_id": self.temperature.pk,
                "semantic_key": "air_temperature",
                "variable_name": "Temperatura del aire",
                "value": 27.4133,
                "unit": "°C",
            },
        )

    def test_the_value_travels_as_a_json_number_not_a_string(self):
        self.record(self.temperature_variable, "27.4133", minutes_ago=3)

        row = self.history("history-readings").json()["results"][0]

        self.assertIsInstance(row["value"], float)
        self.assertTrue(row["recorded_at"].endswith("Z"))

    def test_a_reading_without_a_value_is_absent(self):
        self.record(self.temperature_variable, None, minutes_ago=2)
        kept = self.record(self.temperature_variable, 21, minutes_ago=3)

        body = self.history("history-readings").json()

        self.assertEqual([row["id"] for row in body["results"]], [kept.pk])

    def test_a_reading_of_an_inactive_sensor_is_absent(self):
        inactive_variable = self.measure(self.inactive_sensor, self.temperature)
        self.record(inactive_variable, 21, minutes_ago=2)

        self.assertEqual(self.history("history-readings").json()["count"], 0)

    def test_filtering_by_plot_keeps_only_that_plot(self):
        self.record(self.temperature_variable, 21, minutes_ago=2)
        self.record(self.second_plot_variable, 22, minutes_ago=3)

        body = self.history("history-readings", plot=self.second_plot.pk).json()

        self.assertEqual([row["plot_name"] for row in body["results"]], ["Lote Sur"])

    def test_filtering_by_variable_keeps_only_that_semantic_key(self):
        self.record(self.temperature_variable, 21, minutes_ago=2)
        self.record(self.moisture_variable, 40, minutes_ago=3)

        body = self.history("history-readings", variable="soil_moisture").json()

        self.assertEqual([row["semantic_key"] for row in body["results"]], ["soil_moisture"])

    def test_readings_outside_the_requested_range_are_excluded(self):
        inside = self.record(self.temperature_variable, 21, minutes_ago=60)
        self.record(self.temperature_variable, 22, minutes_ago=60 * 24 * 3)

        body = self.history(
            "history-readings",
            date_from=self.moment(hours=2),
            date_to=self.moment(minutes=1),
        ).json()

        self.assertEqual([row["id"] for row in body["results"]], [inside.pk])

    def test_an_absent_range_defaults_to_the_last_seven_days(self):
        recent = self.record(self.temperature_variable, 21, minutes_ago=60 * 24)
        self.record(self.temperature_variable, 22, minutes_ago=60 * 24 * 8)

        body = self.history("history-readings").json()

        self.assertEqual([row["id"] for row in body["results"]], [recent.pk])

    def test_a_range_wider_than_the_cap_is_rejected(self):
        response = self.history("history-readings", date_from=self.moment(days=91))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date_from", response.json())

    def test_a_range_that_ends_before_it_starts_is_rejected(self):
        response = self.history(
            "history-readings",
            date_from=self.moment(days=1),
            date_to=self.moment(days=2),
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date_from", response.json())

    def test_an_unreadable_date_is_rejected_naming_the_field(self):
        response = self.history("history-readings", date_from="ayer")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date_from", response.json())

    def test_an_unknown_variable_is_rejected_naming_the_field(self):
        response = self.history("history-readings", variable="humedad_lunar")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("variable", response.json())

    def test_a_plot_of_another_farm_of_the_same_owner_is_not_found(self):
        response = self.history("history-readings", plot=self.plot_of_another_farm.pk)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {"detail": "Not found."})

    def test_a_farm_owned_by_someone_else_leaks_nothing(self):
        foreign_sensor = FieldSensor.objects.create(
            plot=Plot.objects.create(farm=self.other_farm, name="Lote Ajeno"),
            name="Sensor ajeno",
        )
        self.record(self.measure(foreign_sensor, self.temperature), 21, minutes_ago=2)

        response = self.history("history-readings", farm=self.other_farm)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {"detail": "Not found."})

    def test_the_page_size_param_narrows_the_page(self):
        self.record_series(25)

        body = self.history("history-readings", page_size=5).json()

        self.assertEqual(body["page_size"], 5)
        self.assertEqual(len(body["results"]), 5)
        self.assertEqual(body["count"], 25)

    def test_the_page_size_param_widens_the_page_up_to_the_cap(self):
        self.record_series(100)

        body = self.history("history-readings", page_size=100).json()

        self.assertEqual(body["page_size"], 100)
        self.assertEqual(len(body["results"]), 100)

    def test_a_page_size_above_the_cap_is_clamped_to_a_hundred(self):
        self.record_series(101)

        body = self.history("history-readings", page_size=1000).json()

        self.assertEqual(body["page_size"], 100)
        self.assertEqual(len(body["results"]), 100)
        self.assertEqual(body["count"], 101)

    def test_an_unusable_page_size_falls_back_to_the_default(self):
        self.record_series(25)

        for page_size in (0, -3, "abc"):
            with self.subTest(page_size=page_size):
                body = self.history("history-readings", page_size=page_size).json()

                self.assertEqual(body["page_size"], 20)
                self.assertEqual(len(body["results"]), 20)

    def test_the_query_count_does_not_grow_with_the_page_size(self):
        self.record_series(25)
        # The three queries are the farm ownership lookup, the page count and the page
        # itself. If this number changes, a query was added — do not just bump it.
        with self.assertNumQueries(3):
            self.history("history-readings", page_size=5)
        with self.assertNumQueries(3):
            self.history("history-readings", page_size=100)

    def test_it_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.history("history-readings")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SensorHistorySeriesTests(SensorHistoryTestCase):
    """The chart series: one per variable, downsampled into date_bin buckets."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.temperature_variable = cls.measure(cls.sensor, cls.temperature)
        cls.moisture_variable = cls.measure(cls.sensor, cls.moisture)

    def series(self, **params):
        return self.history("history-series", plot=self.plot.pk, **params)

    def test_it_returns_one_series_per_variable_measured_by_the_plot(self):
        self.record(self.temperature_variable, 21, minutes_ago=5)
        self.record(self.moisture_variable, 40, minutes_ago=5)

        body = self.series().json()

        self.assertEqual(
            [entry["name"] for entry in body], ["Humedad del suelo", "Temperatura del aire"]
        )

    def test_a_series_carries_its_identity_unit_and_bucket_size(self):
        self.record(self.temperature_variable, 21, minutes_ago=5)

        entry = self.series(variable="air_temperature").json()[0]

        self.assertEqual(entry["variable_id"], self.temperature.pk)
        self.assertEqual(entry["semantic_key"], "air_temperature")
        self.assertEqual(entry["name"], "Temperatura del aire")
        self.assertEqual(entry["unit"], "°C")
        self.assertEqual(entry["bucket_seconds"], 3600)

    def test_points_are_bucket_averages_rather_than_raw_readings(self):
        range_start = self.now - timedelta(hours=1)
        self.record(self.temperature_variable, 20, minutes_ago=55)
        self.record(self.temperature_variable, 30, minutes_ago=52)

        entry = self.series(
            date_from=range_start.isoformat(), date_to=self.now.isoformat()
        ).json()[0]

        self.assertEqual(entry["bucket_seconds"], 900)
        self.assertEqual(
            entry["points"],
            [{"t": self.wire_time(range_start), "value": 25.0, "sample_count": 2}],
        )

    def test_empty_buckets_are_omitted_rather_than_sent_as_zero(self):
        range_start = self.now - timedelta(hours=1)
        self.record(self.temperature_variable, 20, minutes_ago=55)
        self.record(self.temperature_variable, 30, minutes_ago=25)

        points = self.series(
            date_from=range_start.isoformat(), date_to=self.now.isoformat()
        ).json()[0]["points"]

        self.assertEqual(len(points), 2)
        self.assertEqual(
            [point["t"] for point in points],
            [
                self.wire_time(range_start),
                self.wire_time(range_start + timedelta(minutes=30)),
            ],
        )

    def test_the_bucket_size_follows_the_span_of_the_range(self):
        self.record(self.temperature_variable, 21, minutes_ago=1)

        for days, expected_seconds in ((1, 900), (7, 3600), (30, 21600), (60, 86400)):
            with self.subTest(days=days):
                entry = self.series(date_from=self.moment(days=days)).json()[0]

                self.assertEqual(entry["bucket_seconds"], expected_seconds)

    def test_filtering_by_variable_returns_a_single_series(self):
        self.record(self.temperature_variable, 21, minutes_ago=5)
        self.record(self.moisture_variable, 40, minutes_ago=5)

        body = self.series(variable="soil_moisture").json()

        self.assertEqual([entry["semantic_key"] for entry in body], ["soil_moisture"])

    def test_two_variables_sharing_a_semantic_key_stay_separate_series(self):
        first = self.make_variable("Presión barométrica", SemanticKey.OTHER, "hPa")
        second = self.make_variable("Presión del suelo", SemanticKey.OTHER, "hPa")
        self.record(self.measure(self.sensor, first), 1010, minutes_ago=5)
        self.record(self.measure(self.sensor, second), 1015, minutes_ago=5)

        body = self.series(variable="other").json()

        self.assertEqual([entry["variable_id"] for entry in body], [first.pk, second.pk])
        self.assertEqual({entry["semantic_key"] for entry in body}, {"other"})

    def test_readings_of_an_inactive_sensor_never_enter_a_series(self):
        inactive_variable = self.measure(self.inactive_sensor, self.temperature)
        self.record(inactive_variable, 21, minutes_ago=5)

        self.assertEqual(self.series().json(), [])

    def test_a_plot_without_readings_returns_an_empty_list(self):
        response = self.series()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_the_query_count_does_not_grow_with_the_number_of_variables(self):
        self.record(self.temperature_variable, 21, minutes_ago=5)
        # The two queries are the plot ownership lookup and the single bucketed aggregate.
        # If this number changes, a query was added — do not just bump it.
        with self.assertNumQueries(2):
            one_series = self.series()

        self.record(self.moisture_variable, 40, minutes_ago=5)
        pressure = self.make_variable("Presión barométrica", SemanticKey.OTHER, "hPa")
        self.record(self.measure(self.sensor, pressure), 1010, minutes_ago=5)
        with self.assertNumQueries(2):
            three_series = self.series()

        self.assertEqual(len(one_series.json()), 1)
        self.assertEqual(len(three_series.json()), 3)

    def test_a_request_without_a_plot_is_rejected(self):
        response = self.history("history-series")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("plot", response.json())

    def test_a_plot_of_another_farm_of_the_same_owner_is_not_found(self):
        response = self.history("history-series", plot=self.plot_of_another_farm.pk)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_a_farm_owned_by_someone_else_is_not_found(self):
        response = self.history("history-series", farm=self.other_farm, plot=self.plot.pk)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {"detail": "Not found."})

    def test_it_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.series()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SensorHistoryPlotAveragesTests(SensorHistoryTestCase):
    """The farm-only mode: the average of every variable on every plot of the farm."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.temperature_variable = cls.measure(cls.sensor, cls.temperature)
        cls.second_sensor = FieldSensor.objects.create(
            plot=cls.second_plot, name="Sensor 1 — Lote Sur"
        )
        cls.second_plot_variable = cls.measure(cls.second_sensor, cls.moisture)

    def test_it_returns_one_average_per_variable_per_plot(self):
        self.record(self.temperature_variable, 20, minutes_ago=5)
        self.record(self.temperature_variable, 30, minutes_ago=6)
        self.record(self.second_plot_variable, 40, minutes_ago=5)

        body = self.history("history-plot-averages").json()

        self.assertEqual(
            body,
            [
                {
                    "plot_id": self.plot.pk,
                    "plot_name": "Lote Norte",
                    "variable_id": self.temperature.pk,
                    "semantic_key": "air_temperature",
                    "variable_name": "Temperatura del aire",
                    "unit": "°C",
                    "average": 25.0,
                    "sample_count": 2,
                },
                {
                    "plot_id": self.second_plot.pk,
                    "plot_name": "Lote Sur",
                    "variable_id": self.moisture.pk,
                    "semantic_key": "soil_moisture",
                    "variable_name": "Humedad del suelo",
                    "unit": "%",
                    "average": 40.0,
                    "sample_count": 1,
                },
            ],
        )

    def test_readings_outside_the_range_do_not_count(self):
        self.record(self.temperature_variable, 20, minutes_ago=30)
        self.record(self.temperature_variable, 30, minutes_ago=60 * 24 * 3)

        body = self.history("history-plot-averages", date_from=self.moment(hours=2)).json()

        self.assertEqual(body[0]["average"], 20.0)
        self.assertEqual(body[0]["sample_count"], 1)

    def test_a_plot_without_readings_is_absent_rather_than_null(self):
        self.record(self.temperature_variable, 20, minutes_ago=5)

        body = self.history("history-plot-averages").json()

        self.assertEqual([row["plot_name"] for row in body], ["Lote Norte"])

    def test_an_inactive_sensor_does_not_contribute(self):
        inactive_variable = self.measure(self.inactive_sensor, self.temperature)
        self.record(inactive_variable, 99, minutes_ago=5)
        self.record(self.temperature_variable, 20, minutes_ago=5)

        body = self.history("history-plot-averages").json()

        self.assertEqual(body[0]["average"], 20.0)
        self.assertEqual(body[0]["sample_count"], 1)

    def test_a_plot_param_is_ignored_so_the_farm_comparison_stays_whole(self):
        self.record(self.temperature_variable, 20, minutes_ago=5)
        self.record(self.second_plot_variable, 40, minutes_ago=5)

        body = self.history("history-plot-averages", plot=self.plot.pk).json()

        self.assertEqual([row["plot_name"] for row in body], ["Lote Norte", "Lote Sur"])

    def test_the_query_count_does_not_grow_with_the_number_of_plots(self):
        self.record(self.temperature_variable, 20, minutes_ago=5)
        self.record(self.second_plot_variable, 40, minutes_ago=5)
        big_farm = Farm.objects.create(
            owner=self.farmer, name="Finca Grande", address="Vereda Larga"
        )
        for index in range(12):
            sensor = FieldSensor.objects.create(
                plot=Plot.objects.create(farm=big_farm, name=f"Lote {index:02d}"),
                name=f"Sensor {index}",
            )
            self.record(self.measure(sensor, self.temperature), 20 + index, minutes_ago=5)

        # The two queries are the farm ownership lookup and the grouped average.
        # If this number changes, a query was added — do not just bump it.
        with self.assertNumQueries(2):
            two_plots = self.history("history-plot-averages")
        with self.assertNumQueries(2):
            twelve_plots = self.history("history-plot-averages", farm=big_farm)

        self.assertEqual(len(two_plots.json()), 2)
        self.assertEqual(len(twelve_plots.json()), 12)

    def test_a_farm_owned_by_someone_else_is_not_found(self):
        response = self.history("history-plot-averages", farm=self.other_farm)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {"detail": "Not found."})

    def test_it_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.history("history-plot-averages")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SensorHistoryExportTests(SensorHistoryTestCase):
    """The CSV and JSON exports carry the whole filtered set, streamed, never truncated."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.temperature_variable = cls.measure(cls.sensor, cls.temperature)
        cls.moisture_variable = cls.measure(cls.sensor, cls.moisture)

    def body_of(self, response):
        return b"".join(response.streaming_content).decode("utf-8")

    def csv_rows(self, response):
        text = self.body_of(response)
        self.assertTrue(text.startswith(BOM_UTF8))
        return list(csv.reader(io.StringIO(text.lstrip(BOM_UTF8))))

    def test_the_csv_carries_a_header_and_one_row_per_reading(self):
        reading = self.record(self.temperature_variable, "27.4133", minutes_ago=3)

        rows = self.csv_rows(self.history("history-export-csv"))

        self.assertEqual(
            rows[0],
            ["recorded_at", "plot", "sensor", "variable", "semantic_key", "value", "unit"],
        )
        self.assertEqual(
            rows[1],
            [
                self.wire_time(reading.recorded_at),
                "Lote Norte",
                "Sensor 1 — Lote Norte",
                "Temperatura del aire",
                "air_temperature",
                "27.4133",
                "°C",
            ],
        )

    def test_the_csv_is_utf8_with_a_byte_order_mark_so_excel_reads_the_accents(self):
        self.record(self.measure(self.sensor, self.make_variable(
            "Radiación solar", SemanticKey.SOLAR_RADIATION, "W/m²"
        )), 612, minutes_ago=3)

        text = self.body_of(self.history("history-export-csv"))

        self.assertTrue(text.startswith(BOM_UTF8))
        self.assertIn("Radiación solar", text)
        self.assertIn("W/m²", text)

    def test_the_csv_exports_the_whole_filtered_set_not_just_the_first_page(self):
        for step in range(25):
            self.record(self.temperature_variable, 20 + step, minutes_ago=step + 1)

        rows = self.csv_rows(self.history("history-export-csv"))

        self.assertEqual(len(rows), 26)

    def test_the_export_respects_the_filters(self):
        self.record(self.temperature_variable, 21, minutes_ago=3)
        self.record(self.moisture_variable, 40, minutes_ago=3)

        rows = self.csv_rows(self.history("history-export-csv", variable="soil_moisture"))

        self.assertEqual([row[4] for row in rows[1:]], ["soil_moisture"])

    def test_a_reading_without_a_value_is_absent_from_the_export(self):
        self.record(self.temperature_variable, None, minutes_ago=2)
        self.record(self.temperature_variable, 21, minutes_ago=3)

        rows = self.csv_rows(self.history("history-export-csv"))

        self.assertEqual(len(rows), 2)

    def test_the_filename_names_the_farm_and_the_range(self):
        response = self.history(
            "history-export-csv",
            date_from="2026-08-01T00:00:00Z",
            date_to="2026-08-22T00:00:00Z",
        )

        self.assertIn(
            'filename="historial-sensores-finca-el-tesoro-20260801_20260822.csv"',
            response.headers["Content-Disposition"],
        )
        self.assertIn("filename*=UTF-8''", response.headers["Content-Disposition"])
        self.assertEqual(response.headers["Content-Type"], "text/csv; charset=utf-8")

    def test_the_json_export_is_an_array_with_the_same_rows_and_order(self):
        for step in range(3):
            self.record(self.temperature_variable, 20 + step, minutes_ago=step + 1)

        csv_body = self.csv_rows(self.history("history-export-csv"))
        json_body = json.loads(self.body_of(self.history("history-export-json")))

        self.assertEqual(len(json_body), 3)
        self.assertEqual(
            [row["recorded_at"] for row in json_body], [row[0] for row in csv_body[1:]]
        )
        self.assertEqual(
            set(json_body[0]),
            {
                "recorded_at",
                "plot_id",
                "plot_name",
                "sensor_id",
                "sensor_name",
                "variable_id",
                "semantic_key",
                "variable_name",
                "value",
                "unit",
            },
        )
        self.assertIsInstance(json_body[0]["value"], float)

    def test_the_json_export_of_an_empty_set_is_an_empty_array(self):
        body = json.loads(self.body_of(self.history("history-export-json")))

        self.assertEqual(body, [])

    def test_the_json_filename_and_content_type_announce_a_download(self):
        response = self.history("history-export-json")

        self.assertEqual(response.headers["Content-Type"], "application/json")
        self.assertIn("attachment;", response.headers["Content-Disposition"])
        self.assertIn(".json", response.headers["Content-Disposition"])

    def test_both_exports_are_streamed(self):
        self.record(self.temperature_variable, 21, minutes_ago=3)

        self.assertTrue(self.history("history-export-csv").streaming)
        self.assertTrue(self.history("history-export-json").streaming)

    def test_a_set_over_the_cap_is_rejected_naming_the_count_and_the_limit(self):
        for step in range(3):
            self.record(self.temperature_variable, 20 + step, minutes_ago=step + 1)

        with patch("sensors.api.HISTORY_EXPORT_ROW_CAP", 2):
            response = self.history("history-export-csv")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "detail": "El rango seleccionado supera el máximo exportable.",
                "code": "export_too_large",
                "count": 3,
                "limit": 2,
            },
        )

    def test_the_json_export_honours_the_same_cap(self):
        for step in range(3):
            self.record(self.temperature_variable, 20 + step, minutes_ago=step + 1)

        with patch("sensors.api.HISTORY_EXPORT_ROW_CAP", 2):
            response = self.history("history-export-json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["code"], "export_too_large")

    def test_an_invalid_range_is_rejected(self):
        response = self.history("history-export-csv", date_from=self.moment(days=91))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date_from", response.json())

    def test_a_farm_owned_by_someone_else_is_not_found(self):
        response = self.history("history-export-csv", farm=self.other_farm)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {"detail": "Not found."})

    def test_it_requires_authentication(self):
        self.client.force_authenticate(user=None)

        self.assertEqual(
            self.history("history-export-csv").status_code, status.HTTP_401_UNAUTHORIZED
        )
        self.assertEqual(
            self.history("history-export-json").status_code, status.HTTP_401_UNAUTHORIZED
        )


class SeedSensorReadingsCommandTests(TestCase):
    """`seed_sensor_readings` is the only thing that creates `SensorMeasurement` rows today."""

    @classmethod
    def setUpTestData(cls):
        user = get_user_model().objects.create_user(
            username="juan", email="juan@example.com", password="testpass123"
        )
        farmer = Farmer.objects.create(user=user, first_name="Juan")
        cls.farm = Farm.objects.create(
            owner=farmer, name="Finca El Tesoro", address="Vereda La Esperanza"
        )
        cls.other_farm = Farm.objects.create(
            owner=farmer, name="Finca San Vicente", address="Vereda El Carmen"
        )
        cls.plot = Plot.objects.create(farm=cls.farm, name="Lote Norte")
        cls.second_plot = Plot.objects.create(farm=cls.farm, name="Lote Sur")

        active_sensor = FieldSensor.objects.create(plot=cls.plot, name="Sensor activo")
        second_sensor = FieldSensor.objects.create(plot=cls.second_plot, name="Sensor lote sur")
        inactive_sensor = FieldSensor.objects.create(
            plot=cls.plot, name="Sensor apagado", is_active=False
        )

        moisture = EnvironmentalVariable.objects.create(
            name="Humedad del suelo", semantic_key=SemanticKey.SOIL_MOISTURE, unit="%"
        )
        radiation = EnvironmentalVariable.objects.create(
            name="Radiación solar", semantic_key=SemanticKey.SOLAR_RADIATION, unit="W/m²"
        )
        temperature = EnvironmentalVariable.objects.create(
            name="Temperatura del aire", semantic_key=SemanticKey.AIR_TEMPERATURE, unit="°C"
        )

        # The command gives the lowest pk the gap and the highest pk the nulls, so the three
        # rows below are created in the order the assertions below expect.
        cls.gap_variable = FieldSensorVariable.objects.create(
            sensor=active_sensor, env_variable=moisture
        )
        cls.radiation_variable = FieldSensorVariable.objects.create(
            sensor=active_sensor, env_variable=radiation
        )
        cls.null_variable = FieldSensorVariable.objects.create(
            sensor=second_sensor, env_variable=temperature
        )
        cls.skipped_variable = FieldSensorVariable.objects.create(
            sensor=inactive_sensor, env_variable=temperature
        )

    def values_of(self, sensor_variable):
        return list(
            sensor_variable.measurements.order_by("recorded_at").values_list("value", flat=True)
        )

    def mean_between(self, readings, first_hour, last_hour):
        window = [
            float(value)
            for recorded_at, value in readings
            if first_hour <= recorded_at.hour < last_hour
        ]
        return sum(window) / len(window)

    def test_it_seeds_a_series_for_every_active_sensor_variable(self):
        call_command("seed_sensor_readings", days=2, verbosity=0)

        self.assertEqual(self.radiation_variable.measurements.count(), 193)
        self.assertEqual(self.null_variable.measurements.count(), 193)

    def test_variables_of_an_inactive_sensor_are_skipped(self):
        call_command("seed_sensor_readings", days=2, verbosity=0)

        self.assertEqual(self.skipped_variable.measurements.count(), 0)

    def test_running_it_twice_replaces_rather_than_duplicates(self):
        call_command("seed_sensor_readings", days=2, verbosity=0)
        after_one_run = SensorMeasurement.objects.count()
        call_command("seed_sensor_readings", days=2, verbosity=0)

        self.assertEqual(SensorMeasurement.objects.count(), after_one_run)

    def test_the_keep_flag_appends_instead_of_replacing(self):
        call_command("seed_sensor_readings", days=2, verbosity=0)
        after_one_run = SensorMeasurement.objects.count()
        call_command("seed_sensor_readings", days=2, keep=True, verbosity=0)

        self.assertEqual(SensorMeasurement.objects.count(), after_one_run * 2)

    def test_the_flags_control_the_span_and_the_resolution(self):
        call_command("seed_sensor_readings", days=1, interval_minutes=60, verbosity=0)

        recorded = list(
            self.radiation_variable.measurements.order_by("-recorded_at").values_list(
                "recorded_at", flat=True
            )
        )
        self.assertEqual(len(recorded), 25)
        self.assertEqual(recorded[0] - recorded[1], timedelta(minutes=60))

    def test_the_default_span_covers_a_full_month_of_history(self):
        call_command("seed_sensor_readings", verbosity=0)

        recorded = self.radiation_variable.measurements.aggregate(
            oldest=models.Min("recorded_at"), newest=models.Max("recorded_at")
        )
        self.assertEqual(recorded["newest"] - recorded["oldest"], timedelta(days=30))

    def test_the_newest_reading_is_recent_enough_for_the_24h_preset(self):
        call_command("seed_sensor_readings", days=2, verbosity=0)

        newest = self.radiation_variable.measurements.order_by("-recorded_at").first()

        self.assertLess(timezone.now() - newest.recorded_at, timedelta(minutes=20))

    def test_seeded_values_stay_inside_the_plausible_range_of_their_variable(self):
        call_command("seed_sensor_readings", days=2, verbosity=0)

        self.assertTrue(all(25 <= value <= 55 for value in self.values_of(self.gap_variable)))
        self.assertTrue(
            all(0 <= value <= 950 for value in self.values_of(self.radiation_variable))
        )

    def test_solar_radiation_is_dark_at_night_and_peaks_around_midday(self):
        # `seed` is not optional here: the curve is nearly flat around noon while the jitter
        # is of the same order, so an unseeded run makes this assertion a coin toss.
        call_command("seed_sensor_readings", days=2, seed=20260822, verbosity=0)

        readings = list(
            self.radiation_variable.measurements.values_list("recorded_at", "value")
        )
        night = [value for recorded_at, value in readings if recorded_at.hour < 5]

        self.assertTrue(all(value == 0 for value in night))
        # A window average, not the brightest single reading: the peak the AC asks for is a
        # property of the curve, and one noisy sample near the top proves nothing about it.
        midday = self.mean_between(readings, 11, 14)
        self.assertGreater(midday, self.mean_between(readings, 7, 10))
        self.assertGreater(midday, self.mean_between(readings, 16, 19))

    def test_it_leaves_a_gap_and_null_readings_so_the_unhappy_paths_have_data(self):
        call_command("seed_sensor_readings", days=2, verbosity=0)

        newest_of_gap = self.gap_variable.measurements.order_by("-recorded_at").first()
        newest_overall = self.radiation_variable.measurements.order_by("-recorded_at").first()

        self.assertEqual(
            newest_overall.recorded_at - newest_of_gap.recorded_at, timedelta(hours=6)
        )
        self.assertTrue(self.null_variable.measurements.filter(value__isnull=True).exists())

    def test_the_seed_flag_makes_the_series_reproducible(self):
        call_command("seed_sensor_readings", days=1, interval_minutes=60, seed=7, verbosity=0)
        first_run = list(
            SensorMeasurement.objects.order_by("sensor_variable_id", "recorded_at").values_list(
                "sensor_variable_id", "recorded_at", "value"
            )
        )
        call_command("seed_sensor_readings", days=1, interval_minutes=60, seed=7, verbosity=0)
        second_run = list(
            SensorMeasurement.objects.order_by("sensor_variable_id", "recorded_at").values_list(
                "sensor_variable_id", "recorded_at", "value"
            )
        )

        self.assertEqual(first_run, second_run)

    def test_the_plot_flag_narrows_the_seed(self):
        call_command("seed_sensor_readings", days=1, plot=self.second_plot.pk, verbosity=0)

        self.assertTrue(self.null_variable.measurements.exists())
        self.assertFalse(self.radiation_variable.measurements.exists())

    def test_the_farm_flag_narrows_the_seed(self):
        call_command("seed_sensor_readings", days=1, farm=self.other_farm.pk, verbosity=0)

        self.assertEqual(SensorMeasurement.objects.count(), 0)


class SensorSeedDataContractTests(APITestCase):
    """The fixtures plus the seeder must give the history page real data to render.

    Kept here rather than in `farm/tests.py::SeedDataContractTests` so that already heavy
    class does not also pay for seeding measurements.
    """

    fixtures = [
        "initial_users.json",
        "initial_farmers.json",
        "initial_farms_with_plots.json",
        "initial_sensors.json",
    ]

    REAL_VARIABLE_KEYS = {
        "air_temperature",
        "solar_radiation",
        "relative_humidity",
        "soil_moisture",
    }
    SEEDED_PLOTS = ((1, 1), (1, 2), (2, 3), (2, 4))

    @classmethod
    def setUpTestData(cls):
        call_command("seed_sensor_readings", days=2, verbosity=0)
        cls.user = get_user_model().objects.get(email="juan.perez@email.com")

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def get(self, name, farm_id, **params):
        return self.client.get(reverse(f"sensors:{name}", args=[farm_id]), params)

    def test_every_seeded_plot_measures_the_four_real_variables(self):
        for farm_id, plot_id in self.SEEDED_PLOTS:
            with self.subTest(plot=plot_id):
                body = self.get("history-variables", farm_id, plot=plot_id).json()

                self.assertEqual(
                    {variable["semantic_key"] for variable in body}, self.REAL_VARIABLE_KEYS
                )

    def test_every_seeded_plot_has_readings_for_the_four_real_variables(self):
        for farm_id, plot_id in self.SEEDED_PLOTS:
            with self.subTest(plot=plot_id):
                body = self.get("history-series", farm_id, plot=plot_id).json()

                self.assertEqual(
                    {entry["semantic_key"] for entry in body}, self.REAL_VARIABLE_KEYS
                )
                self.assertTrue(all(entry["points"] for entry in body))

    def test_the_farm_level_history_covers_the_four_real_variables(self):
        body = self.get("history-variables", 1).json()

        self.assertEqual(
            {variable["semantic_key"] for variable in body}, self.REAL_VARIABLE_KEYS
        )

    def test_the_variable_only_an_inactive_sensor_measures_stays_out(self):
        body = self.get("history-variables", 1, plot=1).json()

        self.assertNotIn("other", {variable["semantic_key"] for variable in body})

    def test_the_plot_without_sensors_reports_an_empty_history(self):
        readings = self.get("history-readings", 1, plot=29).json()
        series = self.get("history-series", 1, plot=29).json()

        self.assertEqual(readings["count"], 0)
        self.assertEqual(readings["results"], [])
        self.assertEqual(series, [])

    def test_the_farm_comparison_reports_every_seeded_plot(self):
        body = self.get("history-plot-averages", 1).json()

        self.assertEqual(
            {row["plot_name"] for row in body}, {"Lote La Colina", "Lote El Abrevadero"}
        )
