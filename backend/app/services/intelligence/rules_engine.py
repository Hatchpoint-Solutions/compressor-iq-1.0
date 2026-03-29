"""Rules engine for issue inference and action resolution mapping.

Implements:
- Issue taxonomy with detection keywords and severity
- Action → issue category mapping (which actions indicate which issues)
- Issue → recommended action mapping (what to do for each issue)
- Resolution precedence rules (when multiple signals compete)

The rules are derived from inspection of the MC6068 maintenance dataset
and standard compressor maintenance practices. They are documented here
as explicit, auditable business logic rather than opaque model weights.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── Issue taxonomy ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class IssueCategoryRule:
    name: str
    label: str
    severity_default: str
    detection_keywords: tuple[str, ...]
    description: str


ISSUE_TAXONOMY: list[IssueCategoryRule] = [
    IssueCategoryRule(
        name="detonation",
        label="Detonation / Knock",
        severity_default="high",
        detection_keywords=("detonation", "detination", "detnation", "knock", "detonating"),
        description="Engine or compressor detonation events — often linked to spark plugs, "
                    "fuel/BTU settings, or ignition timing.",
    ),
    IssueCategoryRule(
        name="leak",
        label="Leak (Oil / Coolant / Gas)",
        severity_default="medium",
        detection_keywords=("leak", "leaking", "leaks", "seeping"),
        description="Fluid leaks from hoses, fittings, gaskets, seals, or other components.",
    ),
    IssueCategoryRule(
        name="pressure_abnormality",
        label="Pressure Abnormality",
        severity_default="medium",
        detection_keywords=("pressure", "suction", "discharge", "over-pressure",
                            "low pressure", "high pressure"),
        description="Abnormal suction or discharge pressure readings, relief valve trips, "
                    "or pressure instability.",
    ),
    IssueCategoryRule(
        name="fuel_system",
        label="Fuel System Issue",
        severity_default="medium",
        detection_keywords=("fuel", "btu", "fuel curve", "fuel pressure",
                            "fuel valve", "gas quality"),
        description="Fuel supply, BTU calibration, fuel valve, or gas composition issues.",
    ),
    IssueCategoryRule(
        name="valve_failure",
        label="Valve Failure / Wear",
        severity_default="medium",
        detection_keywords=("valve", "lash", "valve clearance", "valve spring",
                            "valve seat"),
        description="Compressor or engine valve degradation, wear, or failure.",
    ),
    IssueCategoryRule(
        name="cooling_system",
        label="Cooling System Issue",
        severity_default="medium",
        detection_keywords=("coolant", "temperature", "overheating", "overheat",
                            "radiator", "water pump", "thermostat"),
        description="Overheating, coolant loss, radiator, or thermostat problems.",
    ),
    IssueCategoryRule(
        name="electrical",
        label="Electrical / Sensor Issue",
        severity_default="medium",
        detection_keywords=("wiring", "sensor", "scanner", "panel", "fault code",
                            "electrical", "connector", "harness"),
        description="Sensor failures, wiring damage, control panel faults, or "
                    "instrument issues.",
    ),
    IssueCategoryRule(
        name="lubrication",
        label="Lubrication / Oil Service",
        severity_default="medium",
        detection_keywords=("oil", "lube", "lubrication", "oil pressure",
                            "oil sample", "oil change"),
        description="Engine or compressor oil issues including degradation, "
                    "contamination, low level, or scheduled service.",
    ),
    IssueCategoryRule(
        name="filter_maintenance",
        label="Filter Maintenance",
        severity_default="low",
        detection_keywords=("filter", "air filter", "oil filter", "fuel filter",
                            "restriction"),
        description="Air, oil, or fuel filter replacement or cleaning.",
    ),
    IssueCategoryRule(
        name="shutdown",
        label="Unplanned Shutdown",
        severity_default="high",
        detection_keywords=("shutdown", "shut down", "down on", "tripped",
                            "unit down", "not running"),
        description="Unplanned unit shutdown or trip requiring investigation.",
    ),
    IssueCategoryRule(
        name="vibration_noise",
        label="Vibration / Noise",
        severity_default="medium",
        detection_keywords=("vibration", "noise", "knocking", "rattling"),
        description="Abnormal vibration or noise indicating mechanical wear.",
    ),
    IssueCategoryRule(
        name="seal_gasket",
        label="Seal / Gasket / Packing",
        severity_default="medium",
        detection_keywords=("seal", "gasket", "packing", "o-ring"),
        description="Seal, gasket, or packing degradation or failure.",
    ),
    IssueCategoryRule(
        name="ignition_system",
        label="Ignition System Issue",
        severity_default="medium",
        detection_keywords=("spark plug", "ignition", "misfire", "plug gap",
                            "ignition timing", "ignition wire"),
        description="Spark plug, ignition timing, or ignition wiring issues.",
    ),
    IssueCategoryRule(
        name="routine_service",
        label="Routine Service / PM",
        severity_default="low",
        detection_keywords=("pm", "preventive", "routine", "scheduled",
                            "annual", "semi-annual"),
        description="Scheduled preventive maintenance or routine service visit.",
    ),
    IssueCategoryRule(
        name="unknown",
        label="Unknown / Requires Review",
        severity_default="medium",
        detection_keywords=(),
        description="Issue could not be classified — requires manual review.",
    ),
]

ISSUE_TAXONOMY_MAP: dict[str, IssueCategoryRule] = {r.name: r for r in ISSUE_TAXONOMY}


# ── Issue → recommended primary action mapping ───────────────────────────
# Maps each issue category to the most common resolution action(s) with
# a brief rationale. Used as default when historical data is sparse.

@dataclass(frozen=True)
class ActionRecommendation:
    action_code: str
    action_label: str
    rationale: str
    priority: int = 1  # 1 = primary, 2 = secondary


ISSUE_ACTION_MAP: dict[str, list[ActionRecommendation]] = {
    "detonation": [
        ActionRecommendation("spark_plug_inspection", "Inspect spark plugs",
                             "Detonation most commonly traced to spark plug condition", 1),
        ActionRecommendation("adjustment", "Adjust fuel/BTU settings",
                             "Fuel curve or BTU miscalibration is second most common cause", 2),
    ],
    "leak": [
        ActionRecommendation("inspection", "Locate and inspect leak source",
                             "Must identify leak type (oil/coolant/gas) before repair", 1),
        ActionRecommendation("gasket_seal_repair", "Repair seal/gasket/fitting",
                             "Most leaks resolve with fitting tightening or seal replacement", 2),
    ],
    "pressure_abnormality": [
        ActionRecommendation("inspection", "Check pressure gauges and valves",
                             "Verify readings and inspect relief/check valves", 1),
        ActionRecommendation("valve_inspection", "Inspect compressor valves",
                             "Valve wear is a common cause of pressure instability", 2),
    ],
    "fuel_system": [
        ActionRecommendation("fuel_system_service", "Service fuel system",
                             "Check fuel pressure, BTU settings, and fuel valves", 1),
        ActionRecommendation("adjustment", "Adjust fuel curve/BTU",
                             "Recalibrate if gas composition has changed", 2),
    ],
    "valve_failure": [
        ActionRecommendation("valve_inspection", "Inspect valve condition",
                             "Check clearances, springs, seats, and lash settings", 1),
        ActionRecommendation("valve_replacement", "Replace damaged valve components",
                             "Replace if inspection reveals wear beyond tolerance", 2),
    ],
    "cooling_system": [
        ActionRecommendation("coolant_service", "Check coolant level and condition",
                             "Low coolant or degraded antifreeze is the most common cause", 1),
        ActionRecommendation("inspection", "Inspect radiator, hoses, water pump",
                             "Identify source of cooling deficiency", 2),
    ],
    "electrical": [
        ActionRecommendation("electrical_repair", "Diagnose electrical fault",
                             "Check control panel, sensors, and wiring", 1),
        ActionRecommendation("inspection", "Inspect connectors and harnesses",
                             "Environmental damage to wiring is common in field units", 2),
    ],
    "lubrication": [
        ActionRecommendation("oil_inspection", "Inspect oil level and condition",
                             "Check for contamination, low level, or degradation", 1),
        ActionRecommendation("oil_change", "Perform oil change if needed",
                             "Replace oil and filter if condition warrants", 2),
    ],
    "filter_maintenance": [
        ActionRecommendation("filter_inspection", "Inspect filter condition",
                             "Check restriction indicator and visual condition", 1),
        ActionRecommendation("filter_replacement", "Replace filters",
                             "Replace if dirty, restricted, or overdue by hours/date", 2),
    ],
    "shutdown": [
        ActionRecommendation("inspection", "Read fault codes and inspect unit",
                             "Identify shutdown cause from panel before any repairs", 1),
        ActionRecommendation("test_run", "Attempt controlled restart",
                             "After addressing fault, start and monitor closely", 2),
    ],
    "vibration_noise": [
        ActionRecommendation("inspection", "Inspect for mechanical wear",
                             "Check bearings, mounts, loose components", 1),
        ActionRecommendation("component_replacement", "Replace worn components",
                             "Address source of vibration identified during inspection", 2),
    ],
    "seal_gasket": [
        ActionRecommendation("inspection", "Inspect seals, gaskets, packing",
                             "Locate degraded seal or gasket", 1),
        ActionRecommendation("gasket_seal_repair", "Replace gasket/seal/packing",
                             "Install new seal components and verify", 2),
    ],
    "ignition_system": [
        ActionRecommendation("spark_plug_inspection", "Inspect spark plugs",
                             "Check gap, carbon buildup, electrode condition", 1),
        ActionRecommendation("spark_plug_replacement", "Replace spark plugs",
                             "Replace if worn, fouled, or beyond service interval", 2),
    ],
    "routine_service": [
        ActionRecommendation("routine_inspection", "Perform routine PM inspection",
                             "Follow standard PM checklist for unit type", 1),
        ActionRecommendation("oil_inspection", "Check fluids and filters",
                             "Standard PM includes oil, coolant, and filter checks", 2),
    ],
    "unknown": [
        ActionRecommendation("inspection", "Perform general inspection",
                             "Issue is not yet classified — start with visual inspection", 1),
    ],
}


# ── Issue inference ───────────────────────────────────────────────────────

@dataclass
class IssueInferenceResult:
    """Result of inferring issue category from text signals."""
    category_name: str
    category_label: str
    severity: str
    matched_keywords: list[str]
    confidence: float
    secondary_categories: list[str] = field(default_factory=list)


def infer_issue_category(
    notes: str | None = None,
    description: str | None = None,
    event_category: str | None = None,
    action_types: list[str] | None = None,
) -> IssueInferenceResult:
    """Infer the most likely issue category from available text signals.

    Checks notes and description for keyword matches against the taxonomy.
    Applies priority ordering: higher-severity issues win ties.
    Also considers event category and action types as secondary signals.
    """
    combined = f"{notes or ''} {description or ''}".lower()

    matches: list[tuple[IssueCategoryRule, list[str], float]] = []

    for rule in ISSUE_TAXONOMY:
        if not rule.detection_keywords:
            continue
        matched = [kw for kw in rule.detection_keywords if kw in combined]
        if matched:
            # Score by number of keyword hits and severity weight
            severity_weight = {"high": 1.3, "medium": 1.0, "low": 0.7}
            score = len(matched) * severity_weight.get(rule.severity_default, 1.0)

            # Boost compound keyword matches (multi-word phrases)
            compound_hits = sum(1 for kw in matched if " " in kw)
            score += compound_hits * 0.5

            matches.append((rule, matched, score))

    if not matches:
        # Fallback: check event_category for classification hints
        if event_category in ("preventive_maintenance", "oil_sampling"):
            rule = ISSUE_TAXONOMY_MAP.get("routine_service", ISSUE_TAXONOMY_MAP["unknown"])
            return IssueInferenceResult(
                category_name=rule.name, category_label=rule.label,
                severity=rule.severity_default, matched_keywords=[],
                confidence=0.3, secondary_categories=[],
            )

        return IssueInferenceResult(
            category_name="unknown", category_label="Unknown / Requires Review",
            severity="medium", matched_keywords=[], confidence=0.0,
            secondary_categories=[],
        )

    matches.sort(key=lambda x: x[2], reverse=True)
    best_rule, best_keywords, best_score = matches[0]

    confidence = min(0.95, 0.4 + (best_score * 0.15))

    secondary = [m[0].name for m in matches[1:4] if m[0].name != best_rule.name]

    return IssueInferenceResult(
        category_name=best_rule.name,
        category_label=best_rule.label,
        severity=best_rule.severity_default,
        matched_keywords=best_keywords,
        confidence=confidence,
        secondary_categories=secondary,
    )


def get_recommended_actions(category_name: str) -> list[ActionRecommendation]:
    """Return the rule-based recommended actions for an issue category."""
    return ISSUE_ACTION_MAP.get(category_name, ISSUE_ACTION_MAP["unknown"])


def get_issue_rule(category_name: str) -> IssueCategoryRule | None:
    """Look up the taxonomy rule for a category name."""
    return ISSUE_TAXONOMY_MAP.get(category_name)


def get_primary_action_for_issue(category_name: str) -> ActionRecommendation | None:
    """Return the single highest-priority action for an issue category."""
    actions = ISSUE_ACTION_MAP.get(category_name, [])
    return actions[0] if actions else None
