import itertools
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from farm.models import Farm, Plot
from farmer.models import Farmer
from predictions.fuzzy import membership_definitions, predict_irrigation
from predictions.fuzzy.irrigation import INPUTS, OUTPUT, RULES
from predictions.models import IrrigationPrediction, PredictionStatus
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

GOLDEN_TEMPERATURES = (0, 8, 12.5, 17, 24)
GOLDEN_RADIATIONS = (0, 100, 600, 1200, 3000)
# Reference minutes of the study's model for each moisture: one row per temperature,
# one column per radiation. A mismatch means the rules or membership functions changed.
GOLDEN_MINUTES = {
    0: [
        (28.67, 28.4, 28.67, 28.37, 28.67),
        (28.67, 28.4, 28.67, 28.37, 28.67),
        (24.45, 24.45, 24.45, 20.47, 19.64),
        (24.21, 17.05, 17.01, 15.72, 12.49),
        (28.67, 14.29, 8.0, 7.05, 2.67),
    ],
    10: [
        (28.67, 28.4, 28.67, 28.37, 28.67),
        (28.67, 28.4, 28.67, 28.37, 28.67),
        (24.45, 24.45, 24.45, 20.47, 19.64),
        (24.21, 17.05, 17.01, 15.72, 12.49),
        (28.67, 14.29, 8.0, 7.05, 2.67),
    ],
    22.5: [
        (19.64, 19.64, 19.64, 19.64, 19.64),
        (19.64, 19.64, 19.64, 19.64, 19.64),
        (20.47, 20.47, 20.47, 16.48, 15.27),
        (20.24, 16.75, 16.43, 15.27, 11.33),
        (24.45, 16.7, 8.0, 7.05, 3.11),
    ],
    30: [
        (16.0, 16.0, 16.0, 16.0, 16.0),
        (16.0, 16.0, 16.0, 16.0, 16.0),
        (16.0, 16.0, 16.0, 12.0, 12.0),
        (19.28, 15.92, 12.64, 11.33, 7.39),
        (23.94, 16.2, 8.0, 7.05, 2.67),
    ],
    40: [
        (10.17, 10.69, 10.17, 10.81, 10.17),
        (10.17, 10.69, 10.17, 10.81, 10.17),
        (10.81, 10.81, 10.81, 10.5, 10.5),
        (14.43, 14.2, 10.14, 10.5, 6.37),
        (14.49, 14.04, 6.22, 6.66, 2.89),
    ],
    52: [
        (2.67, 3.07, 2.67, 3.11, 2.67),
        (2.67, 3.07, 2.67, 3.11, 2.67),
        (3.11, 3.11, 3.11, 3.11, 3.11),
        (2.97, 3.07, 2.97, 3.11, 2.97),
        (2.67, 3.07, 2.67, 3.11, 2.67),
    ],
}


class IrrigationEngineTests(SimpleTestCase):
    def test_minutes_match_the_reference_grid(self):
        for moisture, rows in GOLDEN_MINUTES.items():
            for temperature, row in zip(GOLDEN_TEMPERATURES, rows, strict=True):
                for radiation, expected in zip(GOLDEN_RADIATIONS, row, strict=True):
                    with self.subTest(m=moisture, t=temperature, r=radiation):
                        result = predict_irrigation(moisture, temperature, radiation)
                        self.assertEqual(result.minutes, expected)

    def test_rules_cover_every_input_term_combination(self):
        combinations = set(
            itertools.product(*(variable.terms for variable in INPUTS.values()))
        )
        self.assertEqual(set(RULES), combinations)
        self.assertLessEqual(set(RULES.values()), set(OUTPUT.terms))

    def test_reports_the_membership_of_each_input(self):
        result = predict_irrigation(moisture=40, temperature=17, radiation=600)

        self.assertEqual(result.input_memberships['moisture'], {'low': 0.0, 'medium': 0.333, 'high': 0.667})
        self.assertEqual(result.input_memberships['temperature'], {'low': 0.0, 'medium': 0.6, 'high': 0.4})
        self.assertEqual(result.input_memberships['radiation'], {'low': 0.0, 'medium': 1.0, 'high': 0.0})

    def test_reports_the_activation_of_each_output_term(self):
        result = predict_irrigation(moisture=40, temperature=17, radiation=600)

        self.assertEqual(
            result.output_activation,
            {'nothing': 0.6, 'very_little': 0.333, 'little': 0.333, 'long': 0.0, 'very_long': 0.0},
        )

    def test_label_is_the_output_term_the_minutes_belong_to_most(self):
        self.assertEqual(predict_irrigation(0, 0, 0).label, 'very_long')
        self.assertEqual(predict_irrigation(30, 0, 0).label, 'little')
        self.assertEqual(predict_irrigation(40, 17, 600).label, 'very_little')
        self.assertEqual(predict_irrigation(52, 24, 3000).label, 'nothing')

    def test_out_of_range_inputs_are_clipped_and_reported(self):
        clipped = predict_irrigation(moisture=-5, temperature=31, radiation=4000)
        at_bounds = predict_irrigation(moisture=0, temperature=25, radiation=3500)

        self.assertEqual(clipped.clipped_inputs, ['moisture', 'temperature', 'radiation'])
        self.assertEqual(clipped.minutes, at_bounds.minutes)
        self.assertEqual(at_bounds.clipped_inputs, [])

    def test_membership_definitions_describe_every_variable(self):
        definitions = membership_definitions()

        self.assertEqual(
            set(definitions), {'moisture', 'temperature', 'radiation', 'irrigation_time'}
        )
        self.assertEqual(
            definitions['temperature']['terms']['medium'],
            {'shape': 'tri', 'points': [10.0, 15.0, 20.0]},
        )
        self.assertEqual(definitions['radiation']['unit'], 'W/m²')


class IrrigationPredictionAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username='juan', email='juan@example.com', password='testpass123'
        )
        farmer = Farmer.objects.create(user=cls.user, first_name='Juan')
        other_user = get_user_model().objects.create_user(
            username='maria', email='maria@example.com', password='testpass123'
        )
        other_farmer = Farmer.objects.create(user=other_user, first_name='María')

        farm = Farm.objects.create(owner=farmer, name='Finca El Tesoro', address='Vereda')
        other_farm = Farm.objects.create(owner=other_farmer, name='Finca Ajena', address='Vereda')
        cls.plot = Plot.objects.create(farm=farm, name='Lote Norte')
        cls.second_plot = Plot.objects.create(farm=farm, name='Lote Sur')
        cls.other_plot = Plot.objects.create(farm=other_farm, name='Lote Ajeno')

        variables = {
            key: EnvironmentalVariable.objects.create(name=key, semantic_key=key, unit='')
            for key in (
                SemanticKey.SOIL_MOISTURE,
                SemanticKey.AIR_TEMPERATURE,
                SemanticKey.SOLAR_RADIATION,
            )
        }
        sensor = FieldSensor.objects.create(plot=cls.plot, name='Sensor 1')
        inactive_sensor = FieldSensor.objects.create(
            plot=cls.plot, name='Sensor apagado', is_active=False
        )
        cls.channels = {
            key: FieldSensorVariable.objects.create(sensor=sensor, env_variable=variable)
            for key, variable in variables.items()
        }
        cls.inactive_moisture = FieldSensorVariable.objects.create(
            sensor=inactive_sensor, env_variable=variables[SemanticKey.SOIL_MOISTURE]
        )
        cls.now = timezone.now().replace(microsecond=0)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def record(self, key, value, minutes_ago=10, channel=None):
        SensorMeasurement.objects.create(
            sensor_variable=channel or self.channels[key],
            value=None if value is None else Decimal(str(value)),
            recorded_at=self.now - timedelta(minutes=minutes_ago),
        )

    def record_all(self, moisture, temperature, radiation, minutes_ago=10):
        self.record(SemanticKey.SOIL_MOISTURE, moisture, minutes_ago)
        self.record(SemanticKey.AIR_TEMPERATURE, temperature, minutes_ago)
        self.record(SemanticKey.SOLAR_RADIATION, radiation, minutes_ago)

    def predict(self, plot=None, **body):
        url = reverse('predictions:plot-irrigation', args=[(plot or self.plot).pk])
        return self.client.post(url, body, format='json')

    def test_creates_a_prediction_from_the_recent_averages(self):
        self.record_all(moisture=30, temperature=15, radiation=700, minutes_ago=30)
        self.record_all(moisture=50, temperature=19, radiation=500, minutes_ago=90)

        response = self.predict()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        expected = predict_irrigation(40, 17, 600)
        self.assertEqual(response.data['avg_moisture'], 40.0)
        self.assertEqual(response.data['avg_temperature'], 17.0)
        self.assertEqual(response.data['avg_radiation'], 600.0)
        self.assertEqual(response.data['avg_period_hours'], 6)
        self.assertEqual(response.data['irrigation_time_minutes'], expected.minutes)
        self.assertEqual(response.data['output_label'], expected.label)
        self.assertEqual(response.data['input_memberships'], expected.input_memberships)
        self.assertEqual(response.data['output_activation'], expected.output_activation)

        prediction = IrrigationPrediction.objects.get(pk=response.data['id'])
        self.assertEqual(prediction.plot, self.plot)
        self.assertEqual(prediction.status, PredictionStatus.COMPLETED)
        self.assertIsNotNone(prediction.completed_at)

    def test_ignores_readings_outside_the_window(self):
        self.record_all(moisture=40, temperature=17, radiation=600, minutes_ago=30)
        self.record_all(moisture=0, temperature=0, radiation=0, minutes_ago=7 * 60)

        response = self.predict()

        self.assertEqual(response.data['avg_moisture'], 40.0)

    def test_window_length_is_configurable(self):
        self.record_all(moisture=40, temperature=17, radiation=600, minutes_ago=30)
        self.record_all(moisture=20, temperature=17, radiation=600, minutes_ago=10 * 60)

        response = self.predict(hours=12)

        self.assertEqual(response.data['avg_moisture'], 30.0)
        self.assertEqual(response.data['avg_period_hours'], 12)

    def test_ignores_inactive_sensors_and_null_values(self):
        self.record_all(moisture=40, temperature=17, radiation=600)
        self.record(SemanticKey.SOIL_MOISTURE, None, minutes_ago=20)
        self.record(SemanticKey.SOIL_MOISTURE, 0, channel=self.inactive_moisture)

        response = self.predict()

        self.assertEqual(response.data['avg_moisture'], 40.0)

    def test_reports_clipped_inputs(self):
        self.record_all(moisture=40, temperature=31, radiation=600)

        response = self.predict()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['avg_temperature'], 31.0)
        self.assertEqual(response.data['clipped_inputs'], ['temperature'])

    def test_missing_variables_return_422_without_creating_a_prediction(self):
        self.record(SemanticKey.AIR_TEMPERATURE, 17)

        response = self.predict()

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(
            response.data['missing'],
            [SemanticKey.SOIL_MOISTURE, SemanticKey.SOLAR_RADIATION],
        )
        self.assertFalse(IrrigationPrediction.objects.exists())

    def test_rejects_a_window_out_of_bounds(self):
        response = self.predict(hours=48)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hours', response.data)

    def test_plot_of_another_user_returns_404(self):
        self.assertEqual(self.predict(plot=self.other_plot).status_code, status.HTTP_404_NOT_FOUND)
        url = reverse('predictions:plot-irrigation', args=[self.other_plot.pk])
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)

        self.assertEqual(self.predict().status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            self.client.get(reverse('predictions:model-list')).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_history_lists_the_plot_predictions_newest_first(self):
        self.record_all(moisture=40, temperature=17, radiation=600)
        first = self.predict().data['id']
        second = self.predict().data['id']
        IrrigationPrediction.objects.create(
            plot=self.second_plot, avg_moisture=1, avg_temperature=1, avg_radiation=1
        )

        response = self.client.get(reverse('predictions:plot-irrigation', args=[self.plot.pk]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual([row['id'] for row in response.data['results']], [second, first])

    def test_model_catalogue_lists_fuzzy_irrigation(self):
        response = self.client.get(reverse('predictions:model-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            [{'key': 'fuzzy-irrigation', 'technique': 'fuzzy', 'target': 'irrigation'}],
        )

    def test_definitions_endpoint_returns_the_membership_functions(self):
        response = self.client.get(reverse('predictions:irrigation-definitions'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, membership_definitions())


class IrrigationPredictionSourcesTests(APITestCase):
    """Field sensors and the farm's weather station both feed the model, one vote each."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username='juan', email='juan@example.com', password='testpass123'
        )
        farmer = Farmer.objects.create(user=cls.user, first_name='Juan')
        cls.farm = Farm.objects.create(owner=farmer, name='Finca El Tesoro', address='Vereda')
        other_farm = Farm.objects.create(owner=farmer, name='Finca San Vicente', address='Vereda')
        cls.plot = Plot.objects.create(farm=cls.farm, name='Lote Norte')

        cls.variables = {
            key: EnvironmentalVariable.objects.create(name=key, semantic_key=key, unit='')
            for key in (
                SemanticKey.SOIL_MOISTURE,
                SemanticKey.AIR_TEMPERATURE,
                SemanticKey.SOLAR_RADIATION,
            )
        }
        sensor = FieldSensor.objects.create(plot=cls.plot, name='Sensor 1')
        cls.field_channels = {
            key: FieldSensorVariable.objects.create(sensor=sensor, env_variable=variable)
            for key, variable in cls.variables.items()
        }

        cls.station = WeatherStation.objects.create(
            farm=cls.farm, name='Estación', station_id='s-1', api_key='key'
        )
        cls.station_channels = {
            key: WeatherStationVariableConfiguration.objects.create(
                station=cls.station,
                env_variable=variable,
                field_key=key,
                use_in_predictions=True,
            )
            for key, variable in cls.variables.items()
        }
        inactive_station = WeatherStation.objects.create(
            farm=cls.farm, name='Estación apagada', station_id='s-2', api_key='key', is_active=False
        )
        cls.inactive_station_temperature = WeatherStationVariableConfiguration.objects.create(
            station=inactive_station,
            env_variable=cls.variables[SemanticKey.AIR_TEMPERATURE],
            field_key='temp',
            use_in_predictions=True,
        )
        other_station = WeatherStation.objects.create(
            farm=other_farm, name='Estación vecina', station_id='s-3', api_key='key'
        )
        cls.other_farm_temperature = WeatherStationVariableConfiguration.objects.create(
            station=other_station,
            env_variable=cls.variables[SemanticKey.AIR_TEMPERATURE],
            field_key='temp',
            use_in_predictions=True,
        )
        cls.now = timezone.now().replace(microsecond=0)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def record_field(self, key, value, minutes_ago=10):
        SensorMeasurement.objects.create(
            sensor_variable=self.field_channels[key],
            value=Decimal(str(value)),
            recorded_at=self.now - timedelta(minutes=minutes_ago),
        )

    def record_station(self, key, value, minutes_ago=10, channel=None):
        channel = channel or self.station_channels[key]
        snapshot, _ = WeatherSnapshot.objects.get_or_create(
            station=channel.station, recorded_at=self.now - timedelta(minutes=minutes_ago)
        )
        WeatherMeasurement.objects.create(
            snapshot=snapshot, station_variable=channel, value=Decimal(str(value))
        )

    def record_field_inputs(self, moisture=40, temperature=17, radiation=600, minutes_ago=10):
        self.record_field(SemanticKey.SOIL_MOISTURE, moisture, minutes_ago)
        self.record_field(SemanticKey.AIR_TEMPERATURE, temperature, minutes_ago)
        self.record_field(SemanticKey.SOLAR_RADIATION, radiation, minutes_ago)

    def record_station_inputs(self, moisture=40, temperature=17, radiation=600, minutes_ago=10):
        self.record_station(SemanticKey.SOIL_MOISTURE, moisture, minutes_ago)
        self.record_station(SemanticKey.AIR_TEMPERATURE, temperature, minutes_ago)
        self.record_station(SemanticKey.SOLAR_RADIATION, radiation, minutes_ago)

    def predict(self):
        url = reverse('predictions:plot-irrigation', args=[self.plot.pk])
        return self.client.post(url, {}, format='json')

    def test_field_sensors_alone_are_enough(self):
        self.record_field_inputs()

        response = self.predict()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data['input_sources'],
            {
                'moisture': {'field': 40.0, 'station': None},
                'temperature': {'field': 17.0, 'station': None},
                'radiation': {'field': 600.0, 'station': None},
            },
        )

    def test_the_weather_station_alone_is_enough(self):
        self.record_station_inputs(moisture=30, temperature=20, radiation=500)

        response = self.predict()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['avg_moisture'], 30.0)
        self.assertEqual(response.data['avg_temperature'], 20.0)
        self.assertEqual(
            response.data['input_sources']['moisture'], {'field': None, 'station': 30.0}
        )

    def test_both_sources_are_averaged_with_equal_weight(self):
        # Three field readings against one station reading: the station still counts half.
        for minutes_ago in (10, 20, 30):
            self.record_field_inputs(temperature=20, minutes_ago=minutes_ago)
        self.record_station_inputs(temperature=30)

        response = self.predict()

        self.assertEqual(response.data['avg_temperature'], 25.0)
        self.assertEqual(
            response.data['input_sources']['temperature'], {'field': 20.0, 'station': 30.0}
        )
        expected = predict_irrigation(40, 25, 600)
        self.assertEqual(response.data['irrigation_time_minutes'], expected.minutes)

    def test_a_field_variable_left_out_of_predictions_is_ignored(self):
        FieldSensorVariable.objects.filter(
            pk=self.field_channels[SemanticKey.AIR_TEMPERATURE].pk
        ).update(use_in_predictions=False)
        self.record_field_inputs(temperature=5)
        self.record_station(SemanticKey.AIR_TEMPERATURE, 18)

        response = self.predict()

        self.assertEqual(response.data['avg_temperature'], 18.0)
        self.assertEqual(
            response.data['input_sources']['temperature'], {'field': None, 'station': 18.0}
        )

    def test_a_station_variable_is_left_out_unless_enabled(self):
        WeatherStationVariableConfiguration.objects.filter(
            pk=self.station_channels[SemanticKey.AIR_TEMPERATURE].pk
        ).update(use_in_predictions=False)
        self.record_field_inputs(temperature=17)
        self.record_station(SemanticKey.AIR_TEMPERATURE, 30)

        response = self.predict()

        self.assertEqual(response.data['avg_temperature'], 17.0)

    def test_station_variables_default_to_left_out(self):
        configuration = WeatherStationVariableConfiguration.objects.create(
            station=self.station,
            env_variable=EnvironmentalVariable.objects.create(
                name='Humedad relativa', semantic_key=SemanticKey.RELATIVE_HUMIDITY, unit='%'
            ),
            field_key='hum_out',
        )

        self.assertFalse(configuration.use_in_predictions)
        self.assertTrue(
            FieldSensorVariable._meta.get_field('use_in_predictions').default
        )

    def test_inactive_and_foreign_stations_and_old_readings_are_ignored(self):
        self.record_field_inputs(temperature=17)
        self.record_station(
            SemanticKey.AIR_TEMPERATURE, 0, channel=self.inactive_station_temperature
        )
        self.record_station(SemanticKey.AIR_TEMPERATURE, 0, channel=self.other_farm_temperature)
        self.record_station(SemanticKey.AIR_TEMPERATURE, 0, minutes_ago=7 * 60)
        WeatherStationVariableConfiguration.objects.filter(
            pk=self.station_channels[SemanticKey.SOLAR_RADIATION].pk
        ).update(is_active=False)
        self.record_station(SemanticKey.SOLAR_RADIATION, 0)

        response = self.predict()

        self.assertEqual(response.data['avg_temperature'], 17.0)
        self.assertEqual(response.data['avg_radiation'], 600.0)
        self.assertEqual(
            response.data['input_sources']['temperature'], {'field': 17.0, 'station': None}
        )

    def test_an_input_neither_source_has_returns_422(self):
        self.record_field(SemanticKey.AIR_TEMPERATURE, 17)
        self.record_station(SemanticKey.SOLAR_RADIATION, 600)

        response = self.predict()

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data['missing'], [SemanticKey.SOIL_MOISTURE])
        self.assertFalse(IrrigationPrediction.objects.exists())

    def test_the_history_keeps_the_sources_of_each_prediction(self):
        self.record_field_inputs()
        self.record_station_inputs(moisture=20)
        self.predict()

        response = self.client.get(reverse('predictions:plot-irrigation', args=[self.plot.pk]))

        self.assertEqual(
            response.data['results'][0]['input_sources']['moisture'],
            {'field': 40.0, 'station': 20.0},
        )
