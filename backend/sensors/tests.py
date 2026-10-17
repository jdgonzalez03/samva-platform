import csv
import importlib.util
import io
import json
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, models
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import exceptions, status
from rest_framework.test import APITestCase

from backend.settings.common import mqtt_ingest_config, mqtt_source
from farm.models import Farm, Plot
from farmer.models import Farmer
from sensors import lorawan
from sensors.authentication import ApiKeyRateThrottle
from sensors.constants import (
    INGEST_MAX_CLOCK_SKEW,
    READING_ORDER,
    SENSOR_OFFLINE_AFTER,
    STATION_READING_ORDER,
    STATION_STALE_AFTER,
)
from sensors.lorawan import LoRaPayloadError, handle_uplink, parse_ttn_uplink
from sensors.management.commands import mqtt_ingest
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
from sensors.tasks import poll_weather_stations
from sensors.utils import resolve_sensor
from sensors.weather_station_providers.weatherlink import (
    _extract_measurements,
    fahrenheit_to_celsius,
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

    def record_series(self, count):
        return [
            self.record(self.temperature_variable, 20 + step, minutes_ago=step + 1)
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
        # One sensor stores a single row per instant, so the tie spans 25 sensors.
        readings = [
            self.record(
                self.measure(
                    FieldSensor.objects.create(plot=self.plot, name=f"Sensor {number}"),
                    self.temperature,
                ),
                20,
                minutes_ago=5,
            )
            for number in range(25)
        ]
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

        self.assertEqual(entry["bucket_seconds"], 600)
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

        for hours, expected_seconds in (
            (1, 600),
            (6, 900),
            (24, 900),
            (7 * 24, 3600),
            (30 * 24, 21600),
            (60 * 24, 86400),
        ):
            with self.subTest(hours=hours):
                entry = self.series(date_from=self.moment(hours=hours)).json()[0]

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

        with patch("sensors.utils.HISTORY_EXPORT_ROW_CAP", 2):
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

        with patch("sensors.utils.HISTORY_EXPORT_ROW_CAP", 2):
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

    def test_the_keep_flag_preserves_existing_readings_without_duplicating_them(self):
        call_command("seed_sensor_readings", days=2, verbosity=0)
        older_reading = SensorMeasurement.objects.create(
            sensor_variable=self.radiation_variable,
            value=Decimal("1"),
            recorded_at=timezone.now() - timedelta(days=10),
        )
        after_one_run = SensorMeasurement.objects.count()
        call_command("seed_sensor_readings", days=2, keep=True, verbosity=0)

        self.assertEqual(SensorMeasurement.objects.count(), after_one_run)
        self.assertTrue(SensorMeasurement.objects.filter(pk=older_reading.pk).exists())

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


class SensorIngestTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        user = get_user_model().objects.create_user(
            username="juan", email="juan@example.com", password="testpass123"
        )
        cls.user = user
        cls.farmer = Farmer.objects.create(user=user, first_name="Juan")
        other_user = get_user_model().objects.create_user(
            username="maria", email="maria@example.com", password="testpass123"
        )
        other_farmer = Farmer.objects.create(user=other_user, first_name="María")

        plot = Plot.objects.create(
            farm=Farm.objects.create(owner=cls.farmer, name="Finca El Tesoro"),
            name="Lote Norte",
        )
        other_plot = Plot.objects.create(
            farm=Farm.objects.create(owner=other_farmer, name="Finca La Montaña"),
            name="Lote Ajeno",
        )

        cls.moisture = EnvironmentalVariable.objects.create(
            name="Humedad del suelo", semantic_key=SemanticKey.SOIL_MOISTURE, unit="%"
        )
        cls.temperature = EnvironmentalVariable.objects.create(
            name="Temperatura del aire", semantic_key=SemanticKey.AIR_TEMPERATURE, unit="°C"
        )
        pressure = EnvironmentalVariable.objects.create(
            name="Presión", semantic_key=SemanticKey.OTHER, unit="hPa"
        )
        wind = EnvironmentalVariable.objects.create(
            name="Viento", semantic_key=SemanticKey.OTHER, unit="km/h"
        )

        cls.sensor = FieldSensor.objects.create(plot=plot, name="Sensor 1", serial_number="SN-1")
        cls.moisture_variable = FieldSensorVariable.objects.create(
            sensor=cls.sensor, env_variable=cls.moisture
        )
        cls.temperature_variable = FieldSensorVariable.objects.create(
            sensor=cls.sensor, env_variable=cls.temperature
        )
        FieldSensorVariable.objects.create(sensor=cls.sensor, env_variable=pressure)
        FieldSensorVariable.objects.create(sensor=cls.sensor, env_variable=wind)

        inactive_sensor = FieldSensor.objects.create(
            plot=plot, name="Sensor apagado", serial_number="SN-OFF", is_active=False
        )
        FieldSensorVariable.objects.create(sensor=inactive_sensor, env_variable=cls.moisture)
        other_sensor = FieldSensor.objects.create(
            plot=other_plot, name="Sensor ajeno", serial_number="SN-OTHER"
        )
        FieldSensorVariable.objects.create(sensor=other_sensor, env_variable=cls.moisture)

        cls.recorded_at = timezone.now().replace(microsecond=0) - timedelta(minutes=15)

    def setUp(self):
        # The throttle counts in the cache, which outlives each test's transaction.
        cache.clear()

    def payload(self, **overrides):
        body = {
            "serial_number": "SN-1",
            "recorded_at": self.recorded_at.isoformat(),
            "readings": [
                {"variable": SemanticKey.SOIL_MOISTURE, "value": 31.2},
                {"variable": SemanticKey.AIR_TEMPERATURE, "value": 24.8},
            ],
        }
        body.update(overrides)
        return body

    def ingest(self, body=None, api_key=None):
        headers = {}
        key = self.farmer.api_secret if api_key is None else api_key
        if key:
            headers["X-API-Key"] = key
        return self.client.post(
            reverse("sensors:ingest"),
            self.payload() if body is None else body,
            format="json",
            headers=headers,
        )

    def test_a_reading_is_stored_per_variable(self):
        response = self.ingest()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json(), {"created": 2, "duplicates": 0})
        self.assertEqual(
            self.moisture_variable.measurements.get().value, Decimal("31.2000")
        )
        stored = self.temperature_variable.measurements.get()
        self.assertEqual(stored.value, Decimal("24.8000"))
        self.assertEqual(stored.recorded_at, self.recorded_at)

    def test_the_stored_reading_shows_up_in_the_history(self):
        self.ingest()
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse("sensors:history-readings", args=[self.sensor.plot.farm_id]),
            {"variable": SemanticKey.SOIL_MOISTURE},
        )

        self.assertEqual([row["value"] for row in response.json()["results"]], [31.2])

    def test_a_resent_reading_is_reported_as_a_duplicate(self):
        self.ingest()
        response = self.ingest()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json(), {"created": 0, "duplicates": 2})
        self.assertEqual(SensorMeasurement.objects.count(), 2)

    def test_a_partially_resent_reading_stores_only_the_new_variable(self):
        self.ingest(self.payload(readings=[{"variable": SemanticKey.SOIL_MOISTURE, "value": 1}]))
        response = self.ingest()

        self.assertEqual(response.json(), {"created": 1, "duplicates": 1})

    def test_a_null_value_is_stored_as_a_missing_reading(self):
        response = self.ingest(
            self.payload(readings=[{"variable": SemanticKey.SOIL_MOISTURE, "value": None}])
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(self.moisture_variable.measurements.get().value)

    def test_the_ingest_costs_a_fixed_number_of_queries(self):
        # api key lookup, sensor, last seen stamp, sensor variables, already stored, insert
        with self.assertNumQueries(6):
            self.ingest()

    def test_an_accepted_reading_stamps_the_sensor_as_seen(self):
        before = timezone.now()

        self.ingest()

        self.sensor.refresh_from_db()
        self.assertGreaterEqual(self.sensor.last_seen_at, before)

    def test_a_misconfigured_payload_still_stamps_the_sensor_as_seen(self):
        self.ingest(self.payload(readings=[{"variable": SemanticKey.SOLAR_RADIATION, "value": 1}]))

        self.sensor.refresh_from_db()
        self.assertIsNotNone(self.sensor.last_seen_at)

    def test_a_rejected_request_is_logged_without_the_api_key(self):
        with self.assertLogs("sensors.api", level="WARNING") as captured:
            self.ingest(self.payload(serial_number="SN-NOPE"))

        self.assertEqual(len(captured.output), 1)
        self.assertIn("status=404", captured.output[0])
        self.assertIn(f"farmer={self.farmer.pk}", captured.output[0])
        self.assertIn("serial=SN-NOPE", captured.output[0])
        self.assertNotIn(self.farmer.api_secret, captured.output[0])

    def test_an_invalid_api_key_is_logged_without_echoing_it(self):
        with self.assertLogs("sensors.api", level="WARNING") as captured:
            self.ingest(api_key="smv_leaked-guess")

        self.assertIn("status=401", captured.output[0])
        self.assertNotIn("smv_leaked-guess", captured.output[0])

    def test_a_missing_api_key_is_unauthorized(self):
        response = self.ingest(api_key="")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response["WWW-Authenticate"], "X-API-Key")

    def test_an_unknown_api_key_is_unauthorized(self):
        response = self.ingest(api_key="smv_not-a-real-key")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_a_jwt_session_cannot_ingest(self):
        self.client.force_authenticate(user=self.user)

        response = self.ingest(api_key="")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(SensorMeasurement.objects.exists())

    def test_an_inactive_farmer_is_forbidden(self):
        Farmer.objects.filter(pk=self.farmer.pk).update(is_active=False)

        response = self.ingest()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_an_inactive_user_is_forbidden(self):
        get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)

        response = self.ingest()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_an_inactive_sensor_is_forbidden(self):
        response = self.ingest(self.payload(serial_number="SN-OFF"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(SensorMeasurement.objects.exists())

    def test_an_unknown_serial_is_not_found(self):
        response = self.ingest(self.payload(serial_number="SN-NOPE"))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_another_farmers_serial_is_indistinguishable_from_an_unknown_one(self):
        unknown = self.ingest(self.payload(serial_number="SN-NOPE"))
        foreign = self.ingest(self.payload(serial_number="SN-OTHER"))

        self.assertEqual(foreign.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(foreign.json(), unknown.json())
        self.assertFalse(SensorMeasurement.objects.exists())

    def test_a_variable_the_sensor_does_not_measure_is_rejected_whole(self):
        response = self.ingest(
            self.payload(
                readings=[
                    {"variable": SemanticKey.SOIL_MOISTURE, "value": 30},
                    {"variable": SemanticKey.SOLAR_RADIATION, "value": 500},
                ]
            )
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("readings", response.json())
        self.assertFalse(SensorMeasurement.objects.exists())

    def test_an_ambiguous_other_variable_is_rejected(self):
        response = self.ingest(
            self.payload(readings=[{"variable": SemanticKey.OTHER, "value": 1010}])
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("more than one", response.json()["readings"][0])

    def test_a_repeated_variable_is_rejected(self):
        response = self.ingest(
            self.payload(
                readings=[
                    {"variable": SemanticKey.SOIL_MOISTURE, "value": 30},
                    {"variable": SemanticKey.SOIL_MOISTURE, "value": 31},
                ]
            )
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("readings", response.json())

    def test_an_unknown_variable_key_is_rejected(self):
        response = self.ingest(self.payload(readings=[{"variable": "wind_speed", "value": 3}]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_readings_are_rejected(self):
        response = self.ingest(self.payload(readings=[]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("readings", response.json())

    def test_a_timestamp_without_offset_is_rejected(self):
        response = self.ingest(self.payload(recorded_at="2026-09-29T14:30:00"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("recorded_at", response.json())

    def test_a_timestamp_in_the_future_is_rejected(self):
        future = timezone.now() + timedelta(minutes=10)

        response = self.ingest(self.payload(recorded_at=future.isoformat()))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("recorded_at", response.json())

    def test_a_slightly_fast_device_clock_is_tolerated(self):
        ahead = timezone.now() + timedelta(minutes=2)

        response = self.ingest(self.payload(recorded_at=ahead.isoformat()))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_a_value_beyond_the_stored_precision_is_rejected(self):
        response = self.ingest(
            self.payload(readings=[{"variable": SemanticKey.SOIL_MOISTURE, "value": "1.23456"}])
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requests_past_the_rate_are_throttled(self):
        with patch.object(ApiKeyRateThrottle, "THROTTLE_RATES", {"sensor_ingest": "2/min"}):
            self.ingest()
            self.ingest()
            response = self.ingest()

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class SensorIngestConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = get_user_model().objects.create_user(
            username="juan", email="juan@example.com", password="testpass123"
        )
        farmer = Farmer.objects.create(user=user, first_name="Juan")
        cls.plot = Plot.objects.create(
            farm=Farm.objects.create(owner=farmer, name="Finca El Tesoro"), name="Lote Norte"
        )

    def test_serial_numbers_are_unique_across_farms(self):
        FieldSensor.objects.create(plot=self.plot, name="Sensor 1", serial_number="SN-1")

        with self.assertRaises(IntegrityError):
            FieldSensor.objects.create(plot=self.plot, name="Sensor 2", serial_number="SN-1")

    def test_many_sensors_may_leave_the_serial_blank(self):
        FieldSensor.objects.create(plot=self.plot, name="Sensor 1")
        FieldSensor.objects.create(plot=self.plot, name="Sensor 2")

        self.assertEqual(FieldSensor.objects.filter(serial_number="").count(), 2)


class ReadingLabelTests(SimpleTestCase):
    recorded_at = datetime(2026, 10, 7, 15, 30, tzinfo=UTC)

    def test_snapshot_label_shows_the_active_time_zone(self):
        snapshot = WeatherSnapshot(
            station=WeatherStation(name="Estación Unillanos"), recorded_at=self.recorded_at
        )

        with timezone.override("America/Bogota"):
            self.assertEqual(str(snapshot), "Estación Unillanos — 2026-10-07 10:30")

    def test_measurement_label_shows_the_active_time_zone(self):
        variable = EnvironmentalVariable(name="Temperatura del aire", unit="°C")
        measurement = SensorMeasurement(
            sensor_variable=FieldSensorVariable(env_variable=variable),
            value=Decimal("27.83"),
            recorded_at=self.recorded_at,
        )

        with timezone.override("America/Bogota"):
            self.assertEqual(str(measurement), "Temperatura del aire: 27.83 °C @ 2026-10-07 10:30")


class FieldSensorListTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="juan", email="juan@example.com", password="testpass123"
        )
        farmer = Farmer.objects.create(user=cls.user, first_name="Juan")
        other_user = get_user_model().objects.create_user(
            username="maria", email="maria@example.com", password="testpass123"
        )
        other_farmer = Farmer.objects.create(user=other_user, first_name="María")

        cls.farm = Farm.objects.create(owner=farmer, name="Finca El Tesoro")
        second_farm = Farm.objects.create(owner=farmer, name="Finca San Vicente")
        cls.other_farm = Farm.objects.create(owner=other_farmer, name="Finca La Montaña")
        north = Plot.objects.create(farm=cls.farm, name="Lote Norte")
        south = Plot.objects.create(farm=cls.farm, name="Lote Sur")

        moisture = EnvironmentalVariable.objects.create(
            name="Humedad del suelo", semantic_key=SemanticKey.SOIL_MOISTURE, unit="%"
        )
        temperature = EnvironmentalVariable.objects.create(
            name="Temperatura del aire", semantic_key=SemanticKey.AIR_TEMPERATURE, unit="°C"
        )

        now = timezone.now()
        cls.online = FieldSensor.objects.create(
            plot=north, name="B online", serial_number="SN-ON", last_seen_at=now
        )
        FieldSensorVariable.objects.create(sensor=cls.online, env_variable=temperature)
        FieldSensorVariable.objects.create(sensor=cls.online, env_variable=moisture)
        cls.offline = FieldSensor.objects.create(
            plot=north,
            name="A offline",
            serial_number="SN-OFF",
            last_seen_at=now - timedelta(minutes=46),
        )
        cls.never_seen = FieldSensor.objects.create(plot=south, name="C nuevo")
        cls.inactive = FieldSensor.objects.create(
            plot=south, name="D apagado", is_active=False, last_seen_at=now
        )
        FieldSensor.objects.create(
            plot=Plot.objects.create(farm=second_farm, name="Lote Vecino"), name="Otra finca"
        )

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def list_sensors(self, farm=None):
        return self.client.get(reverse("sensors:farm-sensors", args=[(farm or self.farm).pk]))

    def test_it_lists_the_farms_sensors_by_plot_then_name(self):
        response = self.list_sensors()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [sensor["name"] for sensor in response.json()],
            ["A offline", "B online", "C nuevo", "D apagado"],
        )

    def test_each_sensor_carries_what_its_owner_needs_to_configure_it(self):
        sensor = next(row for row in self.list_sensors().json() if row["id"] == self.online.pk)

        self.assertEqual(sensor["serial_number"], "SN-ON")
        self.assertEqual(sensor["plot_name"], "Lote Norte")
        self.assertEqual(
            [variable["semantic_key"] for variable in sensor["variables"]],
            [SemanticKey.SOIL_MOISTURE, SemanticKey.AIR_TEMPERATURE],
        )
        self.assertEqual(sensor["variables"][0]["unit"], "%")

    def test_the_status_reflects_activity_and_the_offline_threshold(self):
        statuses = {row["id"]: row["status"] for row in self.list_sensors().json()}

        self.assertEqual(statuses[self.online.pk], "online")
        self.assertEqual(statuses[self.offline.pk], "offline")
        self.assertEqual(statuses[self.never_seen.pk], "never_seen")
        self.assertEqual(statuses[self.inactive.pk], "inactive")

    def test_the_list_costs_a_fixed_number_of_queries(self):
        # farm ownership, sensors with their plot, prefetched variables
        with self.assertNumQueries(3):
            self.list_sensors()

    def test_another_farmers_farm_is_not_found(self):
        response = self.list_sensors(self.other_farm)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_it_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.list_sensors()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SensorIngestSchemaTests(APITestCase):
    def ingest_operation(self):
        response = self.client.get(reverse("schema"), HTTP_ACCEPT="application/json")
        return response.json()["paths"]["/api/sensors/ingest/"]["post"]

    def test_every_documented_outcome_has_a_response(self):
        self.assertEqual(
            sorted(self.ingest_operation()["responses"]),
            ["201", "400", "401", "403", "404", "429"],
        )

    def test_it_is_documented_as_an_api_key_endpoint(self):
        self.assertEqual(self.ingest_operation()["security"], [{"ApiKeyAuth": []}])

    def test_the_description_quotes_the_live_limits(self):
        description = self.ingest_operation()["description"]

        rate = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["sensor_ingest"]
        offline_minutes = int(SENSOR_OFFLINE_AFTER.total_seconds() // 60)
        skew_minutes = int(INGEST_MAX_CLOCK_SKEW.total_seconds() // 60)
        self.assertIn(rate, description)
        self.assertIn(f"{offline_minutes} minutes without", description)
        self.assertIn(f"{skew_minutes} minutes ahead", description)


def v2_probes():
    """The `decoded_payload.sensors` the v2 uplink formatter emits for one node."""
    return [
        {"id": 101, "readings": {"air_temperature": 22.98, "relative_humidity": 89.79}},
        {"id": 102, "readings": {"leaf_temperature": 22.33, "air_temperature": 22.96}},
        {"id": 103, "readings": {"air_temperature": 22.85}},
        {"id": 104, "readings": {"co2": 507}},
        {"id": 105, "readings": {"soil_water_tension": 12.1}},
        {"id": 106, "readings": {"soil_water_tension": 17.9}},
        {"id": 107, "readings": {"soil_water_tension": 10.1}},
        {"id": 108, "readings": {"soil_temperature": 24.48}},
        {
            "id": 109,
            "readings": {
                "battery_voltage": 3.994,
                "battery_current": -44,
                "solar_panel_voltage": 0.166,
                "solar_panel_current": 0,
            },
        },
    ]


def ttn_uplink(received_at="2026-10-06T01:11:57.218983595Z", f_port=3, decoded_payload=None):
    """An `ApplicationUp` as TTN publishes it on `v3/<app>@ttn/devices/<device>/up`."""
    if decoded_payload is None:
        decoded_payload = {"sensors": v2_probes(), "delta_t_hoja_aire": -0.65}
    uplink_message = {
        "f_port": f_port,
        "f_cnt": 1,
        "frm_payload": "AGU=",
        "received_at": received_at,
    }
    if decoded_payload is not False:
        uplink_message["decoded_payload"] = decoded_payload
    return {
        "end_device_ids": {
            "device_id": "nodo-unillanos-id0",
            "application_ids": {"application_id": "agriculture-unillanos"},
            "dev_eui": "A8404143F184DECA",
        },
        "received_at": received_at,
        "uplink_message": uplink_message,
    }


class ParseTtnUplinkTests(SimpleTestCase):
    def test_every_probe_becomes_a_reading_of_its_serial(self):
        readings = parse_ttn_uplink(ttn_uplink())

        self.assertEqual(
            [reading["serial_number"] for reading in readings],
            ["101", "102", "103", "104", "105", "106", "107", "108", "109"],
        )
        self.assertEqual(
            readings[0]["readings"],
            [
                {"variable": "air_temperature", "value": 22.98},
                {"variable": "relative_humidity", "value": 89.79},
            ],
        )
        self.assertEqual(
            readings[8]["readings"],
            [
                {"variable": "battery_voltage", "value": 3.994},
                {"variable": "battery_current", "value": -44},
                {"variable": "solar_panel_voltage", "value": 0.166},
                {"variable": "solar_panel_current", "value": 0},
            ],
        )

    def test_recorded_at_is_the_reception_time_truncated_to_the_second(self):
        readings = parse_ttn_uplink(ttn_uplink())

        expected = datetime(2026, 10, 6, 1, 11, 57, tzinfo=UTC)
        self.assertEqual({reading["recorded_at"] for reading in readings}, {expected})

    def test_the_console_forward_envelope_is_unwrapped(self):
        envelope = {
            "name": "as.up.data.forward",
            "time": "2026-10-06T01:11:57.424840381Z",
            "data": {"@type": "type.googleapis.com/ttn.lorawan.v3.ApplicationUp", **ttn_uplink()},
        }

        self.assertEqual(parse_ttn_uplink(envelope), parse_ttn_uplink(ttn_uplink()))

    def test_values_are_rounded_to_the_stored_precision(self):
        payload = {"sensors": [{"id": 101, "readings": {"air_temperature": 22.849999999999998}}]}

        readings = parse_ttn_uplink(ttn_uplink(decoded_payload=payload))

        self.assertEqual(readings[0]["readings"][0]["value"], 22.85)

    def test_rejects_the_v1_payload_port(self):
        with self.assertRaisesMessage(LoRaPayloadError, "Unexpected fPort 2"):
            parse_ttn_uplink(ttn_uplink(f_port=2))

    def test_rejects_an_uplink_the_formatter_could_not_decode(self):
        payload = {"errors": ["Payload inesperado (fPort 3, 30 bytes)"]}

        with self.assertRaisesMessage(LoRaPayloadError, "formatter reported errors"):
            parse_ttn_uplink(ttn_uplink(decoded_payload=payload))

    def test_rejects_decode_errors_reported_next_to_the_payload(self):
        message = ttn_uplink()
        message["uplink_message"]["decode_errors"] = ["boom"]

        with self.assertRaisesMessage(LoRaPayloadError, "formatter reported errors"):
            parse_ttn_uplink(message)

    def test_rejects_an_uplink_without_decoded_payload(self):
        with self.assertRaisesMessage(LoRaPayloadError, "no decoded_payload"):
            parse_ttn_uplink(ttn_uplink(decoded_payload=False))

    def test_rejects_a_non_numeric_value(self):
        payload = {"sensors": [{"id": 101, "readings": {"air_temperature": "22.9"}}]}

        with self.assertRaisesMessage(LoRaPayloadError, "non-numeric"):
            parse_ttn_uplink(ttn_uplink(decoded_payload=payload))

    def test_rejects_malformed_messages(self):
        cases = {
            "not an object": [],
            "no uplink": {"end_device_ids": {}},
            "no sensors": ttn_uplink(decoded_payload={"sensors": []}),
            "bad probe id": ttn_uplink(
                decoded_payload={"sensors": [{"id": "101", "readings": {"co2": 1}}]}
            ),
            "probe without readings": ttn_uplink(
                decoded_payload={"sensors": [{"id": 101, "readings": {}}]}
            ),
            "bad timestamp": ttn_uplink(received_at="yesterday"),
        }
        for label, message in cases.items():
            with self.subTest(label), self.assertRaises(LoRaPayloadError):
                parse_ttn_uplink(message)


class HandleUplinkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = get_user_model().objects.create_user(
            username="juan", email="juan@example.com", password="testpass123"
        )
        farmer = Farmer.objects.create(user=user, first_name="Juan")
        plot = Plot.objects.create(
            farm=Farm.objects.create(owner=farmer, name="Finca El Tesoro"), name="Lote Norte"
        )
        variables = {
            key: EnvironmentalVariable.objects.create(name=key, semantic_key=key, unit="")
            for key in (
                SemanticKey.AIR_TEMPERATURE,
                SemanticKey.RELATIVE_HUMIDITY,
                SemanticKey.CO2,
            )
        }
        cls.air_sensor = FieldSensor.objects.create(
            plot=plot, name="Sonda de aire", serial_number="101"
        )
        for key in (SemanticKey.AIR_TEMPERATURE, SemanticKey.RELATIVE_HUMIDITY):
            FieldSensorVariable.objects.create(sensor=cls.air_sensor, env_variable=variables[key])
        cls.co2_sensor = FieldSensor.objects.create(
            plot=plot, name="Sonda de CO2", serial_number="104", is_active=False
        )
        FieldSensorVariable.objects.create(
            sensor=cls.co2_sensor, env_variable=variables[SemanticKey.CO2]
        )
        cls.received_at = timezone.now().replace(microsecond=0) - timedelta(minutes=1)

    def uplink(self, probes):
        timestamp = self.received_at.isoformat().replace("+00:00", ".123456789Z")
        return ttn_uplink(received_at=timestamp, decoded_payload={"sensors": probes})

    def air_probe(self, temperature=22.98):
        return {"id": 101, "readings": {"air_temperature": temperature, "relative_humidity": 89.79}}

    def test_stores_each_probe_under_its_sensor(self):
        with self.assertLogs("sensors.mqtt", "INFO"):
            outcome = handle_uplink(self.uplink([self.air_probe()]))

        self.assertEqual(outcome, {"stored": 1, "rejected": 0})
        stored = SensorMeasurement.objects.filter(sensor_variable__sensor=self.air_sensor)
        self.assertEqual(
            {
                (row.sensor_variable.env_variable.semantic_key, row.value, row.recorded_at)
                for row in stored
            },
            {
                ("air_temperature", Decimal("22.9800"), self.received_at),
                ("relative_humidity", Decimal("89.7900"), self.received_at),
            },
        )

    def test_a_redelivered_uplink_is_stored_once(self):
        with self.assertLogs("sensors.mqtt", "INFO") as logs:
            handle_uplink(self.uplink([self.air_probe()]))
            handle_uplink(self.uplink([self.air_probe()]))

        self.assertEqual(SensorMeasurement.objects.count(), 2)
        self.assertIn("created=0 duplicates=2", logs.output[-1])

    def test_stamps_the_sensor_as_seen(self):
        with self.assertLogs("sensors.mqtt", "INFO"):
            handle_uplink(self.uplink([self.air_probe()]))

        self.air_sensor.refresh_from_db()
        self.assertAlmostEqual(
            self.air_sensor.last_seen_at, timezone.now(), delta=timedelta(seconds=10)
        )

    def test_unknown_and_inactive_probes_are_logged_without_stopping_the_rest(self):
        probes = [
            {"id": 999, "readings": {"co2": 500}},
            {"id": 104, "readings": {"co2": 500}},
            self.air_probe(),
        ]

        with self.assertLogs("sensors.mqtt", "INFO") as logs:
            outcome = handle_uplink(self.uplink(probes))

        self.assertEqual(outcome, {"stored": 1, "rejected": 2})
        self.assertEqual(
            SensorMeasurement.objects.filter(sensor_variable__sensor=self.air_sensor).count(), 2
        )
        warnings = [line for line in logs.output if line.startswith("WARNING")]
        self.assertEqual(len(warnings), 2)
        self.assertIn("dev_eui=A8404143F184DECA", warnings[0])
        self.assertIn("device_id=nodo-unillanos-id0", warnings[0])
        self.assertIn("serial=999", warnings[0])
        self.assertIn("Unknown sensor", warnings[0])
        self.assertIn("serial=104", warnings[1])
        self.assertIn("inactive", warnings[1])

    def test_a_variable_the_sensor_does_not_measure_is_logged(self):
        probe = {"id": 101, "readings": {"soil_temperature": 24.5}}

        with self.assertLogs("sensors.mqtt", "WARNING") as logs:
            outcome = handle_uplink(self.uplink([probe]))

        self.assertEqual(outcome, {"stored": 0, "rejected": 1})
        self.assertIn("does not measure 'soil_temperature'", logs.output[0])
        self.assertFalse(SensorMeasurement.objects.exists())

    def test_an_unparseable_uplink_is_logged_and_never_raised(self):
        with self.assertLogs("sensors.mqtt", "WARNING") as logs:
            outcome = handle_uplink(ttn_uplink(f_port=2))

        self.assertEqual(outcome, {"stored": 0, "rejected": 1})
        self.assertIn("Unexpected fPort 2", logs.output[0])

    def test_an_unexpected_error_in_one_probe_does_not_stop_the_rest(self):
        probes = [{"id": 104, "readings": {"co2": 500}}, self.air_probe()]
        original_store_probe = lorawan.store_probe

        def failing_once(probe):
            if probe["serial_number"] == "104":
                raise RuntimeError("database hiccup")
            return original_store_probe(probe)

        with (
            patch("sensors.lorawan.store_probe", side_effect=failing_once),
            self.assertLogs("sensors.mqtt", "INFO") as logs,
        ):
            outcome = handle_uplink(self.uplink(probes))

        self.assertEqual(outcome, {"stored": 1, "rejected": 1})
        self.assertIn("database hiccup", "\n".join(logs.output))


class ResolveSensorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = get_user_model().objects.create_user(
            username="juan", email="juan@example.com", password="testpass123"
        )
        cls.farmer = Farmer.objects.create(user=user, first_name="Juan")
        other_user = get_user_model().objects.create_user(
            username="maria", email="maria@example.com", password="testpass123"
        )
        other_farmer = Farmer.objects.create(user=other_user, first_name="María")
        other_plot = Plot.objects.create(
            farm=Farm.objects.create(owner=other_farmer, name="Finca La Montaña"),
            name="Lote Ajeno",
        )
        cls.other_sensor = FieldSensor.objects.create(
            plot=other_plot, name="Sensor ajeno", serial_number="SN-OTHER"
        )
        FieldSensor.objects.create(plot=other_plot, name="Sin serial")

    def test_without_a_farmer_the_lookup_is_global(self):
        self.assertEqual(resolve_sensor("SN-OTHER"), self.other_sensor)

    def test_with_a_farmer_another_owner_serial_is_unknown(self):
        with self.assertRaises(exceptions.NotFound):
            resolve_sensor("SN-OTHER", self.farmer)

    def test_a_blank_serial_never_matches_an_unregistered_sensor(self):
        with self.assertRaises(exceptions.NotFound):
            resolve_sensor("")


@override_settings(MQTT_SOURCE="local", MQTT_INGEST=mqtt_ingest_config("local", {}))
class MqttIngestCommandTests(TestCase):
    TTN_CONFIG = mqtt_ingest_config(
        "ttn", {"TTN_APP_ID": "agriculture-unillanos", "TTN_API_KEY": "NNSXS.secret"}
    )

    @classmethod
    def setUpTestData(cls):
        user = get_user_model().objects.create_user(
            username="juan", email="juan@example.com", password="testpass123"
        )
        farmer = Farmer.objects.create(user=user, first_name="Juan")
        plot = Plot.objects.create(
            farm=Farm.objects.create(owner=farmer, name="Finca El Tesoro"), name="Lote Norte"
        )
        sensor = FieldSensor.objects.create(plot=plot, name="Sonda CO2", serial_number="104")
        FieldSensorVariable.objects.create(
            sensor=sensor,
            env_variable=EnvironmentalVariable.objects.create(
                name="CO2", semantic_key=SemanticKey.CO2, unit="ppm"
            ),
        )

    def run_command(self):
        """Run the command against a fake paho client and return that client."""
        with (
            patch("sensors.management.commands.mqtt_ingest.mqtt.Client") as client_class,
            patch.object(mqtt_ingest.Command, "configure_logging"),
        ):
            call_command("mqtt_ingest", stdout=io.StringIO())
        return client_class.return_value

    def deliver(self, client, message):
        """Feed `message` to the client's `on_message`, as paho would on a delivery."""
        # Closing "old" connections inside the test transaction would close the test's own.
        with patch(
            "sensors.management.commands.mqtt_ingest.close_old_connections"
        ) as close_old_connections:
            client.on_message(client, settings.MQTT_INGEST, message)
        return close_old_connections

    def test_local_profile_connects_to_the_compose_mosquitto_in_the_clear(self):
        client = self.run_command()

        client.connect_async.assert_called_once_with("mqtt", 1883, keepalive=60)
        client.tls_set.assert_not_called()
        client.username_pw_set.assert_not_called()
        client.loop_forever.assert_called_once_with(retry_first_connection=True)

    def test_ttn_profile_uses_tls_and_the_application_credentials(self):
        with self.settings(MQTT_SOURCE="ttn", MQTT_INGEST=self.TTN_CONFIG):
            client = self.run_command()

        client.connect_async.assert_called_once_with(
            "au1.cloud.thethings.network", 8883, keepalive=60
        )
        client.tls_set.assert_called_once_with()
        client.username_pw_set.assert_called_once_with(
            "agriculture-unillanos@ttn", "NNSXS.secret"
        )

    def test_subscribes_with_qos_1_on_every_connection(self):
        with self.settings(MQTT_SOURCE="ttn", MQTT_INGEST=self.TTN_CONFIG):
            client = self.run_command()
        reason_code = MagicMock(is_failure=False)

        with self.assertLogs("sensors.mqtt", "INFO") as logs:
            client.on_connect(client, self.TTN_CONFIG, {}, reason_code, None)

        client.subscribe.assert_called_once_with(
            "v3/agriculture-unillanos@ttn/devices/+/up", qos=1
        )
        self.assertIn("source=ttn", logs.output[0])
        self.assertNotIn("NNSXS", "\n".join(logs.output))

    def test_on_message_stores_the_uplink(self):
        client = self.run_command()
        received_at = timezone.now().replace(microsecond=0) - timedelta(minutes=1)
        uplink = ttn_uplink(
            received_at=received_at.isoformat().replace("+00:00", "Z"),
            decoded_payload={"sensors": [{"id": 104, "readings": {"co2": 507}}]},
        )
        message = MagicMock(topic="v3/app@ttn/devices/node/up", payload=json.dumps(uplink).encode())

        with self.assertLogs("sensors.mqtt", "INFO"):
            close_old_connections = self.deliver(client, message)

        close_old_connections.assert_called_once_with()
        stored = SensorMeasurement.objects.get()
        self.assertEqual(stored.value, Decimal("507.0000"))
        self.assertEqual(stored.recorded_at, received_at)

    def test_on_message_logs_a_payload_that_is_not_json(self):
        client = self.run_command()
        message = MagicMock(topic="v3/app@ttn/devices/node/up", payload=b"\x00\x01")

        with self.assertLogs("sensors.mqtt", "WARNING") as logs:
            self.deliver(client, message)

        self.assertIn("not JSON", logs.output[0])
        self.assertFalse(SensorMeasurement.objects.exists())

    def test_on_message_never_raises_out_of_the_loop(self):
        client = self.run_command()
        message = MagicMock(topic="t", payload=b"{}")

        with (
            patch(
                "sensors.management.commands.mqtt_ingest.handle_uplink",
                side_effect=RuntimeError("boom"),
            ),
            self.assertLogs("sensors.mqtt", "ERROR"),
        ):
            self.deliver(client, message)

    def test_an_unknown_source_is_refused(self):
        with self.settings(MQTT_SOURCE="chirpstack"), self.assertRaises(CommandError):
            self.run_command()

    def test_ttn_without_an_api_key_is_refused(self):
        config = mqtt_ingest_config("ttn", {"TTN_APP_ID": "agriculture-unillanos"})

        with (
            self.settings(MQTT_SOURCE="ttn", MQTT_INGEST=config),
            self.assertRaisesMessage(CommandError, "TTN_API_KEY"),
        ):
            self.run_command()


class MqttIngestSettingsTests(SimpleTestCase):
    def test_local_is_the_default_source(self):
        self.assertEqual(mqtt_source({}), "local")
        self.assertEqual(mqtt_source({"MQTT_SOURCE": " TTN "}), "ttn")

    def test_local_profile_points_at_the_compose_mosquitto(self):
        config = mqtt_ingest_config("local", {})

        self.assertEqual((config["host"], config["port"], config["tls"]), ("mqtt", 1883, False))
        self.assertEqual(config["topic"], "v3/+/devices/+/up")

    def test_ttn_profile_derives_user_and_topic_from_the_application_id(self):
        config = mqtt_ingest_config(
            "ttn", {"TTN_APP_ID": "agriculture-unillanos", "TTN_API_KEY": "NNSXS.key"}
        )

        self.assertEqual(
            (config["host"], config["port"], config["tls"]),
            ("au1.cloud.thethings.network", 8883, True),
        )
        self.assertEqual(config["username"], "agriculture-unillanos@ttn")
        self.assertEqual(config["password"], "NNSXS.key")
        self.assertEqual(config["topic"], "v3/agriculture-unillanos@ttn/devices/+/up")

    def test_ttn_application_id_pasted_with_the_tenant_suffix_is_not_doubled(self):
        config = mqtt_ingest_config(
            "ttn", {"TTN_APP_ID": " agriculture-unillanos@ttn ", "TTN_API_KEY": "NNSXS.key"}
        )

        self.assertEqual(config["username"], "agriculture-unillanos@ttn")
        self.assertEqual(config["topic"], "v3/agriculture-unillanos@ttn/devices/+/up")


class LoraDemoSeedTests(TestCase):
    """`make loaddata` must leave the simulator's probes registered, and its uplink storable."""

    fixtures = [
        "initial_users.json",
        "initial_farmers.json",
        "initial_farms_with_plots.json",
        "initial_sensors.json",
        "lora_demo_sensors.json",
    ]

    EXPECTED_KEYS = {
        "101": {"air_temperature", "relative_humidity"},
        "102": {"leaf_temperature", "air_temperature"},
        "103": {"air_temperature"},
        "104": {"co2"},
        "105": {"soil_water_tension"},
        "106": {"soil_water_tension"},
        "107": {"soil_water_tension"},
        "108": {"soil_temperature"},
        "109": {
            "battery_voltage",
            "battery_current",
            "solar_panel_voltage",
            "solar_panel_current",
        },
    }

    def test_every_probe_is_registered_with_the_variables_it_sends(self):
        sensors = FieldSensor.objects.filter(serial_number__in=self.EXPECTED_KEYS)

        self.assertEqual(
            {
                sensor.serial_number: set(
                    sensor.sensor_variables.values_list("env_variable__semantic_key", flat=True)
                )
                for sensor in sensors
            },
            self.EXPECTED_KEYS,
        )

    def test_every_semantic_key_has_an_environmental_variable(self):
        seeded_keys = set(EnvironmentalVariable.objects.values_list("semantic_key", flat=True))

        self.assertLessEqual(set(SemanticKey.values), seeded_keys)

    def test_the_simulator_uplink_is_stored_for_every_probe(self):
        simulator = load_simulator()
        now = timezone.now().replace(microsecond=0)
        payload = simulator.encode(simulator.node_values(now, random.Random(7)))
        message = simulator.application_up(payload, f_cnt=1, received_at=now)

        with self.assertLogs("sensors.mqtt", "INFO"):
            outcome = handle_uplink(json.loads(json.dumps(message)))

        self.assertEqual(len(payload), 46)
        self.assertEqual(outcome, {"stored": 9, "rejected": 0})
        self.assertEqual(SensorMeasurement.objects.filter(recorded_at=now).count(), 14)


def load_simulator():
    path = Path(settings.BASE_DIR) / "scripts" / "simulate_lora_node.py"
    spec = importlib.util.spec_from_file_location("simulate_lora_node", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WEATHERLINK_CURRENT_RESPONSE = {
    "station_id": 121402,
    "sensors": [
        {"lsid": 453154, "data": [{"temp_in": 79, "hum_in": 46.5, "dew_point_in": 56.8}]},
        {
            "lsid": 453155,
            "data": [{"temp": 83.3, "hum": 77.1, "solar_rad": 346, "dew_point": 75.4}],
        },
        {"lsid": 453152, "data": [{"battery_voltage": 94, "wifi_rssi": None}]},
    ],
}


class WeatherLinkUnitConversionTests(SimpleTestCase):
    def test_fahrenheit_is_converted_to_celsius(self):
        self.assertEqual(fahrenheit_to_celsius(32), 0)
        self.assertEqual(fahrenheit_to_celsius(212), 100)
        self.assertEqual(fahrenheit_to_celsius(83.3), 28.5)

    def test_temperature_fields_are_celsius_and_the_rest_untouched(self):
        measurements = _extract_measurements(WEATHERLINK_CURRENT_RESPONSE)

        self.assertEqual(measurements["temp"], 28.5)
        self.assertEqual(measurements["temp_in"], 26.11)
        self.assertEqual(measurements["dew_point"], 24.11)
        self.assertEqual(measurements["hum"], 77.1)
        self.assertEqual(measurements["solar_rad"], 346)
        self.assertEqual(measurements["battery_voltage"], 94)
        self.assertIsNone(measurements["wifi_rssi"])


class PollWeatherLinkStationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = get_user_model().objects.create_user(
            username="hadid", email="hadid@example.com", password="testpass123"
        )
        farmer = Farmer.objects.create(user=user, first_name="Hadid")
        farm = Farm.objects.create(owner=farmer, name="Unillanos", address="Villavicencio")
        cls.station = WeatherStation.objects.create(
            farm=farm,
            name="Estación Unillanos",
            provider="weatherlink",
            station_id="121402",
            api_key="key",
            api_secret="secret",
        )
        temperature = EnvironmentalVariable.objects.create(
            name="Temperatura del aire", semantic_key=SemanticKey.AIR_TEMPERATURE, unit="°C"
        )
        cls.temperature_variable = WeatherStationVariableConfiguration.objects.create(
            station=cls.station, env_variable=temperature, field_key="temp"
        )

    @patch("sensors.weather_station_providers.weatherlink.requests.get")
    def test_polled_temperature_is_stored_in_celsius(self, mocked_get):
        mocked_get.return_value.json.return_value = WEATHERLINK_CURRENT_RESPONSE

        poll_weather_stations()

        measurement = WeatherMeasurement.objects.get(station_variable=self.temperature_variable)
        self.assertEqual(measurement.value, Decimal("28.5"))
        snapshot = WeatherSnapshot.objects.get(station=self.station)
        self.assertEqual(snapshot.raw_json, WEATHERLINK_CURRENT_RESPONSE)


class WeatherStationTestCase(APITestCase):
    """Owner, farms, variables and snapshot helpers shared by the weather station endpoints."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="juan", email="juan@example.com", password="testpass123"
        )
        cls.farmer = Farmer.objects.create(user=cls.user, first_name="Juan")
        other_user = get_user_model().objects.create_user(
            username="maria", email="maria@example.com", password="testpass123"
        )
        other_farmer = Farmer.objects.create(user=other_user, first_name="María")

        cls.farm = Farm.objects.create(
            owner=cls.farmer, name="Finca El Tesoro", address="Vereda La Esperanza"
        )
        cls.empty_farm = Farm.objects.create(
            owner=cls.farmer, name="Finca Sin Estaciones", address="Vereda El Carmen"
        )
        cls.other_farm = Farm.objects.create(
            owner=other_farmer, name="Finca La Montaña", address="Vereda El Roble"
        )

        cls.temperature = EnvironmentalVariable.objects.create(
            name="Temperatura del aire", semantic_key=SemanticKey.AIR_TEMPERATURE, unit="°C"
        )
        cls.radiation = EnvironmentalVariable.objects.create(
            name="Radiación solar", semantic_key=SemanticKey.SOLAR_RADIATION, unit="W/m²"
        )
        cls.pressure = EnvironmentalVariable.objects.create(
            name="Presión barométrica", semantic_key=SemanticKey.OTHER, unit="hPa"
        )
        cls.now = timezone.now().replace(microsecond=0)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    @classmethod
    def make_station(cls, name="Estación Norte", farm=None, is_active=True):
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
            field_key=f"{variable.semantic_key}-{variable.pk}",
            is_active=is_active,
        )

    @classmethod
    def snapshot(cls, station, minutes_ago=0, at=None):
        snapshot, _ = WeatherSnapshot.objects.get_or_create(
            station=station, recorded_at=at or cls.now - timedelta(minutes=minutes_ago)
        )
        return snapshot

    @classmethod
    def record(cls, station_variable, value, minutes_ago=0, at=None):
        return WeatherMeasurement.objects.create(
            snapshot=cls.snapshot(station_variable.station, minutes_ago, at),
            station_variable=station_variable,
            value=None if value is None else Decimal(str(value)),
        )

    def stations(self, farm=None):
        return self.client.get(
            reverse("sensors:farm-stations", args=[(farm or self.farm).pk])
        )

    def station_get(self, name, station, **params):
        return self.client.get(reverse(f"sensors:{name}", args=[station.pk]), params)

    def wire_time(self, moment):
        return moment.isoformat().replace("+00:00", "Z")


class WeatherStationListTests(WeatherStationTestCase):
    def test_it_lists_every_station_of_the_farm_inactive_included_ordered_by_name(self):
        self.make_station("Estación Sur")
        self.make_station("Estación Apagada", is_active=False)
        self.make_station("Estación Norte")
        self.make_station("Estación Ajena", farm=self.other_farm)

        names = [station["name"] for station in self.stations().json()]

        self.assertEqual(names, ["Estación Apagada", "Estación Norte", "Estación Sur"])

    def test_stations_sharing_a_name_order_by_id(self):
        first = self.make_station("Estación")
        second = self.make_station("Estación")

        ids = [station["id"] for station in self.stations().json()]

        self.assertEqual(ids, [first.pk, second.pk])

    def test_an_item_carries_the_documented_keys(self):
        station = self.make_station()
        self.record(self.configure(station, self.temperature), "27.40", minutes_ago=3)

        item = self.stations().json()[0]

        self.assertEqual(
            set(item),
            {
                "id",
                "farm_id",
                "name",
                "provider",
                "is_active",
                "status",
                "last_reading_at",
                "latest",
                "sparkline",
            },
        )
        self.assertEqual(item["id"], station.pk)
        self.assertEqual(item["farm_id"], self.farm.pk)
        self.assertEqual(item["provider"], "weatherlink")
        self.assertTrue(item["is_active"])

    def test_a_farm_without_stations_returns_an_empty_list(self):
        response = self.stations(self.empty_farm)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_another_farmers_farm_is_404(self):
        self.make_station("Estación Ajena", farm=self.other_farm)

        response = self.stations(self.other_farm)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {"detail": "Not found."})

    def test_an_unknown_farm_is_404(self):
        response = self.client.get(reverse("sensors:farm-stations", args=[999999]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_it_requires_authentication(self):
        self.client.force_authenticate(user=None)

        self.assertEqual(self.stations().status_code, status.HTTP_401_UNAUTHORIZED)

    def test_status_covers_online_stale_never_seen_and_inactive(self):
        online = self.make_station("A online")
        self.snapshot(online, minutes_ago=3)
        almost_stale = self.make_station("B almost stale")
        self.snapshot(almost_stale, minutes_ago=29)
        stale = self.make_station("C stale")
        self.snapshot(stale, minutes_ago=31)
        self.make_station("D never seen")
        inactive = self.make_station("E inactive", is_active=False)
        self.snapshot(inactive, minutes_ago=1)
        self.make_station("F inactive never seen", is_active=False)

        statuses = {station["name"]: station["status"] for station in self.stations().json()}

        self.assertEqual(
            statuses,
            {
                "A online": "online",
                "B almost stale": "online",
                "C stale": "stale",
                "D never seen": "never_seen",
                "E inactive": "inactive",
                "F inactive never seen": "inactive",
            },
        )

    def test_the_stale_threshold_is_thirty_minutes(self):
        self.assertEqual(STATION_STALE_AFTER, timedelta(minutes=30))

    def test_last_reading_at_is_the_newest_snapshot_even_without_values(self):
        station = self.make_station()
        station_variable = self.configure(station, self.temperature)
        self.record(station_variable, "20.00", minutes_ago=40)
        newest = self.record(station_variable, None, minutes_ago=2)

        item = self.stations().json()[0]

        self.assertEqual(item["last_reading_at"], self.wire_time(newest.snapshot.recorded_at))
        self.assertEqual(item["status"], "online")

    def test_a_station_never_seen_has_no_last_reading_and_no_latest(self):
        self.configure(self.make_station(), self.temperature)

        item = self.stations().json()[0]

        self.assertIsNone(item["last_reading_at"])
        self.assertEqual(item["latest"], [])
        self.assertEqual(item["sparkline"]["points"], [])

    def test_latest_holds_the_newest_non_null_value_of_each_active_variable_by_name(self):
        station = self.make_station()
        temperature = self.configure(station, self.temperature)
        radiation = self.configure(station, self.radiation)
        self.configure(station, self.pressure)
        humidity = self.configure(
            station,
            EnvironmentalVariable.objects.create(
                name="Humedad relativa", semantic_key=SemanticKey.RELATIVE_HUMIDITY, unit="%"
            ),
            is_active=False,
        )
        self.record(temperature, "18.00", minutes_ago=60)
        kept = self.record(temperature, "27.40", minutes_ago=10)
        self.record(temperature, None, minutes_ago=2)
        self.record(radiation, "612.50", minutes_ago=2)
        self.record(humidity, "80.00", minutes_ago=2)

        latest = self.stations().json()[0]["latest"]

        self.assertEqual(
            latest,
            [
                {
                    "variable_id": self.radiation.pk,
                    "semantic_key": "solar_radiation",
                    "name": "Radiación solar",
                    "unit": "W/m²",
                    "value": 612.5,
                    "recorded_at": self.wire_time(self.now - timedelta(minutes=2)),
                },
                {
                    "variable_id": self.temperature.pk,
                    "semantic_key": "air_temperature",
                    "name": "Temperatura del aire",
                    "unit": "°C",
                    "value": 27.4,
                    "recorded_at": self.wire_time(kept.snapshot.recorded_at),
                },
            ],
        )

    def test_latest_is_computed_per_station(self):
        north = self.configure(self.make_station("Norte"), self.temperature)
        south = self.configure(self.make_station("Sur"), self.temperature)
        self.record(north, "18.00", minutes_ago=5)
        self.record(south, "25.00", minutes_ago=1)

        values = {
            station["name"]: station["latest"][0]["value"] for station in self.stations().json()
        }

        self.assertEqual(values, {"Norte": 18.0, "Sur": 25.0})

    def test_the_sparkline_holds_hourly_averages_of_air_temperature_over_a_day(self):
        station = self.make_station()
        temperature = self.configure(station, self.temperature)
        radiation = self.configure(station, self.radiation)
        hour = self.now.replace(minute=0, second=0) - timedelta(hours=2)
        self.record(temperature, "20.00", at=hour + timedelta(minutes=10))
        self.record(temperature, "22.00", at=hour + timedelta(minutes=40))
        self.record(temperature, None, at=hour + timedelta(minutes=50))
        self.record(temperature, "25.00", at=hour + timedelta(hours=1, minutes=5))
        self.record(temperature, "99.00", at=self.now - timedelta(hours=25))
        self.record(radiation, "500.00", at=hour + timedelta(minutes=10))

        sparkline = self.stations().json()[0]["sparkline"]

        self.assertEqual(
            sparkline,
            {
                "semantic_key": "air_temperature",
                "unit": "°C",
                "points": [
                    {"t": self.wire_time(hour), "value": 21.0},
                    {"t": self.wire_time(hour + timedelta(hours=1)), "value": 25.0},
                ],
            },
        )

    def test_the_sparkline_window_covers_the_whole_last_day(self):
        temperature = self.configure(self.make_station(), self.temperature)
        self.record(temperature, "19.00", at=self.now - timedelta(hours=23, minutes=59))

        points = self.stations().json()[0]["sparkline"]["points"]

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0]["value"], 19.0)

    def test_the_sparkline_is_null_without_an_active_air_temperature_variable(self):
        without = self.make_station("Sin temperatura")
        self.record(self.configure(without, self.radiation), "612.00", minutes_ago=3)
        switched_off = self.make_station("Temperatura apagada")
        self.record(
            self.configure(switched_off, self.temperature, is_active=False), "20.00", minutes_ago=3
        )

        sparklines = {
            station["name"]: station["sparkline"] for station in self.stations().json()
        }

        self.assertEqual(sparklines, {"Sin temperatura": None, "Temperatura apagada": None})

    def test_the_query_count_does_not_grow_with_stations_or_variables(self):
        first = self.make_station("Primera")
        self.record(self.configure(first, self.temperature), "20.00", minutes_ago=3)
        # Farm ownership, stations with `last_reading_at`, their active variables, the
        # latest values and the sparkline points. If this changes, a query was added — do
        # not just bump it.
        with self.assertNumQueries(5):
            self.stations()

        for index in range(3):
            station = self.make_station(f"Extra {index}", is_active=index != 0)
            for variable in (self.temperature, self.radiation, self.pressure):
                self.record(self.configure(station, variable), "10.00", minutes_ago=index + 1)

        with self.assertNumQueries(5):
            response = self.stations()

        self.assertEqual(len(response.json()), 4)

    def test_a_farm_without_stations_costs_two_queries(self):
        with self.assertNumQueries(2):
            self.stations(self.empty_farm)


class WeatherStationDetailTests(WeatherStationTestCase):
    def detail(self, station):
        return self.client.get(reverse("sensors:station-detail", args=[station.pk]))

    def test_it_returns_the_card_plus_the_active_variables_by_name(self):
        station = self.make_station()
        temperature = self.configure(station, self.temperature)
        self.configure(station, self.pressure)
        self.configure(station, self.radiation, is_active=False)
        self.record(temperature, "27.40", minutes_ago=3)

        payload = self.detail(station).json()

        self.assertEqual(payload["id"], station.pk)
        self.assertEqual(payload["status"], "online")
        self.assertEqual(payload["latest"][0]["value"], 27.4)
        self.assertEqual(payload["sparkline"]["semantic_key"], "air_temperature")
        self.assertEqual(
            payload["variables"],
            [
                {
                    "variable_id": self.pressure.pk,
                    "semantic_key": "other",
                    "name": "Presión barométrica",
                    "unit": "hPa",
                },
                {
                    "variable_id": self.temperature.pk,
                    "semantic_key": "air_temperature",
                    "name": "Temperatura del aire",
                    "unit": "°C",
                },
            ],
        )

    def test_an_inactive_station_is_still_readable(self):
        station = self.make_station(is_active=False)

        payload = self.detail(station).json()

        self.assertEqual(payload["status"], "inactive")
        self.assertEqual(payload["variables"], [])

    def test_another_farmers_station_is_404(self):
        station = self.make_station(farm=self.other_farm)

        response = self.detail(station)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {"detail": "Not found."})

    def test_an_unknown_station_is_404(self):
        response = self.client.get(reverse("sensors:station-detail", args=[999999]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_it_requires_authentication(self):
        station = self.make_station()
        self.client.force_authenticate(user=None)

        self.assertEqual(self.detail(station).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_it_costs_four_queries(self):
        station = self.make_station()
        for variable in (self.temperature, self.radiation, self.pressure):
            self.record(self.configure(station, variable), "10.00", minutes_ago=3)

        # Owned station with `last_reading_at`, its active variables, the latest values and
        # the sparkline points.
        with self.assertNumQueries(4):
            self.detail(station)


class WeatherStationSeriesTests(WeatherStationTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.station = cls.make_station()
        cls.temperature_variable = cls.configure(cls.station, cls.temperature)
        cls.radiation_variable = cls.configure(cls.station, cls.radiation)

    def series(self, **params):
        return self.station_get("station-series", self.station, **params)

    def test_it_matches_the_history_series_shape_with_one_series_per_variable(self):
        self.record(self.temperature_variable, "21.00", minutes_ago=5)
        self.record(self.radiation_variable, "600.00", minutes_ago=5)

        payload = self.series().json()

        self.assertEqual([series["name"] for series in payload], ["Radiación solar", "Temperatura del aire"])
        self.assertEqual(
            set(payload[0]),
            {"variable_id", "semantic_key", "name", "unit", "bucket_seconds", "points"},
        )
        self.assertEqual(set(payload[0]["points"][0]), {"t", "value", "sample_count"})
        self.assertEqual(payload[1]["variable_id"], self.temperature.pk)
        self.assertEqual(payload[1]["unit"], "°C")

    def test_readings_in_one_bucket_average_from_the_range_start(self):
        date_from = self.now - timedelta(days=1)
        self.record(self.temperature_variable, "20.00", at=date_from + timedelta(minutes=1))
        self.record(self.temperature_variable, "22.00", at=date_from + timedelta(minutes=14))
        self.record(self.temperature_variable, "30.00", at=date_from + timedelta(minutes=16))

        payload = self.series(
            date_from=date_from.isoformat(), date_to=self.now.isoformat()
        ).json()

        series = payload[0]
        self.assertEqual(series["bucket_seconds"], 900)
        self.assertEqual(
            series["points"],
            [
                {"t": self.wire_time(date_from), "value": 21.0, "sample_count": 2},
                {
                    "t": self.wire_time(date_from + timedelta(minutes=15)),
                    "value": 30.0,
                    "sample_count": 1,
                },
            ],
        )

    def test_the_bucket_widens_with_the_range_like_the_history_series(self):
        self.record(self.temperature_variable, "21.00", minutes_ago=5)
        expected = {1: 600, 6: 900, 24: 900, 7 * 24: 3600, 30 * 24: 21600, 90 * 24: 86400}

        for hours, bucket_seconds in expected.items():
            with self.subTest(hours=hours):
                payload = self.series(
                    date_from=(self.now - timedelta(hours=hours)).isoformat(),
                    date_to=self.now.isoformat(),
                ).json()
                self.assertEqual(payload[0]["bucket_seconds"], bucket_seconds)

    def test_the_variable_filter_takes_a_semantic_key(self):
        self.record(self.temperature_variable, "21.00", minutes_ago=5)
        self.record(self.radiation_variable, "600.00", minutes_ago=5)

        payload = self.series(variable="solar_radiation").json()

        self.assertEqual([series["semantic_key"] for series in payload], ["solar_radiation"])

    def test_null_values_inactive_variables_and_readings_out_of_range_are_absent(self):
        pressure = self.configure(self.station, self.pressure, is_active=False)
        self.record(pressure, "1010.00", minutes_ago=5)
        self.record(self.temperature_variable, None, minutes_ago=5)
        self.record(self.radiation_variable, "600.00", at=self.now - timedelta(days=8))

        self.assertEqual(self.series().json(), [])

    def test_an_invalid_range_is_rejected(self):
        cases = {
            "too wide": {"date_from": (self.now - timedelta(days=91)).isoformat()},
            "inverted": {
                "date_from": self.now.isoformat(),
                "date_to": (self.now - timedelta(days=1)).isoformat(),
            },
        }
        for name, params in cases.items():
            with self.subTest(name):
                response = self.series(**params)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("date_from", response.json())

        response = self.series(variable="wind")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("variable", response.json())

    def test_another_farmers_station_is_404(self):
        station = self.make_station(farm=self.other_farm)

        response = self.station_get("station-series", station)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_it_requires_authentication(self):
        self.client.force_authenticate(user=None)

        self.assertEqual(self.series().status_code, status.HTTP_401_UNAUTHORIZED)

    def test_the_query_count_does_not_grow_with_the_number_of_variables(self):
        self.record(self.temperature_variable, "21.00", minutes_ago=5)
        # The station ownership lookup and the single bucketed aggregate.
        with self.assertNumQueries(2):
            self.series()

        self.record(self.radiation_variable, "600.00", minutes_ago=5)
        self.record(self.configure(self.station, self.pressure), "1010.00", minutes_ago=5)
        with self.assertNumQueries(2):
            response = self.series()

        self.assertEqual(len(response.json()), 3)


class WeatherStationReadingsTests(WeatherStationTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.station = cls.make_station()
        cls.temperature_variable = cls.configure(cls.station, cls.temperature)
        cls.radiation_variable = cls.configure(cls.station, cls.radiation)

    def readings(self, **params):
        return self.station_get("station-readings", self.station, **params)

    def test_the_page_envelope_matches_the_history_readings(self):
        for step in range(25):
            self.record(self.temperature_variable, 20 + step, minutes_ago=step + 1)

        payload = self.readings().json()

        self.assertEqual(set(payload), {"count", "page", "page_size", "results"})
        self.assertEqual(payload["count"], 25)
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["page_size"], 20)
        self.assertEqual(len(payload["results"]), 20)

    def test_a_row_names_the_variable_and_carries_a_numeric_value(self):
        reading = self.record(self.temperature_variable, "27.40", minutes_ago=3)

        row = self.readings().json()["results"][0]

        self.assertEqual(
            row,
            {
                "id": reading.pk,
                "recorded_at": self.wire_time(reading.snapshot.recorded_at),
                "variable_id": self.temperature.pk,
                "semantic_key": "air_temperature",
                "variable_name": "Temperatura del aire",
                "value": 27.4,
                "unit": "°C",
            },
        )

    def test_rows_run_newest_first_with_the_id_as_a_unique_tie_break(self):
        older = self.record(self.temperature_variable, "18.00", minutes_ago=30)
        newer = [
            self.record(self.temperature_variable, "21.00", minutes_ago=3),
            self.record(self.radiation_variable, "600.00", minutes_ago=3),
        ]
        pressure = self.configure(self.station, self.pressure)
        newer.append(self.record(pressure, "1010.00", minutes_ago=3))
        expected = [reading.pk for reading in sorted(newer, key=lambda r: -r.pk)] + [older.pk]

        first = self.readings(page_size=2).json()["results"]
        second = self.readings(page_size=2, page=2).json()["results"]

        self.assertEqual([row["id"] for row in first + second], expected)

    def test_the_reading_order_ends_in_a_unique_tie_break(self):
        self.assertEqual(STATION_READING_ORDER, ("-snapshot__recorded_at", "-id"))

    def test_filters_apply_and_null_values_are_absent(self):
        self.record(self.temperature_variable, "21.00", minutes_ago=3)
        self.record(self.temperature_variable, None, minutes_ago=6)
        self.record(self.radiation_variable, "600.00", minutes_ago=3)
        self.record(self.radiation_variable, "500.00", at=self.now - timedelta(days=8))

        payload = self.readings(variable="solar_radiation").json()

        self.assertEqual([row["value"] for row in payload["results"]], [600.0])
        self.assertEqual(self.readings().json()["count"], 2)

    def test_another_farmers_station_is_404(self):
        station = self.make_station(farm=self.other_farm)

        response = self.station_get("station-readings", station)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_it_requires_authentication(self):
        self.client.force_authenticate(user=None)

        self.assertEqual(self.readings().status_code, status.HTTP_401_UNAUTHORIZED)

    def test_the_query_count_does_not_grow_with_the_page_size(self):
        for step in range(25):
            self.record(self.temperature_variable, 20 + step, minutes_ago=step + 1)
        # The station ownership lookup, the page count and the page itself.
        with self.assertNumQueries(3):
            self.readings(page_size=5)
        with self.assertNumQueries(3):
            self.readings(page_size=100)


class WeatherStationExportTests(WeatherStationTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.station = cls.make_station("Estación Unillanos")
        cls.temperature_variable = cls.configure(cls.station, cls.temperature)
        cls.radiation_variable = cls.configure(cls.station, cls.radiation)

    def body_of(self, response):
        return b"".join(response.streaming_content).decode("utf-8")

    def export(self, extension, station=None, **params):
        return self.station_get(f"station-export-{extension}", station or self.station, **params)

    def test_the_csv_has_a_bom_a_header_and_one_row_per_reading_newest_first(self):
        older = self.record(self.temperature_variable, "21.50", minutes_ago=10)
        newer = self.record(self.radiation_variable, "612.00", minutes_ago=3)

        response = self.export("csv")
        text = self.body_of(response)

        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertTrue(text.startswith(BOM_UTF8))
        rows = list(csv.reader(io.StringIO(text.lstrip(BOM_UTF8))))
        self.assertEqual(
            rows,
            [
                ["recorded_at", "station", "variable", "semantic_key", "value", "unit"],
                [
                    self.wire_time(newer.snapshot.recorded_at),
                    "Estación Unillanos",
                    "Radiación solar",
                    "solar_radiation",
                    "612.0",
                    "W/m²",
                ],
                [
                    self.wire_time(older.snapshot.recorded_at),
                    "Estación Unillanos",
                    "Temperatura del aire",
                    "air_temperature",
                    "21.5",
                    "°C",
                ],
            ],
        )

    def test_the_json_is_an_array_of_the_same_rows(self):
        reading = self.record(self.temperature_variable, "21.50", minutes_ago=10)
        self.record(self.temperature_variable, None, minutes_ago=5)

        response = self.export("json")

        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(
            json.loads(self.body_of(response)),
            [
                {
                    "recorded_at": self.wire_time(reading.snapshot.recorded_at),
                    "station_id": self.station.pk,
                    "station_name": "Estación Unillanos",
                    "variable_id": self.temperature.pk,
                    "semantic_key": "air_temperature",
                    "variable_name": "Temperatura del aire",
                    "value": 21.5,
                    "unit": "°C",
                }
            ],
        )

    def test_the_filename_names_the_station_and_the_range(self):
        response = self.export(
            "csv", date_from="2026-08-01T00:00:00Z", date_to="2026-08-22T00:00:00Z"
        )

        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="historial-estacion-estacion-unillanos-20260801_20260822.csv"; '
            "filename*=UTF-8''historial-estacion-estacion-unillanos-20260801_20260822.csv",
        )

    def test_the_export_respects_the_filters(self):
        self.record(self.temperature_variable, "21.50", minutes_ago=10)
        self.record(self.radiation_variable, "612.00", minutes_ago=3)

        rows = json.loads(self.body_of(self.export("json", variable="air_temperature")))

        self.assertEqual([row["semantic_key"] for row in rows], ["air_temperature"])

    def test_a_set_over_the_cap_is_rejected_for_both_formats(self):
        for step in range(3):
            self.record(self.temperature_variable, 20 + step, minutes_ago=step + 1)

        for extension in ("csv", "json"):
            with self.subTest(extension), patch("sensors.utils.HISTORY_EXPORT_ROW_CAP", 2):
                response = self.export(extension)
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

    def test_another_farmers_station_is_404(self):
        station = self.make_station(farm=self.other_farm)

        for extension in ("csv", "json"):
            with self.subTest(extension):
                response = self.export(extension, station=station)
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_it_requires_authentication(self):
        self.client.force_authenticate(user=None)

        for extension in ("csv", "json"):
            with self.subTest(extension):
                self.assertEqual(
                    self.export(extension).status_code, status.HTTP_401_UNAUTHORIZED
                )


class WeatherStationSchemaTests(APITestCase):
    def schema(self):
        return self.client.get(reverse("schema"), HTTP_ACCEPT="application/json").json()

    def test_every_station_endpoint_is_documented_under_its_tag(self):
        paths = self.schema()["paths"]

        for path in (
            "/api/sensors/farms/{farm_id}/stations/",
            "/api/sensors/stations/{station_id}/",
            "/api/sensors/stations/{station_id}/series/",
            "/api/sensors/stations/{station_id}/readings/",
            "/api/sensors/stations/{station_id}/export/csv/",
            "/api/sensors/stations/{station_id}/export/json/",
        ):
            with self.subTest(path):
                self.assertEqual(paths[path]["get"]["tags"], ["Weather stations"])

    def test_the_description_quotes_the_live_stale_threshold(self):
        operation = self.schema()["paths"]["/api/sensors/farms/{farm_id}/stations/"]["get"]

        stale_minutes = int(STATION_STALE_AFTER.total_seconds() // 60)
        self.assertIn(f"older than {stale_minutes} minutes", operation["description"])
