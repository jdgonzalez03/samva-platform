import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

from typing import Any, Optional, Union


# Mapping from crisp value to dominant linguistic label
OUTPUT_THRESHOLDS: list[tuple[float, str]] = [
    (4,   "Nothing"),
    (10,  "VeryLittle"),
    (18,  "Little"),
    (26,  "Long"),
    (32,  "VeryLong"),
]


def _crisp_to_label(value: float) -> str:
    """Map a crisp output value to its dominant linguistic label."""
    for threshold, label in OUTPUT_THRESHOLDS:
        if value <= threshold:
            return label
    return "VeryLong"


def _check_in_range(name: str, value: float, bounds: tuple[float, float]) -> None:
    """Raise ValueError if *value* falls outside *bounds* (inclusive)."""
    lo, hi = bounds
    if not lo <= value <= hi:
        raise ValueError(
            f"{name} must be in [{lo}, {hi}], got {value}"
        )


class FuzzyIrrigationEngine:
    """
    Fuzzy logic engine for irrigation time prediction.

    Uses three inputs (soil moisture, air temperature, solar radiation)
    to infer an irrigation duration via 27 Mamdani-style rules.

    Usage:
        engine = FuzzyIrrigationEngine()
        result = engine.run(moisture=32.0, temperature=18.5, radiation=850.0)
    """

    INPUT_RANGES: dict[str, tuple[float, float]] = {
        "moisture": (0.0, 52.56),
        "temperature": (0.0, 25.0),
        "radiation": (0.0, 3500.0),
    }

    def __init__(self) -> None:
        self._control_system: Optional[ctrl.ControlSystem] = None
        self._antecedents: dict[str, ctrl.Antecedent] = {}
        self._consequents: dict[str, ctrl.Consequent] = {}


    def run(self, moisture: float, temperature: float, radiation: float) -> dict[str, Any]:
        """
        Run fuzzy inference and return the result.

        Parameters
        ----------
        moisture : float - Average soil moisture (0–52.56).
        temperature : float - Average air temperature (0–25 °C).
        radiation : float - Average solar radiation (0–3500 W/m²).

        Returns
        -------
        dict
            {
                "irrigation_time_minutes": float,
                "output_label": str,
                "chart_data": { ... }
            }
        """
        self._validate_inputs(moisture, temperature, radiation)
        self._build_system()

        sim = ctrl.ControlSystemSimulation(self._control_system)

        sim.input["Moisture"] = moisture
        sim.input["Temperature"] = temperature
        sim.input["Radiation"] = radiation
        sim.compute()

        crisp_value = round(float(sim.output["IrrTime"]), 2)

        return {
            "irrigation_time_minutes": crisp_value,
            "output_label": _crisp_to_label(crisp_value),
            "chart_data": self._build_chart_data(
                sim, crisp_value, moisture, temperature, radiation,
            ),
        }


    def _validate_inputs(self, moisture: float, temperature: float, radiation: float):
        """Raise ValueError if any input is outside its expected range."""
        _check_in_range("moisture", moisture, self.INPUT_RANGES["moisture"])
        _check_in_range("temperature", temperature, self.INPUT_RANGES["temperature"])
        _check_in_range("radiation", radiation, self.INPUT_RANGES["radiation"])

    def _build_system(self) -> None:
        """Build fuzzy variables, membership functions and rules once."""
        if self._control_system is not None:
            return

        self._build_variables()
        rules = self._build_rules()
        self._control_system = ctrl.ControlSystem(rules)

    def _build_variables(self) -> None:
        """Create antecedents, consequents and their membership functions."""
        # -- Antecedents --
        Moisture = ctrl.Antecedent(np.arange(0.0, 52.56, 1.0), "Moisture")
        Temperature = ctrl.Antecedent(np.arange(0.0, 25.0, 1.0), "Temperature")
        Radiation = ctrl.Antecedent(np.arange(0.0, 3500.0, 1.0), "Radiation")

        # -- Consequent --
        IrrTime = ctrl.Consequent(np.arange(0.0, 32.0, 1.0), "IrrTime")

        # Moisture membership functions
        Moisture["LowM"] = fuzz.trapmf(Moisture.universe, [-20.0, -20.0, 15.0, 30.0])
        Moisture["MediumM"] = fuzz.trimf(Moisture.universe, [15.0, 30.0, 45.0])
        Moisture["HighM"] = fuzz.trapmf(Moisture.universe, [30.0, 45.0, 65.0, 65.0])

        # Temperature membership functions
        Temperature["LowT"] = fuzz.trapmf(Temperature.universe, [-2.0, -2.0, 10.0, 15.0])
        Temperature["MediumT"] = fuzz.trimf(Temperature.universe, [10.0, 15.0, 20.0])
        Temperature["HighT"] = fuzz.trapmf(Temperature.universe, [15.0, 20.0, 25.0, 25.0])

        # Radiation membership functions
        Radiation["LowR"] = fuzz.trapmf(Radiation.universe, [-10.0, -10.0, 10.0, 200.0])
        Radiation["MediumR"] = fuzz.trapmf(Radiation.universe, [10.0, 200.0, 1000.0, 1400.0])
        Radiation["HighR"] = fuzz.trapmf(Radiation.universe, [1000.0, 1400.0, 3550.0, 3550.0])

        # Irrigation time membership functions
        IrrTime["Nothing"] = fuzz.trapmf(IrrTime.universe, [-20.0, -20.0, 0.0, 8.0])
        IrrTime["VeryLittle"] = fuzz.trimf(IrrTime.universe, [0.0, 8.0, 16.0])
        IrrTime["Little"] = fuzz.trimf(IrrTime.universe, [8.0, 16.0, 24.0])
        IrrTime["Long"] = fuzz.trimf(IrrTime.universe, [16.0, 24.0, 32.0])
        IrrTime["VeryLong"] = fuzz.trapmf(IrrTime.universe, [24.0, 32.0, 40.0, 40.0])

        self._antecedents = {
            "Moisture": Moisture,
            "Temperature": Temperature,
            "Radiation": Radiation,
        }
        self._consequents = {"IrrTime": IrrTime}

    def _build_rules(self) -> list[ctrl.Rule]:
        """Build the 27 Mamdani-style rules (3 × 3 × 3 combinations)."""
        M = self._antecedents["Moisture"]
        T = self._antecedents["Temperature"]
        R = self._antecedents["Radiation"]
        O = self._consequents["IrrTime"]

        return [
            ctrl.Rule(M["LowM"] & T["LowT"] & R["LowR"], O["VeryLong"]),
            ctrl.Rule(M["LowM"] & T["LowT"] & R["MediumR"], O["VeryLong"]),
            ctrl.Rule(M["LowM"] & T["LowT"] & R["HighR"], O["VeryLong"]),
            ctrl.Rule(M["LowM"] & T["MediumT"] & R["LowR"], O["Long"]),
            ctrl.Rule(M["LowM"] & T["MediumT"] & R["MediumR"], O["Long"]),
            ctrl.Rule(M["LowM"] & T["MediumT"] & R["HighR"], O["Little"]),
            ctrl.Rule(M["LowM"] & T["HighT"] & R["LowR"], O["VeryLong"]),
            ctrl.Rule(M["LowM"] & T["HighT"] & R["MediumR"], O["VeryLittle"]),
            ctrl.Rule(M["LowM"] & T["HighT"] & R["HighR"], O["Nothing"]),
            ctrl.Rule(M["MediumM"] & T["LowT"] & R["LowR"], O["Little"]),
            ctrl.Rule(M["MediumM"] & T["LowT"] & R["MediumR"], O["Little"]),
            ctrl.Rule(M["MediumM"] & T["LowT"] & R["HighR"], O["Little"]),
            ctrl.Rule(M["MediumM"] & T["MediumT"] & R["LowR"], O["Little"]),
            ctrl.Rule(M["MediumM"] & T["MediumT"] & R["MediumR"], O["Little"]),
            ctrl.Rule(M["MediumM"] & T["MediumT"] & R["HighR"], O["VeryLittle"]),
            ctrl.Rule(M["MediumM"] & T["HighT"] & R["LowR"], O["Long"]),
            ctrl.Rule(M["MediumM"] & T["HighT"] & R["MediumR"], O["VeryLittle"]),
            ctrl.Rule(M["MediumM"] & T["HighT"] & R["HighR"], O["Nothing"]),
            ctrl.Rule(M["HighM"] & T["LowT"] & R["LowR"], O["Nothing"]),
            ctrl.Rule(M["HighM"] & T["LowT"] & R["MediumR"], O["Nothing"]),
            ctrl.Rule(M["HighM"] & T["LowT"] & R["HighR"], O["Nothing"]),
            ctrl.Rule(M["HighM"] & T["MediumT"] & R["LowR"], O["Nothing"]),
            ctrl.Rule(M["HighM"] & T["MediumT"] & R["MediumR"], O["Nothing"]),
            ctrl.Rule(M["HighM"] & T["MediumT"] & R["HighR"], O["Nothing"]),
            ctrl.Rule(M["HighM"] & T["HighT"] & R["LowR"], O["Nothing"]),
            ctrl.Rule(M["HighM"] & T["HighT"] & R["MediumR"], O["Nothing"]),
            ctrl.Rule(M["HighM"] & T["HighT"] & R["HighR"], O["Nothing"]),
        ]

    @staticmethod
    def _extract_mf_data(fuzzy_var) -> dict:
        """
        Extract (x, y) points for every membership function of a fuzzy variable.

        Returns a dict suitable for JSON serialisation and Chart.js rendering.
        """
        universe = fuzzy_var.universe.tolist()
        return {
            term_name: {
                "x": universe,
                "y": mf.mf.tolist(),
            }
            for term_name, mf in fuzzy_var.terms.items()
        }

    def _build_chart_data(
        self, sim: ctrl.ControlSystemSimulation, crisp_value: float, moisture: float, temperature: float,radiation: float ) -> dict:
        """Build chart data with membership curves and activated output area."""
        activated_y = (
            sim.output_membership_values.tolist()
            if hasattr(sim, "output_membership_values")
            else self._consequents["IrrTime"]["Nothing"].mf.tolist()
        )

        return {
            "moisture": self._extract_mf_data(self._antecedents["Moisture"]),
            "temperature": self._extract_mf_data(self._antecedents["Temperature"]),
            "radiation": self._extract_mf_data(self._antecedents["Radiation"]),
            "output": {
                **self._extract_mf_data(self._consequents["IrrTime"]),
                "activated": {
                    "x": self._consequents["IrrTime"].universe.tolist(),
                    "y": activated_y,
                },
            },
            "crisp_value": crisp_value,
            "inputs": {
                "moisture": moisture,
                "temperature": temperature,
                "radiation": radiation,
            },
        }
