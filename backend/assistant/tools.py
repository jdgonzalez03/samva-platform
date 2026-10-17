import inspect
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count
from django.utils import timezone

from farm.models import Farm, Plot
from farm.utils import build_conditions
from predictions.constants import DEFAULT_AVERAGE_HOURS, MAX_AVERAGE_HOURS
from predictions.utils import MissingSensorData, create_irrigation_prediction
from sensors.models import FieldSensor
from sensors.serializers import FieldSensorSerializer


class ToolError(Exception):
    """A failure the model should read and explain, not a server error."""


def _matching(queryset, reference, noun):
    """One row of `queryset` named or numbered by `reference`.

    Small models pass whatever the user typed ("el rodeo", "lote 3", "3"), so an exact name
    wins over a partial one and a bare number is tried as the id.
    """
    reference = str(reference).strip()
    if not reference:
        raise ToolError(f"Tell me which {noun}.")

    if reference.isdigit():
        by_id = queryset.filter(pk=int(reference)).first()
        if by_id:
            return by_id

    exact = list(queryset.filter(name__iexact=reference)[:2])
    if len(exact) == 1:
        return exact[0]

    partial = list(queryset.filter(name__icontains=reference))
    if len(partial) == 1:
        return partial[0]

    options = [str(row) for row in (partial or queryset)]
    if partial:
        raise ToolError(f'Several {noun}s match "{reference}": {", ".join(options)}.')
    raise ToolError(f'No {noun} matches "{reference}". Available: {", ".join(options) or "none"}.')


def _owned_farms(user):
    return Farm.objects.filter(owner__user=user).order_by("name", "id")


def _owned_plots(user):
    return (
        Plot.objects.filter(farm__owner__user=user)
        .select_related("farm")
        .order_by("farm__name", "name", "id")
    )


def _resolve_plot(user, plot):
    return _matching(_owned_plots(user), plot, "plot")


def _irrigation_summary(prediction):
    return {
        "plot": prediction.plot.name,
        "irrigation_time_minutes": float(prediction.irrigation_time_minutes),
        "level": prediction.output_label,
        "average_soil_moisture_percent": float(prediction.avg_moisture),
        "average_air_temperature_celsius": float(prediction.avg_temperature),
        "average_solar_radiation_w_m2": float(prediction.avg_radiation),
        "averaged_over_hours": prediction.avg_period_hours,
        "calculated_at": prediction.requested_at,
    }


def _listing(key, rows, note=None):
    # Small models miscount long lists and read an empty one as missing data, so the total
    # comes precomputed and an empty result says so in words.
    listing = {"count": len(rows), key: rows}
    if not rows:
        note = note or f"The user has no {key} registered."
    if note:
        listing["note"] = note
    return listing


def _narrow(user, queryset, farm, farm_lookup, plot_lookup):
    """Filter a listing by the optional `farm` argument, without failing on a bad one.

    Small models fill this optional argument on their own, often with a plot name taken
    from earlier in the chat, so a plot name narrows to that plot and anything else lists
    everything with a note instead of answering with an error.
    """
    if not farm:
        return queryset, None
    try:
        return queryset.filter(**{farm_lookup: _matching(_owned_farms(user), farm, "farm")}), None
    except ToolError:
        pass
    try:
        plot = _matching(_owned_plots(user), farm, "plot")
        return queryset.filter(**{plot_lookup: plot.pk}), None
    except ToolError:
        return queryset, f'No farm or plot matches "{farm}", so everything is listed.'


def list_farms(user):
    farms = _owned_farms(user).annotate(plot_count=Count("plots"))
    return _listing(
        "farms",
        [
            {"id": farm.pk, "name": farm.name, "address": farm.address, "plots": farm.plot_count}
            for farm in farms
        ],
    )


def list_plots(user, farm=None):
    plots, note = _narrow(
        user,
        _owned_plots(user).with_sensor_count().order_by("farm__name", "name", "id"),
        farm,
        farm_lookup="farm",
        plot_lookup="pk",
    )
    rows = [
        {
            "id": plot.pk,
            "name": plot.name,
            "farm": plot.farm.name,
            "area_hectares": None if plot.area_hectares is None else float(plot.area_hectares),
            "active_sensors": plot.sensor_count,
        }
        for plot in plots
    ]
    return _listing("plots", rows, note)


def get_plot_conditions(user, plot):
    plot = _resolve_plot(user, plot)
    conditions = [
        {
            "variable": condition["name"],
            "value": condition["value"],
            "unit": condition["unit"],
            "level": condition["level"],
            "change_24h": condition["change_24h"],
            "recorded_at": condition["recorded_at"],
        }
        for condition in build_conditions(plot, timezone.now())
    ]
    if not conditions:
        return {"plot": plot.name, "farm": plot.farm.name, "note": "This plot has no readings."}
    return {"plot": plot.name, "farm": plot.farm.name, "conditions": conditions}


def list_sensors(user, farm=None):
    sensors = (
        FieldSensor.objects.filter(plot__farm__owner__user=user)
        .select_related("plot")
        .prefetch_related("sensor_variables__env_variable")
        .order_by("plot__name", "name", "id")
    )
    sensors, note = _narrow(user, sensors, farm, farm_lookup="plot__farm", plot_lookup="plot_id")
    rows = [
        {
            "name": sensor["name"],
            "serial_number": sensor["serial_number"],
            "plot": sensor["plot_name"],
            "status": sensor["status"],
            "last_seen_at": sensor["last_seen_at"],
            "variables": [variable["name"] for variable in sensor["variables"]],
        }
        for sensor in FieldSensorSerializer(sensors, many=True).data
    ]
    return _listing("sensors", rows, note)


def get_latest_irrigation(user, plot):
    plot = _resolve_plot(user, plot)
    prediction = plot.irrigation_predictions.order_by("-requested_at", "-id").first()
    if prediction is None:
        return {"plot": plot.name, "note": "This plot has no irrigation prescription yet."}
    return _irrigation_summary(prediction)


def calculate_irrigation(user, plot, hours=DEFAULT_AVERAGE_HOURS):
    plot = _resolve_plot(user, plot)
    try:
        hours = int(hours)
    except TypeError, ValueError:
        hours = DEFAULT_AVERAGE_HOURS
    hours = min(max(hours, 1), MAX_AVERAGE_HOURS)

    try:
        prediction = create_irrigation_prediction(plot, hours)
    except MissingSensorData as error:
        raise ToolError(
            f"Cannot calculate irrigation for {plot.name}: no recent readings for "
            f"{', '.join(error.missing)}."
        ) from error
    return _irrigation_summary(prediction)


TOOLS = {
    "list_farms": list_farms,
    "list_plots": list_plots,
    "get_plot_conditions": get_plot_conditions,
    "list_sensors": list_sensors,
    "get_latest_irrigation": get_latest_irrigation,
    "calculate_irrigation": calculate_irrigation,
}


def _function(name, description, properties=None, required=()):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties or {},
                "required": list(required),
            },
        },
    }


PLOT_PARAMETER = {"type": "string", "description": "Plot name as the user wrote it, or its id."}
FARM_PARAMETER = {
    "type": "string",
    "description": "Only when the user explicitly names a farm: its name or id. "
    "Omit it otherwise, so every farm is listed.",
}

TOOL_SCHEMAS = [
    _function("list_farms", "List the user's farms with their address and number of plots."),
    _function(
        "list_plots",
        "List the user's plots (lots) with their farm, area and number of active sensors.",
        {"farm": FARM_PARAMETER},
    ),
    _function(
        "get_plot_conditions",
        "Latest reading of every variable of a plot (soil moisture, temperature, radiation...)"
        " with its fuzzy level (low/medium/high) and 24 h change.",
        {"plot": PLOT_PARAMETER},
        required=["plot"],
    ),
    _function(
        "list_sensors",
        "List the user's field sensors with their plot, variables and status "
        "(online, offline, never_seen, inactive).",
        {"farm": FARM_PARAMETER},
    ),
    _function(
        "get_latest_irrigation",
        "Latest irrigation prescription already calculated for a plot: irrigation time in "
        "minutes and the averages it used.",
        {"plot": PLOT_PARAMETER},
        required=["plot"],
    ),
    _function(
        "calculate_irrigation",
        "Calculate and save a new irrigation prescription for a plot with the fuzzy-logic "
        "model, from the average of its recent readings.",
        {
            "plot": PLOT_PARAMETER,
            "hours": {
                "type": "integer",
                "description": f"Hours of readings to average (1-{MAX_AVERAGE_HOURS}), "
                f"default {DEFAULT_AVERAGE_HOURS}.",
            },
        },
        required=["plot"],
    ),
]


def run_tool(user, name, arguments):
    """Run a tool for `user` and return a JSON-safe result; failures become `{"error"}`."""
    tool = TOOLS.get(name)
    if tool is None:
        return {"error": f'Unknown tool "{name}".'}

    # Models sometimes invent parameters or send `null` for optional ones.
    signature = inspect.signature(tool)
    arguments = {
        key: value
        for key, value in arguments.items()
        if key in signature.parameters and key != "user" and value not in (None, "")
    }
    try:
        signature.bind(user, **arguments)
    except TypeError:
        return {"error": f'Missing arguments for "{name}".'}

    try:
        result = tool(user, **arguments)
    except ToolError as error:
        return {"error": str(error)}

    # Decimals and datetimes become plain JSON values for both the model and the client.
    return json.loads(json.dumps(result, cls=DjangoJSONEncoder))
