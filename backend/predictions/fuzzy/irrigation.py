"""
Fuzzy (Mamdani) model that predicts how many minutes a plot should be irrigated.

Inputs are averages of recent sensor readings:

- soil moisture (%), air temperature (°C) and solar radiation (W/m²).

The membership functions and the 27 rules come from the agronomic study the
model is based on; change them only together with the study's authors.

Each universe is sampled as ``np.arange(low, high, 1.0)``, which stops one step
short of ``high`` (e.g. temperature reaches 24, not 25, and irrigation time 31,
not 32). skfuzzy clips inputs to the sampled universe, and the centroid is
computed over it, so widening a universe changes the predictions.
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


@dataclass(frozen=True)
class MembershipFunction:
    shape: Literal['trap', 'tri']
    points: tuple[float, ...]

    def evaluate(self, universe: np.ndarray) -> np.ndarray:
        if self.shape == 'trap':
            return fuzz.trapmf(universe, list(self.points))
        return fuzz.trimf(universe, list(self.points))


@dataclass(frozen=True)
class FuzzyVariable:
    unit: str
    bounds: tuple[float, float]
    terms: dict[str, MembershipFunction]

    @property
    def universe(self) -> np.ndarray:
        return np.arange(*self.bounds, 1.0)

    def clip(self, value: float) -> float:
        low, high = self.bounds
        return min(max(value, low), high)


def trap(*points: float) -> MembershipFunction:
    return MembershipFunction('trap', points)


def tri(*points: float) -> MembershipFunction:
    return MembershipFunction('tri', points)


INPUTS: dict[str, FuzzyVariable] = {
    'moisture': FuzzyVariable(
        unit='%',
        bounds=(0.0, 52.56),
        terms={
            'low': trap(-20.0, -20.0, 15.0, 30.0),
            'medium': tri(15.0, 30.0, 45.0),
            'high': trap(30.0, 45.0, 65.0, 65.0),
        },
    ),
    'temperature': FuzzyVariable(
        unit='°C',
        bounds=(0.0, 25.0),
        terms={
            'low': trap(-2.0, -2.0, 10.0, 15.0),
            'medium': tri(10.0, 15.0, 20.0),
            'high': trap(15.0, 20.0, 25.0, 25.0),
        },
    ),
    'radiation': FuzzyVariable(
        unit='W/m²',
        bounds=(0.0, 3500.0),
        terms={
            'low': trap(-10.0, -10.0, 10.0, 200.0),
            'medium': trap(10.0, 200.0, 1000.0, 1400.0),
            'high': trap(1000.0, 1400.0, 3550.0, 3550.0),
        },
    ),
}

OUTPUT = FuzzyVariable(
    unit='min',
    bounds=(0.0, 32.0),
    terms={
        'nothing': trap(-20.0, -20.0, 0.0, 8.0),
        'very_little': tri(0.0, 8.0, 16.0),
        'little': tri(8.0, 16.0, 24.0),
        'long': tri(16.0, 24.0, 32.0),
        'very_long': trap(24.0, 32.0, 40.0, 40.0),
    },
)

# (moisture, temperature, radiation) → irrigation time
RULES: dict[tuple[str, str, str], str] = {
    ('low', 'low', 'low'): 'very_long',
    ('low', 'low', 'medium'): 'very_long',
    ('low', 'low', 'high'): 'very_long',
    ('low', 'medium', 'low'): 'long',
    ('low', 'medium', 'medium'): 'long',
    ('low', 'medium', 'high'): 'little',
    ('low', 'high', 'low'): 'very_long',
    ('low', 'high', 'medium'): 'very_little',
    ('low', 'high', 'high'): 'nothing',
    ('medium', 'low', 'low'): 'little',
    ('medium', 'low', 'medium'): 'little',
    ('medium', 'low', 'high'): 'little',
    ('medium', 'medium', 'low'): 'little',
    ('medium', 'medium', 'medium'): 'little',
    ('medium', 'medium', 'high'): 'very_little',
    ('medium', 'high', 'low'): 'long',
    ('medium', 'high', 'medium'): 'very_little',
    ('medium', 'high', 'high'): 'nothing',
    ('high', 'low', 'low'): 'nothing',
    ('high', 'low', 'medium'): 'nothing',
    ('high', 'low', 'high'): 'nothing',
    ('high', 'medium', 'low'): 'nothing',
    ('high', 'medium', 'medium'): 'nothing',
    ('high', 'medium', 'high'): 'nothing',
    ('high', 'high', 'low'): 'nothing',
    ('high', 'high', 'medium'): 'nothing',
    ('high', 'high', 'high'): 'nothing',
}


@dataclass(frozen=True)
class IrrigationResult:
    minutes: float
    label: str
    # Degree (0–1) to which each input belongs to each of its terms.
    input_memberships: dict[str, dict[str, float]]
    # Firing strength (0–1) of each output term after rule aggregation.
    output_activation: dict[str, float]
    # Inputs that were outside their bounds and were clipped to them.
    clipped_inputs: list[str]


def predict_irrigation(
    moisture: float, temperature: float, radiation: float
) -> IrrigationResult:
    raw_inputs = {
        'moisture': moisture,
        'temperature': temperature,
        'radiation': radiation,
    }
    inputs = {name: INPUTS[name].clip(value) for name, value in raw_inputs.items()}
    clipped_inputs = [name for name in inputs if inputs[name] != raw_inputs[name]]

    # skfuzzy stores every simulation's state on the system's own objects, so a
    # system shared across calls would grow with each distinct input and is not
    # thread-safe; building one per prediction costs well under 100 ms.
    antecedents, consequent, system = _build_control_system()
    simulation = ctrl.ControlSystemSimulation(system)
    for name, value in inputs.items():
        simulation.input[name] = value
    simulation.compute()

    minutes = round(float(simulation.output['irrigation_time']), 2)
    return IrrigationResult(
        minutes=minutes,
        label=_dominant_output_term(minutes),
        input_memberships={
            name: _term_degrees(antecedent, simulation)
            for name, antecedent in antecedents.items()
        },
        output_activation=_term_degrees(consequent, simulation),
        clipped_inputs=clipped_inputs,
    )


def input_term_degrees(name: str, value: float) -> dict[str, float]:
    """Degree of a single reading in each term of the model input `name`.

    Uses the same sampled universe and clipping as the inference, so a reading
    is classified exactly as the prediction would see it.
    """
    variable = INPUTS[name]
    universe = variable.universe
    # skfuzzy clips to the sampled universe, which ends one step short of the bounds.
    clipped = min(max(value, universe[0]), universe[-1])
    return {
        term: round(float(fuzz.interp_membership(universe, mf.evaluate(universe), clipped)), 3)
        for term, mf in variable.terms.items()
    }


def membership_definitions() -> dict:
    """Shape of every membership function, enough for a client to plot them."""
    variables = {**INPUTS, 'irrigation_time': OUTPUT}
    return {
        name: {
            'unit': variable.unit,
            'bounds': list(variable.bounds),
            'terms': {
                term: {'shape': mf.shape, 'points': list(mf.points)}
                for term, mf in variable.terms.items()
            },
        }
        for name, variable in variables.items()
    }


def _build_control_system() -> tuple[
    dict[str, ctrl.Antecedent], ctrl.Consequent, ctrl.ControlSystem
]:
    antecedents = {
        name: _with_terms(ctrl.Antecedent(variable.universe, name), variable)
        for name, variable in INPUTS.items()
    }
    consequent = _with_terms(
        ctrl.Consequent(OUTPUT.universe, 'irrigation_time'), OUTPUT
    )
    rules = [
        ctrl.Rule(
            antecedents['moisture'][moisture]
            & antecedents['temperature'][temperature]
            & antecedents['radiation'][radiation],
            consequent[output],
        )
        for (moisture, temperature, radiation), output in RULES.items()
    ]
    return antecedents, consequent, ctrl.ControlSystem(rules)


def _with_terms(fuzzy_var, variable: FuzzyVariable):
    for term, mf in variable.terms.items():
        fuzzy_var[term] = mf.evaluate(fuzzy_var.universe)
    return fuzzy_var


def _term_degrees(fuzzy_var, simulation) -> dict[str, float]:
    return {
        term: round(float(fuzzy_var.terms[term].membership_value[simulation]), 3)
        for term in fuzzy_var.terms
    }


def _dominant_output_term(minutes: float) -> str:
    universe = OUTPUT.universe
    degrees = {
        term: fuzz.interp_membership(universe, mf.evaluate(universe), minutes)
        for term, mf in OUTPUT.terms.items()
    }
    return max(degrees, key=degrees.get)
