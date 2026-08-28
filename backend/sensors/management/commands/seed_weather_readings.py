import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from sensors.models import (
    SemanticKey,
    WeatherMeasurement,
    WeatherSnapshot,
    WeatherStation,
)

VALUE_RANGES = {
    SemanticKey.AIR_TEMPERATURE: (18, 30),
    SemanticKey.SOLAR_RADIATION: (0, 950),
    SemanticKey.RELATIVE_HUMIDITY: (40, 95),
    SemanticKey.SOIL_MOISTURE: (20, 60),
    SemanticKey.OTHER: (900, 1015),
}
DEFAULT_RANGE = (0, 100)


class Command(BaseCommand):
    help = (
        'Seed weather snapshots and measurements with timestamps relative to now, so the '
        'dashboard cards show a recent reading instead of a date frozen in a fixture.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=12, help='Snapshots per station.')
        parser.add_argument(
            '--interval-minutes', type=int, default=5, help='Gap between snapshots.'
        )
        parser.add_argument(
            '--lag-minutes',
            type=int,
            default=3,
            help='Age of the newest snapshot of a station.',
        )
        parser.add_argument(
            '--stale-minutes',
            type=int,
            default=95,
            help='Age of the newest snapshot of the stale farm, past the staleness threshold.',
        )
        parser.add_argument(
            '--stale-farm',
            type=int,
            default=2,
            help='Farm whose stations are seeded stale so the outdated badge is visible.',
        )
        parser.add_argument('--farm', type=int, help='Seed only the stations of this farm.')

    @transaction.atomic
    def handle(self, *args, **options):
        stations = WeatherStation.objects.filter(
            is_active=True, station_variables__is_active=True
        ).distinct()
        if options['farm'] is not None:
            stations = stations.filter(farm_id=options['farm'])

        now = timezone.now()
        interval = timedelta(minutes=options['interval_minutes'])
        seeded_stations = 0
        seeded_measurements = 0

        for station in stations:
            configurations = list(
                station.station_variables.filter(is_active=True).select_related('env_variable')
            )
            lag = (
                options['stale_minutes']
                if station.farm_id == options['stale_farm']
                else options['lag_minutes']
            )
            newest = now - timedelta(minutes=lag)

            # Deleting first cascades the measurements away, which keeps the command
            # idempotent and respects the (station, recorded_at) uniqueness.
            station.snapshots.all().delete()

            for step in range(options['count']):
                snapshot = WeatherSnapshot.objects.create(
                    station=station, recorded_at=newest - step * interval
                )
                WeatherMeasurement.objects.bulk_create(
                    WeatherMeasurement(
                        snapshot=snapshot,
                        station_variable=configuration,
                        value=self.plausible_value(configuration.env_variable.semantic_key),
                    )
                    for configuration in configurations
                )
                seeded_measurements += len(configurations)

            seeded_stations += 1

        if options['verbosity']:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Seeded {seeded_measurements} measurements across {seeded_stations} stations.'
                )
            )

    def plausible_value(self, semantic_key):
        low, high = VALUE_RANGES.get(semantic_key, DEFAULT_RANGE)
        return Decimal(f'{random.uniform(low, high):.2f}')
