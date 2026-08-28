import math
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from sensors.models import FieldSensorVariable, SemanticKey, SensorMeasurement

VALUE_RANGES = {
    SemanticKey.AIR_TEMPERATURE: (19, 29),
    SemanticKey.SOLAR_RADIATION: (0, 950),
    SemanticKey.RELATIVE_HUMIDITY: (50, 90),
    SemanticKey.SOIL_MOISTURE: (25, 55),
    SemanticKey.OTHER: (1000, 1020),
}
DEFAULT_RANGE = (0, 100)

IRRIGATION_CYCLE = timedelta(days=3)
GAP_HOURS = 6
NULL_EVERY = 240


def hour_of_day(moment):
    return moment.hour + moment.minute / 60


def air_temperature(moment, noise):
    return 24 + 5 * math.sin(2 * math.pi * (hour_of_day(moment) - 9) / 24) + noise.gauss(0, 0.4)


def relative_humidity(moment, noise):
    # Anti-phase with temperature: the air dries out as it warms up.
    return 70 - 20 * math.sin(2 * math.pi * (hour_of_day(moment) - 9) / 24) + noise.gauss(0, 2)


def solar_radiation(moment, noise):
    hour = hour_of_day(moment)
    if hour <= 6 or hour >= 18:
        return 0
    # Jitter scales with the curve so passing clouds dim the day without lighting the night.
    base = 900 * math.sin(math.pi * (hour - 6) / 12)
    return base + noise.gauss(0, base * 0.06)


def soil_moisture(moment, noise):
    # Slow drying between irrigations, then a step back up when the cycle restarts.
    elapsed = moment.timestamp() % IRRIGATION_CYCLE.total_seconds()
    return 55 - 30 * (elapsed / IRRIGATION_CYCLE.total_seconds()) + noise.gauss(0, 0.8)


def barometric_pressure(moment, noise):
    return 1010 + 3 * math.sin(2 * math.pi * hour_of_day(moment) / 24) + noise.gauss(0, 0.5)


def flat_curve(moment, noise):
    return 50 + noise.gauss(0, 5)


CURVES = {
    SemanticKey.AIR_TEMPERATURE: air_temperature,
    SemanticKey.RELATIVE_HUMIDITY: relative_humidity,
    SemanticKey.SOLAR_RADIATION: solar_radiation,
    SemanticKey.SOIL_MOISTURE: soil_moisture,
    SemanticKey.OTHER: barometric_pressure,
}


class Command(BaseCommand):
    help = (
        'Seed sensor measurements for every active field sensor variable, on daily curves '
        'ending at now, so the history page has something to plot, page and export.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Days of history to write.')
        parser.add_argument(
            '--interval-minutes', type=int, default=15, help='Gap between readings.'
        )
        parser.add_argument('--farm', type=int, help='Seed only the sensors of this farm.')
        parser.add_argument('--plot', type=int, help='Seed only the sensors of this plot.')
        parser.add_argument('--seed', type=int, help='Make the generated series reproducible.')
        parser.add_argument(
            '--keep',
            action='store_true',
            help='Append to the existing readings instead of replacing them.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        sensor_variables = list(
            self.select_sensor_variables(options).select_related('env_variable')
        )
        if not sensor_variables:
            return

        # `SensorMeasurement` has no uniqueness on (sensor_variable, recorded_at), so without
        # this delete a second run would silently double every series.
        if not options['keep']:
            SensorMeasurement.objects.filter(sensor_variable__in=sensor_variables).delete()

        noise = random.Random(options['seed'])
        interval = timedelta(minutes=options['interval_minutes'])
        # Snapped to the interval grid rather than to "right now", so the timestamps of two
        # runs line up and `--seed` really does reproduce a series.
        newest = timezone.now().replace(second=0, microsecond=0)
        newest -= timedelta(minutes=newest.minute % options['interval_minutes'])
        steps = options['days'] * 24 * 60 // options['interval_minutes']

        # The seed has to expose the unhappy paths too: one series stops early so the charts
        # show a real gap, and another carries nulls so the `value__isnull=False` filter is
        # exercised by more than a unit test.
        gap_variable = sensor_variables[0]
        null_variable = sensor_variables[-1]
        seeded_measurements = 0

        for sensor_variable in sensor_variables:
            curve = CURVES.get(sensor_variable.env_variable.semantic_key, flat_curve)
            low, high = VALUE_RANGES.get(
                sensor_variable.env_variable.semantic_key, DEFAULT_RANGE
            )
            first_step = 0
            if sensor_variable.pk == gap_variable.pk:
                first_step = GAP_HOURS * 60 // options['interval_minutes']

            readings = []
            for step in range(first_step, steps + 1):
                recorded_at = newest - step * interval
                value = self.clamped(curve(recorded_at, noise), low, high)
                if sensor_variable.pk == null_variable.pk and step % NULL_EVERY == 0:
                    value = None
                readings.append(
                    SensorMeasurement(
                        sensor_variable=sensor_variable,
                        value=value,
                        recorded_at=recorded_at,
                    )
                )

            SensorMeasurement.objects.bulk_create(readings, batch_size=5000)
            seeded_measurements += len(readings)

        if options['verbosity']:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Seeded {seeded_measurements} measurements across '
                    f'{len(sensor_variables)} sensor variables.'
                )
            )

    def select_sensor_variables(self, options):
        sensor_variables = FieldSensorVariable.objects.filter(sensor__is_active=True).order_by(
            'pk'
        )
        if options['farm'] is not None:
            sensor_variables = sensor_variables.filter(sensor__plot__farm_id=options['farm'])
        if options['plot'] is not None:
            sensor_variables = sensor_variables.filter(sensor__plot_id=options['plot'])
        return sensor_variables

    def clamped(self, value, low, high):
        return Decimal(f'{min(max(value, low), high):.4f}')
