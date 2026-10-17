from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse

from sensors.constants import (
    API_KEY_HEADER,
    BUCKET_TIERS,
    DEFAULT_HISTORY_RANGE_DAYS,
    HISTORY_EXPORT_ROW_CAP,
    HISTORY_MAX_RANGE_DAYS,
    INGEST_MAX_CLOCK_SKEW,
    SENSOR_OFFLINE_AFTER,
    STATION_SPARKLINE_BUCKET,
    STATION_SPARKLINE_KEY,
    STATION_SPARKLINE_SPAN,
    STATION_STALE_AFTER,
    WIDEST_BUCKET,
)
from sensors.models import SemanticKey
from sensors.serializers import (
    HistorySeriesSerializer,
    SensorIngestResultSerializer,
    StationReadingPageSerializer,
    WeatherStationDetailSerializer,
    WeatherStationSerializer,
)

INGEST_TAG = "Sensor ingest"

# Built from the live constants so the published docs cannot drift from the behaviour.
INGEST_DESCRIPTION = f"""
Public endpoint field sensors (or the gateway they report through) call to push readings.

### Authentication
Send the owner's API secret in the `{API_KEY_HEADER}` header. The owner copies it from
*Perfil → Acceso API* in the dashboard (it starts with `smv_`) and can regenerate it there,
which immediately cuts off every device still using the old one. The secret identifies the
**owner**; `serial_number` identifies the **sensor**.

### Before the first upload
An administrator registers the sensor on its plot with its hardware serial number and maps
the variables it measures. *Mis sensores* in the dashboard lists every sensor with its serial.

### One request, one instant
A request carries the values of every variable the sensor measured at `recorded_at`
(one entry per variable). A device that buffered readings while offline sends one request
per instant, oldest first.

- `recorded_at` needs a timezone offset (`Z`, `-05:00`) and may be at most
  {int(INGEST_MAX_CLOCK_SKEW.total_seconds() // 60)} minutes ahead of the server clock.
- `variable` is one of: {", ".join(f"`{key}`" for key in SemanticKey.values)}; it must be
  mapped to this sensor.
- `value` takes up to 4 decimals, or `null` when the probe failed.

### Retries are safe
A reading is unique per sensor variable and `recorded_at`: resending an instant answers
`201` and counts it under `duplicates` instead of storing it twice. Retry `5xx`, timeouts
and `429` with exponential backoff; never retry `400`, `401`, `403` or `404` unchanged.

### Limits and status
- Rate limit: `{settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["sensor_ingest"]}` per API
  secret, shared by all of the owner's devices.
- Every request that reaches a registered, active sensor — even one rejected with `400` —
  updates its *last seen* time. The dashboard shows a sensor as offline after
  {int(SENSOR_OFFLINE_AFTER.total_seconds() // 60)} minutes without any request.
"""

EXAMPLE_RECORDED_AT = "2026-09-29T14:30:00Z"

INGEST_REQUEST_EXAMPLES = [
    OpenApiExample(
        "Several variables at one instant",
        value={
            "serial_number": "SN-001",
            "recorded_at": EXAMPLE_RECORDED_AT,
            "readings": [
                {"variable": SemanticKey.SOIL_MOISTURE, "value": 31.2},
                {"variable": SemanticKey.AIR_TEMPERATURE, "value": 24.8},
            ],
        },
        request_only=True,
    ),
    OpenApiExample(
        "Single variable, local time offset",
        value={
            "serial_number": "SN-001",
            "recorded_at": "2026-09-29T09:30:00-05:00",
            "readings": [{"variable": SemanticKey.SOIL_MOISTURE, "value": 31.2}],
        },
        request_only=True,
    ),
    OpenApiExample(
        "Failed probe",
        description="`null` stores the instant as a missing reading.",
        value={
            "serial_number": "SN-001",
            "recorded_at": EXAMPLE_RECORDED_AT,
            "readings": [{"variable": SemanticKey.SOIL_MOISTURE, "value": None}],
        },
        request_only=True,
    ),
]


def error_response(description, *examples):
    return OpenApiResponse(
        response=OpenApiTypes.OBJECT,
        description=description,
        examples=[
            OpenApiExample(name, value=body, response_only=True) for name, body in examples
        ],
    )


INGEST_RESPONSES = {
    201: OpenApiResponse(
        response=SensorIngestResultSerializer,
        description="Stored. `duplicates` counts variables already stored for that instant.",
        examples=[
            OpenApiExample(
                "New reading", value={"created": 2, "duplicates": 0}, response_only=True
            ),
            OpenApiExample(
                "Resent reading", value={"created": 0, "duplicates": 2}, response_only=True
            ),
        ],
    ),
    400: error_response(
        "Invalid payload. Fix the firmware or the sensor's variable mapping; do not retry.",
        (
            "Timestamp without offset",
            {"recorded_at": ["Datetime must include a timezone offset."]},
        ),
        ("Timestamp in the future", {"recorded_at": ["recorded_at must not be in the future."]}),
        ("Variable not mapped", {"readings": ["The sensor does not measure 'solar_radiation'."]}),
    ),
    401: error_response(
        f"`{API_KEY_HEADER}` missing or wrong — e.g. the owner regenerated the secret.",
        ("Missing key", {"detail": "Authentication credentials were not provided."}),
        ("Invalid key", {"detail": "Invalid API key."}),
    ),
    403: error_response(
        "The owner's account or the sensor is inactive.",
        ("Inactive sensor", {"detail": "This sensor is inactive."}),
        ("Inactive account", {"detail": "This API key belongs to an inactive account."}),
    ),
    404: error_response(
        "Serial unknown for this secret: unregistered, or registered to another owner.",
        ("Unknown sensor", {"detail": "Unknown sensor."}),
    ),
    429: error_response(
        "Rate limit exceeded. Wait the seconds the `Retry-After` header gives.",
        ("Throttled", {"detail": "Request was throttled. Expected available in 42 seconds."}),
    ),
}


STATIONS_TAG = "Weather stations"


def minutes(span):
    return int(span.total_seconds() // 60)


def hours(span):
    return int(span.total_seconds() // 3600)


STATION_CARD_DESCRIPTION = f"""
A station card: identity, reporting status, the latest value of every active variable, and
a sparkline.

- `status`: `inactive` when the station is switched off in the admin; otherwise
  `never_seen` without any snapshot, `stale` when the newest snapshot (`last_reading_at`) is
  older than {minutes(STATION_STALE_AFTER)} minutes, and `online` otherwise. Stations are polled
  every 5 minutes.
- `latest`: newest non-null value of each active station variable, ordered by variable name; a
  variable without any value is absent.
- `sparkline`: {hours(STATION_SPARKLINE_BUCKET)}-hour averages of `{STATION_SPARKLINE_KEY}` over
  the last {hours(STATION_SPARKLINE_SPAN)} hours (hour-aligned window, empty hours absent), or
  `null` when the station has no active `{STATION_SPARKLINE_KEY}` variable.
"""

STATION_LIST_DESCRIPTION = (
    "Every weather station of the farm, inactive ones included, ordered by name.\n"
    + STATION_CARD_DESCRIPTION
)

STATION_DETAIL_DESCRIPTION = (
    "One weather station; `variables` lists its active variables by name.\n"
    + STATION_CARD_DESCRIPTION
)

STATION_NOT_FOUND = error_response(
    "Unknown, or owned by someone else.", ("Not found", {"detail": "Not found."})
)

STATION_RANGE_ERRORS = error_response(
    "Invalid range or variable.",
    (
        "Range too wide",
        {"date_from": [f"The selected range must not exceed {HISTORY_MAX_RANGE_DAYS} days."]},
    ),
    ("Inverted range", {"date_from": ["date_from must be earlier than date_to."]}),
    ("Unknown variable", {"variable": ['"wind" is not a valid choice.']}),
)

STATION_HISTORY_PARAMETERS = [
    OpenApiParameter(
        "date_from",
        OpenApiTypes.DATETIME,
        description=f"Inclusive start; defaults to {DEFAULT_HISTORY_RANGE_DAYS} days before "
        f"`date_to`. The range may span at most {HISTORY_MAX_RANGE_DAYS} days.",
    ),
    OpenApiParameter(
        "date_to", OpenApiTypes.DATETIME, description="Exclusive end; defaults to now."
    ),
    OpenApiParameter(
        "variable",
        OpenApiTypes.STR,
        enum=SemanticKey.values,
        description="Semantic key; keeps only the station variables with that key.",
    ),
]

STATION_PAGE_PARAMETERS = [
    OpenApiParameter("page", OpenApiTypes.INT, description="1-based page number."),
    OpenApiParameter("page_size", OpenApiTypes.INT, description="Rows per page: 20 by default, 100 at most."),
]


def describe_tiers():
    lines = [
        f"- up to {upper_bound.days} days: {minutes(bucket_size)}-minute buckets"
        for upper_bound, bucket_size in BUCKET_TIERS
    ]
    lines.append(f"- longer: {hours(WIDEST_BUCKET)}-hour buckets")
    return "\n".join(lines)


STATION_SERIES_DESCRIPTION = f"""
One series per active station variable, with the same shape and bucketing as the field-sensor
history series. Bucket width follows the range, and buckets start at `date_from`:

{describe_tiers()}

A point is the bucket average plus its `sample_count`; empty buckets are absent, so rebuild the
gaps from `bucket_seconds`.
"""

STATION_EXPORT_DESCRIPTION = f"""
Every reading of the filtered range, newest first, as a download (UTF-8; the CSV starts with a
BOM so Excel reads the accents). A range holding more than {HISTORY_EXPORT_ROW_CAP} readings is
refused with `400` and `code: "export_too_large"` rather than truncated.
"""

STATION_EXPORT_TOO_LARGE = error_response(
    "Invalid range, or more rows than the export cap.",
    (
        "Too large",
        {
            "detail": "El rango seleccionado supera el máximo exportable.",
            "code": "export_too_large",
            "count": HISTORY_EXPORT_ROW_CAP + 1,
            "limit": HISTORY_EXPORT_ROW_CAP,
        },
    ),
)

STATION_LIST_RESPONSES = {
    200: WeatherStationSerializer(many=True),
    404: STATION_NOT_FOUND,
}
STATION_DETAIL_RESPONSES = {200: WeatherStationDetailSerializer, 404: STATION_NOT_FOUND}
STATION_SERIES_RESPONSES = {
    200: HistorySeriesSerializer(many=True),
    400: STATION_RANGE_ERRORS,
    404: STATION_NOT_FOUND,
}
STATION_READINGS_RESPONSES = {
    200: StationReadingPageSerializer,
    400: STATION_RANGE_ERRORS,
    404: STATION_NOT_FOUND,
}


def station_export_responses(media_type):
    return {
        (200, media_type): OpenApiResponse(
            response=OpenApiTypes.BINARY, description="The export file, as an attachment."
        ),
        400: STATION_EXPORT_TOO_LARGE,
        404: STATION_NOT_FOUND,
    }
