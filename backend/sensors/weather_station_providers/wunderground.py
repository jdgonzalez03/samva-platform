from django.utils import timezone


def fetch_wunderground(station):
    print('Fetching weather data from wunderground')
    print('TODO: Please implement this function!')
    return {
        'data': {},
        'raw': None,
        'recorded_at': timezone.now(),
    }
