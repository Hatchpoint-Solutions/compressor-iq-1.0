"""Prescriptive workflow generation.

Layer 4 of the intelligence stack.

Generates step-by-step technician workflows based on:
1. The inferred issue category
2. Recurrence signals (if the issue is repeating, add review steps)
3. Action recommendations from the rules engine
4. Confidence level (low confidence → add triage/escalation steps)

Each step has an instruction, rationale, and optional required evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.services.intelligence.rules_engine import (
    ActionRecommendation,
    get_recommended_actions,
)


@dataclass
class WorkflowStepTemplate:
    """A single step in a technician workflow."""
    step_number: int
    instruction: str
    rationale: str
    required_evidence: str | None = None


@dataclass
class GeneratedWorkflow:
    """Complete workflow produced for a recommendation."""
    issue_category: str
    steps: list[WorkflowStepTemplate]
    notes: list[str] = field(default_factory=list)


# ── Workflow templates per issue category ─────────────────────────────────
# Each template is a list of (instruction, rationale, evidence).
# These are the baseline — they get augmented dynamically based on
# recurrence signals and confidence level.

_WORKFLOW_TEMPLATES: dict[str, list[tuple[str, str, str | None]]] = {
    "detonation": [
        ("Review recent service history and detonation patterns",
         "Repeated detonation events may indicate a systemic issue "
         "rather than a one-time occurrence",
         None),
        ("Check cylinder detonation fault codes and identify affected cylinders",
         "Isolating the affected cylinder(s) narrows the root cause",
         "Record fault codes and affected cylinder numbers"),
        ("Inspect spark plugs — gap, condition, carbon buildup",
         "Spark plug degradation is the most common cause of detonation in gas compressors",
         "Photo of spark plug condition; gap measurement"),
        ("Check fuel pressure and BTU settings",
         "Fuel/BTU miscalibration is the second most common detonation cause",
         "Record fuel pressure reading and current BTU setting"),
        ("Verify ignition timing and wiring integrity",
         "Timing drift or damaged wiring can cause intermittent detonation",
         None),
        ("Replace spark plugs if worn or fouled",
         "If plugs show wear beyond tolerance, replace before further testing",
         "Record part numbers of plugs replaced"),
        ("Adjust fuel curve and BTU settings if needed",
         "Recalibrate if gas composition has changed or settings have drifted",
         "Record new BTU settings after adjustment"),
        ("Start unit, load, and monitor for detonation recurrence",
         "Verify the repair resolved the issue under normal operating conditions",
         "Record run time and any fault codes during test"),
        ("Record findings, adjustments made, and run hours",
         "Complete documentation supports future pattern analysis",
         None),
    ],
    "leak": [
        ("Review recent service history for leak reports",
         "Prior leak events may indicate a chronic leak source",
         None),
        ("Perform visual inspection of unit for active leaks",
         "Identify leak type — oil, coolant, gas, or hydraulic",
         "Photo of leak location"),
        ("Check hoses, fittings, gaskets, and seals in the leak area",
         "Most leaks originate from degraded seals or loose fittings",
         None),
        ("Identify and document leak source",
         "Precise identification prevents repeat visits for the same leak",
         "Record leak source component and fluid type"),
        ("Tighten fittings or replace damaged components",
         "Address the root cause, not just the symptom",
         "Record parts replaced or fittings tightened"),
        ("Pressure test repaired area if applicable",
         "Verify the repair holds under operating pressure",
         "Record test pressure and duration"),
        ("Start unit and verify leak is resolved",
         "Confirm no active leak under normal operating conditions",
         None),
        ("Record findings, parts replaced, and leak location",
         "Detailed records help identify if this leak recurs",
         None),
    ],
    "pressure_abnormality": [
        ("Review recent pressure readings and alarm history",
         "Trending pressure data reveals whether this is sudden or gradual",
         None),
        ("Check suction and discharge pressure gauges",
         "Verify current readings against normal operating range",
         "Record current suction and discharge pressures"),
        ("Inspect pressure relief valves and safety devices",
         "Relief valve malfunction can cause false pressure readings",
         None),
        ("Verify compressor valve condition",
         "Worn valves are a common cause of pressure instability",
         "Record valve clearance measurements"),
        ("Check for blockages in suction/discharge path",
         "Debris or ice can restrict flow and cause pressure anomalies",
         None),
        ("Adjust pressure setpoints if within safe range",
         "Only adjust if readings are confirmed valid and within equipment limits",
         "Record old and new setpoints"),
        ("Start unit and monitor pressure stability",
         "Verify pressure normalizes under load",
         "Record pressures at 15 min and 30 min intervals"),
        ("Record findings and pressure readings",
         "Pressure trend data is critical for future diagnosis",
         None),
    ],
    "fuel_system": [
        ("Review recent fuel system notes and BTU history",
         "Gas quality changes upstream can cause fuel-related symptoms",
         None),
        ("Check fuel pressure at regulator and downstream",
         "Compare to nameplate values — deviation indicates an issue",
         "Record fuel pressure at regulator inlet and outlet"),
        ("Verify fuel quality (BTU) setting matches gas composition",
         "BTU mismatch is a leading cause of performance issues",
         "Record current BTU setting and gas analysis if available"),
        ("Inspect fuel valves, regulators, and fuel lines",
         "Physical damage or wear can cause intermittent fuel issues",
         None),
        ("Adjust fuel curve and absolute fuel pressure",
         "Recalibrate to match current gas conditions",
         "Record new fuel curve settings"),
        ("Check for fuel bottle condensation — drain if needed",
         "Condensation in fuel bottles degrades fuel quality",
         None),
        ("Start unit and monitor engine performance",
         "Verify smooth operation under load after adjustments",
         "Record engine RPM, load, and any fault codes"),
        ("Record BTU settings, adjustments, and fuel pressure readings",
         "Complete fuel system records support trend analysis",
         None),
    ],
    "valve_failure": [
        ("Review valve maintenance history",
         "Recurrent valve issues may indicate a design or operating condition problem",
         None),
        ("Identify affected valve(s) — compressor or engine side",
         "Engine valves and compressor valves have different failure modes",
         "Record which valve(s) are suspect"),
        ("Perform valve inspection and measure clearances",
         "Clearance measurements determine if valves are within tolerance",
         "Record valve clearance measurements"),
        ("Check for broken springs, worn seats, or debris",
         "These are the most common valve failure modes",
         "Photo of valve condition"),
        ("Replace valve components as needed",
         "Replace if inspection reveals wear beyond tolerance",
         "Record part numbers and components replaced"),
        ("Verify lash/clearance settings after replacement",
         "Correct lash is critical for reliable valve operation",
         "Record final clearance measurements"),
        ("Start unit and monitor for abnormal noise or performance",
         "Valve issues often produce audible symptoms when active",
         None),
        ("Record valve condition, parts replaced, and clearances",
         "Historical valve data helps predict future maintenance intervals",
         None),
    ],
    "cooling_system": [
        ("Review coolant temperature and level history",
         "Gradual coolant loss suggests a slow leak; sudden loss suggests a failure",
         None),
        ("Check coolant level and condition",
         "Low coolant is the most common cause of overheating",
         "Record coolant level and condition (color, clarity)"),
        ("Inspect radiator, hoses, and water pump",
         "Visual inspection often reveals the cooling failure source",
         None),
        ("Check thermostat operation",
         "A stuck thermostat can cause overheating without any leaks",
         None),
        ("Look for coolant leaks — internal and external",
         "Internal leaks (head gasket) are harder to detect but critical",
         "Record any leak locations found"),
        ("Top off or replace coolant as needed",
         "Restore coolant level and quality to specification",
         "Record volume of coolant added"),
        ("Start unit and monitor temperatures",
         "Verify temperatures return to normal range under load",
         "Record temperature at 15 min and 30 min intervals"),
        ("Record coolant condition, levels, and temperatures",
         "Temperature trend data helps diagnose chronic cooling issues",
         None),
    ],
    "electrical": [
        ("Review alarm/fault history and panel shutdowns",
         "Fault code history often pinpoints the failing component",
         "Record all active and recent fault codes"),
        ("Check control panel for active faults",
         "Clear and re-read faults to distinguish active from historical",
         None),
        ("Inspect wiring, connectors, and sensor cables",
         "Environmental damage to field wiring is common",
         "Photo of any damaged wiring found"),
        ("Test suspect sensors with multimeter",
         "Verify sensor output is within expected range",
         "Record sensor readings and expected values"),
        ("Replace faulty sensors or wiring as needed",
         "Replace only components confirmed to be faulty",
         "Record part numbers of components replaced"),
        ("Clear faults and restart control system",
         "Confirm all faults clear after repairs",
         None),
        ("Start unit and verify sensor readings are normal",
         "Validate all readings under operating conditions",
         "Record key sensor readings after restart"),
        ("Record fault codes, components replaced, and readings",
         "Electrical fault history is critical for pattern detection",
         None),
    ],
    "lubrication": [
        ("Review oil sample results and oil change history",
         "Oil analysis trends indicate whether degradation is normal or accelerated",
         None),
        ("Check engine oil level and condition",
         "Visual and dipstick check for level, color, and debris",
         "Record oil level (dipstick position) and visual condition"),
        ("Inspect for oil leaks around engine and compressor",
         "External oil loss can cause low oil pressure",
         "Note any leak locations found"),
        ("Check oil pressure readings",
         "Low oil pressure requires immediate attention",
         "Record current oil pressure reading"),
        ("Perform oil change if overdue or contaminated",
         "Replace oil and filter when condition warrants",
         "Record oil volume drained/added and filter replaced"),
        ("Replace oil filter",
         "Always replace filter with oil change",
         "Record filter part number"),
        ("Start unit and verify oil pressure is within range",
         "Confirm oil pressure stabilizes at normal operating range",
         "Record oil pressure at idle and under load"),
        ("Record oil condition, volume added, and pressure readings",
         "Oil service records support interval optimization",
         None),
    ],
    "filter_maintenance": [
        ("Review filter change history and schedule",
         "Determine if filters are being changed at appropriate intervals",
         None),
        ("Inspect air filter condition — check restriction indicator",
         "Restriction indicator gives objective measure of filter loading",
         "Record restriction indicator reading"),
        ("Replace air filter if dirty or restricted",
         "Restricted air filter reduces engine performance and efficiency",
         "Record filter part number replaced"),
        ("Check oil filter and fuel filter condition",
         "All filters should be assessed during a filter service visit",
         None),
        ("Replace additional filters as needed",
         "Proactive replacement prevents unscheduled shutdowns",
         "Record all filter part numbers replaced"),
        ("Verify clean filter installation and sealing",
         "Improper installation can cause unfiltered air/oil ingestion",
         None),
        ("Record filter types replaced and run hours",
         "Run hours at replacement support interval optimization",
         None),
    ],
    "shutdown": [
        ("Review shutdown fault code from control panel",
         "The fault code is the single most important diagnostic clue",
         "Record exact fault code(s) displayed"),
        ("Identify shutdown cause — detonation, temperature, pressure, or panel",
         "Classification determines which subsystem to investigate",
         None),
        ("Investigate specific subsystem based on fault code",
         "Follow the fault-specific workflow for the identified subsystem",
         None),
        ("Attempt restart and monitor closely",
         "If root cause is addressed, verify unit runs normally",
         "Record restart result and any new fault codes"),
        ("If shutdown recurs, escalate diagnostics",
         "Repeated shutdowns require deeper investigation",
         None),
        ("Record fault codes, restart attempts, and observations",
         "Shutdown patterns are high-value data for reliability analysis",
         None),
    ],
    "vibration_noise": [
        ("Review recent vibration or noise complaints",
         "Pattern of vibration reports helps isolate the source",
         None),
        ("Perform auditory and tactile inspection of unit",
         "Experienced technicians can often localize vibration sources by feel",
         "Describe location and character of vibration/noise"),
        ("Check bearings, mounts, and coupling alignment",
         "Bearing wear and misalignment are the most common vibration sources",
         None),
        ("Inspect belts and rotating components",
         "Worn belts or imbalanced components cause characteristic vibration",
         None),
        ("Replace worn components identified during inspection",
         "Address the root cause rather than treating the symptom",
         "Record parts replaced"),
        ("Start unit and verify vibration/noise is resolved",
         "Confirm under normal operating conditions",
         None),
        ("Record findings and components replaced",
         "Vibration trend data supports predictive maintenance",
         None),
    ],
    "seal_gasket": [
        ("Review seal/gasket service history",
         "Repeated seal failures may indicate an alignment or pressure issue",
         None),
        ("Identify the failing seal, gasket, or packing",
         "Determine component type and location before ordering parts",
         "Record component location and type"),
        ("Inspect mating surfaces for damage",
         "Damaged mating surfaces will destroy new seals quickly",
         None),
        ("Replace seal/gasket/packing with correct specification",
         "Use OEM or equivalent specification components",
         "Record part number installed"),
        ("Verify proper seating and alignment",
         "Misalignment is the leading cause of premature seal failure",
         None),
        ("Start unit and verify no leakage",
         "Run at operating pressure and temperature to confirm seal",
         None),
        ("Record component replaced and condition of old seal",
         "Seal condition data helps identify root cause of failure",
         None),
    ],
    "ignition_system": [
        ("Review ignition system maintenance history",
         "Ignition issues often have a predictable replacement interval",
         None),
        ("Inspect spark plugs — gap, electrode condition, carbon deposits",
         "Spark plug condition is the primary diagnostic for ignition issues",
         "Record plug gap measurement and visual condition"),
        ("Check ignition wiring and connectors",
         "Wiring degradation causes intermittent misfires",
         None),
        ("Verify ignition timing",
         "Timing drift causes performance degradation and potential detonation",
         "Record timing measurement"),
        ("Replace spark plugs if worn beyond tolerance",
         "Replace as a set for consistent performance",
         "Record part numbers and quantities replaced"),
        ("Start unit and verify smooth operation",
         "Confirm no misfires or detonation under load",
         "Record any fault codes during test run"),
        ("Record plug condition, timing, and findings",
         "Ignition data supports spark plug interval optimization",
         None),
    ],
    "routine_service": [
        ("Review PM schedule and last service dates",
         "Verify which PM tasks are due based on run hours and calendar",
         None),
        ("Check fluid levels — engine oil, compressor oil, coolant",
         "Fluid levels are the baseline of any PM inspection",
         "Record all fluid levels"),
        ("Inspect belts, hoses, and external condition",
         "Visual inspection catches early-stage degradation",
         None),
        ("Check and replace filters as scheduled",
         "Follow PM interval guidelines for filter replacement",
         "Record filter part numbers if replaced"),
        ("Perform oil change if due by hours or calendar",
         "Follow OEM interval recommendations",
         "Record oil volume and filter replaced"),
        ("Run unit and monitor key parameters",
         "Verify unit runs normally after PM service",
         "Record key operating parameters during test run"),
        ("Record all PM tasks completed and run hours",
         "Complete PM records are essential for compliance and planning",
         None),
    ],
}

_DEFAULT_WORKFLOW: list[tuple[str, str, str | None]] = [
    ("Review recent service history for this compressor",
     "Historical context helps frame the current situation",
     None),
    ("Perform general visual inspection of the unit",
     "Visual inspection may reveal the issue before detailed diagnostics",
     "Note any visible anomalies"),
    ("Check fluid levels — oil, coolant",
     "Low fluids are a common and easy-to-check starting point",
     "Record fluid levels"),
    ("Inspect belts, hoses, and filters",
     "These are the most common wear items on compressor packages",
     None),
    ("Check for unusual noise, vibration, or leaks",
     "Sensory inspection can detect issues not shown by instruments",
     None),
    ("Run unit and monitor key parameters",
     "Operating data under load is the most revealing diagnostic tool",
     "Record key parameters during test run"),
    ("Record all findings and observations",
     "Even negative findings are valuable for future analysis",
     None),
]


# ── Public API ────────────────────────────────────────────────────────────

def generate_workflow(
    issue_category: str,
    has_recurrence: bool = False,
    recurrence_description: str | None = None,
    confidence_label: str = "medium",
    additional_context: str | None = None,
) -> GeneratedWorkflow:
    """Generate a technician workflow for the given issue category.

    Augments the base template with:
    - Recurrence review step if recurrence signals are present
    - Escalation step if confidence is low
    - Context-specific notes
    """
    base_template = _WORKFLOW_TEMPLATES.get(issue_category, _DEFAULT_WORKFLOW)

    steps: list[WorkflowStepTemplate] = []
    notes: list[str] = []
    step_num = 1

    # Prepend recurrence review step if applicable
    if has_recurrence:
        steps.append(WorkflowStepTemplate(
            step_number=step_num,
            instruction="Review recurrence pattern — this issue has repeated recently",
            rationale=recurrence_description or (
                "Recurring issues require investigation of the underlying root cause, "
                "not just the immediate symptom"
            ),
            required_evidence="Note whether previous repairs fully resolved the issue",
        ))
        step_num += 1
        notes.append("Recurrence detected — workflow includes root cause investigation step")

    # Add base template steps
    for instruction, rationale, evidence in base_template:
        steps.append(WorkflowStepTemplate(
            step_number=step_num,
            instruction=instruction,
            rationale=rationale,
            required_evidence=evidence,
        ))
        step_num += 1

    # Append escalation step if confidence is low
    if confidence_label == "low":
        steps.append(WorkflowStepTemplate(
            step_number=step_num,
            instruction=(
                "Escalate to senior technician or engineering if issue "
                "is not resolved after initial inspection"
            ),
            rationale=(
                "System confidence is low for this case — "
                "insufficient historical data to recommend a specific resolution"
            ),
            required_evidence="Document what was attempted and why escalation is needed",
        ))
        step_num += 1
        notes.append("Low confidence — escalation step added to workflow")

    return GeneratedWorkflow(
        issue_category=issue_category,
        steps=steps,
        notes=notes,
    )
