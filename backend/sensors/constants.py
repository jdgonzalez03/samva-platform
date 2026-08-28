from datetime import timedelta

HISTORY_MAX_RANGE_DAYS = 90
DEFAULT_HISTORY_RANGE_DAYS = 7

BUCKET_TIERS = (
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

CSV_HEADER = [
    'recorded_at',
    'plot',
    'sensor',
    'variable',
    'semantic_key',
    'value',
    'unit',
]

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
