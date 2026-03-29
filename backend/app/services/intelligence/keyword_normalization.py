"""Keyword normalization for maintenance actions, components, and issue signals.

Provides two main capabilities:
1. Normalize raw action text into a controlled vocabulary of action codes.
2. Extract technical keywords from free text for similarity matching.

The mappings are derived from inspection of the MC6068 maintenance dataset
and are designed to be extended as new data sources are onboarded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ── Normalized action vocabulary ──────────────────────────────────────────
# Each entry: (canonical_code, human_label, source_patterns)
# source_patterns are lowercase substrings checked against raw text.

@dataclass(frozen=True)
class ActionDefinition:
    code: str
    label: str
    category: str
    patterns: tuple[str, ...]


ACTION_DEFINITIONS: list[ActionDefinition] = [
    ActionDefinition("oil_change", "Oil Change", "lubrication",
                     ("oil change", "changed oil", "changed engine oil", "changed comp oil")),
    ActionDefinition("oil_inspection", "Oil Inspection", "lubrication",
                     ("checked oil", "oil level", "oil sample", "oil condition", "topped off oil",
                      "topped up oil", "added oil")),
    ActionDefinition("filter_replacement", "Filter Replacement", "filtration",
                     ("replaced filter", "changed filter", "new filter", "installed filter",
                      "replaced air filter", "changed air filter")),
    ActionDefinition("filter_inspection", "Filter Check", "filtration",
                     ("checked filter", "inspected filter", "filter condition",
                      "blew out filter", "cleaned filter")),
    ActionDefinition("spark_plug_replacement", "Spark Plug Replacement", "ignition",
                     ("replaced spark plug", "changed spark plug", "new spark plug",
                      "installed plug", "replaced plug", "changed plug")),
    ActionDefinition("spark_plug_inspection", "Spark Plug Inspection", "ignition",
                     ("checked plug", "inspected plug", "plug gap", "gapped plug",
                      "regapped plug")),
    ActionDefinition("valve_inspection", "Valve Inspection", "mechanical",
                     ("valve inspection", "inspected valve", "checked valve",
                      "valve condition", "valve clearance", "lash")),
    ActionDefinition("valve_replacement", "Valve Replacement", "mechanical",
                     ("replaced valve", "installed valve", "new valve")),
    ActionDefinition("adjustment", "Adjustment / Calibration", "calibration",
                     ("adjusted", "adjustment", "calibrat", "tuned", "set point",
                      "setpoint", "re-set", "reset")),
    ActionDefinition("belt_replacement", "Belt Replacement", "mechanical",
                     ("replaced belt", "changed belt", "new belt", "installed belt")),
    ActionDefinition("hose_repair", "Hose Repair / Replacement", "mechanical",
                     ("replaced hose", "hose leak", "new hose", "tightened hose")),
    ActionDefinition("gasket_seal_repair", "Gasket / Seal Repair", "sealing",
                     ("replaced gasket", "replaced seal", "new gasket", "new seal",
                      "gasket leak", "seal leak", "packing")),
    ActionDefinition("coolant_service", "Coolant Service", "cooling",
                     ("coolant", "antifreeze", "topped off coolant", "coolant change",
                      "coolant level", "coolant leak")),
    ActionDefinition("fuel_system_service", "Fuel System Service", "fuel",
                     ("fuel pressure", "fuel valve", "btu", "fuel curve", "fuel bottle",
                      "fuel line", "fuel regulator")),
    ActionDefinition("electrical_repair", "Electrical Repair", "electrical",
                     ("wiring", "sensor replaced", "scanner", "control panel",
                      "harness", "connector")),
    ActionDefinition("leak_repair", "Leak Repair", "sealing",
                     ("leak repair", "fixed leak", "repaired leak", "stopped leak",
                      "tightened fitting")),
    ActionDefinition("component_replacement", "Component Replacement", "mechanical",
                     ("replaced", "installed", "changed")),
    ActionDefinition("inspection", "General Inspection", "inspection",
                     ("inspected", "checked", "observed", "visual inspection",
                      "walk around")),
    ActionDefinition("cleaning", "Cleaning", "maintenance",
                     ("cleaned", "blew out", "washed", "emptied")),
    ActionDefinition("tightening", "Tightening", "mechanical",
                     ("tightened", "torqued", "retorqued")),
    ActionDefinition("test_run", "Test Run", "verification",
                     ("test run", "started unit", "loaded unit", "started and loaded",
                      "ran unit", "load test")),
    ActionDefinition("emergency_repair", "Emergency Repair", "emergency",
                     ("emergency", "urgent", "critical failure", "breakdown")),
    ActionDefinition("routine_inspection", "Routine PM Inspection", "inspection",
                     ("pm", "preventive", "routine", "scheduled")),
]

_ACTION_LOOKUP: dict[str, ActionDefinition] = {a.code: a for a in ACTION_DEFINITIONS}


# ── Technical keyword lexicon ─────────────────────────────────────────────
# Used for similarity matching and note analysis.

TECHNICAL_KEYWORDS: set[str] = {
    "detonation", "detination", "detnation",
    "leak", "leaking", "leaks",
    "pressure", "suction", "discharge",
    "valve", "valves",
    "fuel", "btu",
    "oil", "lube", "lubrication",
    "coolant", "temperature", "overheating", "water",
    "filter", "air filter",
    "spark", "plug", "plugs", "ignition",
    "hose", "gasket", "seal", "packing",
    "wiring", "sensor", "scanner", "panel", "electrical",
    "belt", "piston", "cylinder", "bearing",
    "shutdown", "vibration", "noise",
    "compressor", "engine",
    "bellows", "radiator",
    "replaced", "installed", "adjusted", "tuned",
    "calibrated", "inspected", "checked", "cleaned",
    "tightened", "repaired", "started", "loaded",
}

# Compound technical phrases recognized as single tokens
COMPOUND_KEYWORDS: dict[str, str] = {
    "spark plug": "spark_plug",
    "air filter": "air_filter",
    "oil change": "oil_change",
    "oil sample": "oil_sample",
    "fuel pressure": "fuel_pressure",
    "fuel curve": "fuel_curve",
    "load test": "load_test",
    "test run": "test_run",
    "shut down": "shutdown",
    "start up": "startup",
}

# ── Component vocabulary ──────────────────────────────────────────────────

COMPONENT_MAP: dict[str, str] = {
    "spark plug": "spark_plug",
    "plug": "spark_plug",
    "plugs": "spark_plug",
    "air filter": "air_filter",
    "filter": "filter",
    "oil": "oil_system",
    "coolant": "cooling_system",
    "valve": "valve",
    "belt": "belt",
    "hose": "hose",
    "gasket": "gasket",
    "seal": "seal",
    "sensor": "sensor",
    "scanner": "sensor",
    "wiring": "wiring",
    "piston": "piston",
    "cylinder": "cylinder",
    "bearing": "bearing",
    "packing": "packing",
    "fuel": "fuel_system",
    "btu": "fuel_system",
    "bellows": "bellows",
    "compressor": "compressor_unit",
    "engine": "engine",
    "radiator": "radiator",
    "pressure": "pressure_system",
}


@dataclass
class NormalizedAction:
    """Result of normalizing a raw action string."""
    code: str
    label: str
    category: str
    confidence: float  # how well the raw text matched
    raw_text: str


@dataclass
class KeywordExtractionResult:
    """Keywords and compound phrases extracted from free text."""
    single_keywords: list[str] = field(default_factory=list)
    compound_keywords: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    all_tokens: list[str] = field(default_factory=list)


def normalize_action(raw_text: str) -> NormalizedAction:
    """Map raw action text to the closest controlled action code.

    Tries compound / specific patterns first, then falls back to broader
    patterns. Returns a NormalizedAction with a confidence indicator.
    """
    if not raw_text:
        return NormalizedAction(
            code="unknown", label="Unknown Action", category="unknown",
            confidence=0.0, raw_text=raw_text,
        )

    text_lower = raw_text.lower().strip()

    # Phase 1: exact compound pattern match (highest confidence)
    for defn in ACTION_DEFINITIONS:
        for pattern in defn.patterns:
            if len(pattern.split()) > 1 and pattern in text_lower:
                return NormalizedAction(
                    code=defn.code, label=defn.label, category=defn.category,
                    confidence=0.9, raw_text=raw_text,
                )

    # Phase 2: single-word pattern match
    for defn in ACTION_DEFINITIONS:
        for pattern in defn.patterns:
            if len(pattern.split()) == 1 and pattern in text_lower:
                return NormalizedAction(
                    code=defn.code, label=defn.label, category=defn.category,
                    confidence=0.7, raw_text=raw_text,
                )

    return NormalizedAction(
        code="unknown", label="Unknown Action", category="unknown",
        confidence=0.0, raw_text=raw_text,
    )


def normalize_action_batch(raw_texts: list[str]) -> list[NormalizedAction]:
    """Normalize a list of raw action strings."""
    return [normalize_action(t) for t in raw_texts]


def extract_keywords(text: str) -> KeywordExtractionResult:
    """Extract technical keywords and compound phrases from free text.

    Returns both individual keyword tokens and recognized compound
    phrases (e.g. 'spark plug' → 'spark_plug').
    """
    if not text:
        return KeywordExtractionResult()

    text_lower = text.lower()

    compounds: list[str] = []
    for phrase, token in COMPOUND_KEYWORDS.items():
        if phrase in text_lower:
            compounds.append(token)

    words = re.findall(r"[a-z]+", text_lower)
    singles = [w for w in words if w in TECHNICAL_KEYWORDS]

    components: list[str] = []
    for phrase, comp in COMPONENT_MAP.items():
        if phrase in text_lower and comp not in components:
            components.append(comp)

    all_tokens = list(set(singles + compounds))

    return KeywordExtractionResult(
        single_keywords=singles,
        compound_keywords=compounds,
        components=components,
        all_tokens=all_tokens,
    )


def extract_keyword_set(text: str) -> set[str]:
    """Convenience: return a flat set of all keyword tokens from text."""
    result = extract_keywords(text)
    return set(result.all_tokens)


def get_action_definition(code: str) -> ActionDefinition | None:
    """Look up an action definition by its canonical code."""
    return _ACTION_LOOKUP.get(code)


def get_action_label(code: str) -> str:
    """Return human-readable label for an action code."""
    defn = _ACTION_LOOKUP.get(code)
    return defn.label if defn else code.replace("_", " ").title()
