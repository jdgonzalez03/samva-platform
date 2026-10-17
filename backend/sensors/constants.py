from datetime import timedelta

from sensors.models import SemanticKey

HISTORY_MAX_RANGE_DAYS = 90
DEFAULT_HISTORY_RANGE_DAYS = 7

BUCKET_TIERS = (
    (timedelta(hours=2), timedelta(minutes=10)),
    (timedelta(days=2), timedelta(minutes=15)),
    (timedelta(days=8), timedelta(hours=1)),
    (timedelta(days=40), timedelta(hours=6)),
)
WIDEST_BUCKET = timedelta(days=1)

READING_ORDER = ('-recorded_at', '-id')

VARIABLE_COLUMNS = (
    'sensor_variable__env_variable_id',
    'sensor_variable__env_variable__semantic_key',
    'sensor_variable__env_variable__name',
    'sensor_variable__env_variable__unit',
)

HISTORY_EXPORT_ROW_CAP = 50_000

# Without it, Excel on Windows reads the file as latin-1 and turns `°C` and `Radiación`
# into mojibake.
BOM_UTF8 = '\ufeff'

# (CSV column title, export record key) pairs; the JSON export carries every record key.
SENSOR_CSV_COLUMNS = (
    ('recorded_at', 'recorded_at'),
    ('plot', 'plot_name'),
    ('sensor', 'sensor_name'),
    ('variable', 'variable_name'),
    ('semantic_key', 'semantic_key'),
    ('value', 'value'),
    ('unit', 'unit'),
)

STATION_CSV_COLUMNS = (
    ('recorded_at', 'recorded_at'),
    ('station', 'station_name'),
    ('variable', 'variable_name'),
    ('semantic_key', 'semantic_key'),
    ('value', 'value'),
    ('unit', 'unit'),
)

EXPORT_COLUMNS = (
    'recorded_at',
    'sensor_variable__sensor__plot_id',
    'sensor_variable__sensor__plot__name',
    'sensor_variable__sensor_id',
    'sensor_variable__sensor__name',
    'sensor_variable__env_variable_id',
    'sensor_variable__env_variable__semantic_key',
    'sensor_variable__env_variable__name',
    'value',
    'sensor_variable__env_variable__unit',
)

# A weather measurement has no timestamp of its own: it inherits its snapshot's.
STATION_VARIABLE_FIELD = 'station_variable__env_variable'
STATION_TIME_FIELD = 'snapshot__recorded_at'
STATION_READING_ORDER = ('-snapshot__recorded_at', '-id')

STATION_EXPORT_COLUMNS = (
    'snapshot__recorded_at',
    'station_variable__station_id',
    'station_variable__station__name',
    'station_variable__env_variable_id',
    'station_variable__env_variable__semantic_key',
    'station_variable__env_variable__name',
    'value',
    'station_variable__env_variable__unit',
)

STATION_STATUSES = ('online', 'stale', 'never_seen', 'inactive')

# Six missed polls at the 5-minute Celery Beat cadence.
STATION_STALE_AFTER = timedelta(minutes=30)

STATION_SPARKLINE_KEY = SemanticKey.AIR_TEMPERATURE
STATION_SPARKLINE_SPAN = timedelta(hours=24)
STATION_SPARKLINE_BUCKET = timedelta(hours=1)

API_KEY_HEADER = 'X-API-Key'

# Tolerates a device clock running slightly ahead of the server; anything further out is a
# misconfigured clock, and storing it would put readings in the future of every chart.
INGEST_MAX_CLOCK_SKEW = timedelta(minutes=5)

# Three missed uploads at the slowest planned cadence (every 15 minutes).
SENSOR_OFFLINE_AFTER = timedelta(minutes=45)

# LoRaWAN payload v2 (one `[id u16][values…]` block per probe) travels on this fPort; the
# port versions the layout, so an older node is rejected instead of being misdecoded.
LORAWAN_PAYLOAD_FPORT = 3

# TTN wraps the `ApplicationUp` in this event envelope in its console and webhooks.
TTN_FORWARD_EVENT = 'as.up.data.forward'

MQTT_SOURCES = ('local', 'ttn')
MQTT_KEEPALIVE_SECONDS = 60
MQTT_RECONNECT_MIN_DELAY_SECONDS = 1
MQTT_RECONNECT_MAX_DELAY_SECONDS = 120

# WeatherLink v2 reports every temperature in °F; stored readings are °C like every other
# source, so these keys are converted before a field_key ever reads them.
WEATHERLINK_FAHRENHEIT_FIELDS = frozenset({
    'temp',
    'temp_in',
    'dew_point',
    'dew_point_in',
    'heat_index',
    'heat_index_in',
    'wind_chill',
    'wet_bulb',
    'thw_index',
    'thsw_index',
})
