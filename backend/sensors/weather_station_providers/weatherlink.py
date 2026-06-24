import requests
from django.conf import settings
from django.utils import timezone


def _extract_measurements(raw_json):
    result = {}
    for sensor in raw_json.get('sensors', []):
        for record in sensor.get('data', []):
            result.update(record)
    return result


# Historic endpoint — stopped working since May 2026
# Kept for reference in case the API is restored
# def fetch_weatherlink(station):
#     base_url = getattr(settings, 'WEATHERLINK_BASE_URL', None)
#     if base_url is None:
#         return None
#     url = f'{base_url}/historic/{station.station_id}'
#     now = timezone.now()
#     end_time = now - timezone.timedelta(
#         minutes=now.minute % 5,
#         seconds=now.second,
#         microseconds=now.microsecond,
#     )
#     start_time = end_time - timezone.timedelta(minutes=station.polling_interval_minutes)
#     response = requests.get(
#         url,
#         params={
#             'api-key': station.api_key,
#             'start-timestamp': int(start_time.timestamp()),
#             'end-timestamp': int(end_time.timestamp()),
#         },
#         headers={'X-Api-Secret': station.api_secret},
#         timeout=15,
#     )
#     response.raise_for_status()
#     response_data = response.json()
#     return {
#         'data': _extract_measurements(response_data),
#         'raw': response_data,
#         'recorded_at': end_time,
#     }


def fetch_weatherlink(station):
    base_url = getattr(settings, 'WEATHERLINK_BASE_URL', None)

    if base_url is None:
        return None

    url = f'{base_url}/current/{station.station_id}'

    now = timezone.now()
    end_time = now - timezone.timedelta(
        minutes=now.minute % 5,
        seconds=now.second,
        microseconds=now.microsecond,
    )

    response = requests.get(
        url,
        params={'api-key': station.api_key},
        headers={'X-Api-Secret': station.api_secret},
        timeout=15,
    )
    response.raise_for_status()
    response_data = response.json()
    return {
        'data': _extract_measurements(response_data),
        'raw': response_data,
        'recorded_at': end_time,
    }
 