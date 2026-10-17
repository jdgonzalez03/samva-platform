from sensors.models import SemanticKey

DEFAULT_AVERAGE_HOURS = 6
MAX_AVERAGE_HOURS = 24

# Sensor variable feeding each input of the irrigation model.
IRRIGATION_INPUT_KEYS = {
    'moisture': SemanticKey.SOIL_MOISTURE,
    'temperature': SemanticKey.AIR_TEMPERATURE,
    'radiation': SemanticKey.SOLAR_RADIATION,
}

PREDICTION_MODELS = [
    {
        'key': 'fuzzy-irrigation',
        'technique': 'fuzzy',
        'target': 'irrigation',
    },
]
