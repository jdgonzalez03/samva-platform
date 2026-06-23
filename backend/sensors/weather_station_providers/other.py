from django.utils import timezone


def fetch_other(station):
    print('Fetching weather data from other sources')
    print('TODO: Please implement this function!')
    return {
        'data': {},
        'raw': None,
        'recorded_at': timezone.now(),
    }
