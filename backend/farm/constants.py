from datetime import timedelta

from sensors.models import SemanticKey

# Window of the hourly series behind the overview charts and heatmap.
OVERVIEW_SERIES_SPAN = timedelta(days=7)
OVERVIEW_BUCKET = timedelta(hours=1)

# "24 h ago" is the latest reading inside this window, so a gap in the data
# yields no trend instead of comparing against a days-old value.
CHANGE_LOOKBACK = timedelta(hours=24)
CHANGE_TOLERANCE = timedelta(hours=1)

# Display order of the plot's current conditions; unlisted keys go last.
CONDITION_ORDER = (
    SemanticKey.SOIL_MOISTURE,
    SemanticKey.AIR_TEMPERATURE,
    SemanticKey.SOLAR_RADIATION,
    SemanticKey.RELATIVE_HUMIDITY,
)
