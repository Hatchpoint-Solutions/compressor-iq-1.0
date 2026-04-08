"""Prescriptive workflow generation.

Layer 4 of the intelligence stack.

Generates step-by-step technician workflows based on:
1. The inferred issue category
2. Recurrence signals (if the issue is repeating, add review steps)
3. Action recommendations from the rules engine
4. Confidence level (low confidence → add triage/escalation steps)

Each step has an instruction, rationale, and optional required evidence.
Steps are written as field-executable procedures — a technician should
be able to follow them with tools in hand, without needing to interpret
vague guidance.
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
#
# DESIGN PRINCIPLE: Every step must be a concrete, executable action that
# a field technician can perform without ambiguity. Steps include:
# - Required PPE / tools / materials
# - Specific locations, components, and access points
# - Measurable criteria and acceptance specs
# - Decision logic (if/then) for what to do based on findings
# - Safety isolation requirements (LOTO, depressurization)

_WORKFLOW_TEMPLATES: dict[str, list[tuple[str, str, str | None]]] = {
    "detonation": [
        (
            "SAFETY: Perform lockout/tag-out (LOTO) on the unit. Shut down the engine, "
            "close the fuel gas supply valve, and verify zero energy state. Wear safety "
            "glasses, hearing protection, and leather gloves.",
            "Detonation investigation requires accessing ignition and fuel components. "
            "The unit must be fully isolated before opening any engine covers.",
            "Record LOTO tag number and time applied"
        ),
        (
            "Pull the last 30 days of service history from the control panel or maintenance "
            "log. Count the number of detonation fault events. Note whether they are "
            "concentrated on the same cylinder(s) or distributed across multiple cylinders.",
            "Repeat detonation on a single cylinder points to a component issue (spark plug, "
            "valve). Multi-cylinder detonation points to a fuel/BTU or timing issue affecting "
            "the whole engine.",
            "Record fault code numbers, dates, affected cylinder numbers, and run hours at each event"
        ),
        (
            "Navigate to the control panel (e.g., CAT ADEM, Murphy, or SCADALynx). Pull "
            "active and stored fault codes. Write down each code and its description. "
            "Clear active faults, then restart the panel to confirm which faults return "
            "immediately vs. which were historical.",
            "Active fault codes that return after clearing indicate an ongoing condition; "
            "stored-only codes may already be resolved.",
            "Record all fault codes: code number, description, date/time, and whether active or stored"
        ),
        (
            "Remove the spark plug wire boots one at a time. Using a spark plug socket "
            "(typically 13/16\" or 18mm), remove each spark plug. Inspect each plug:\n"
            "  - Measure electrode gap with a feeler gauge (spec: 0.010\"–0.015\" for most "
            "Cat/Waukesha natural gas engines; refer to OEM manual for exact spec)\n"
            "  - Check for carbon/oil fouling on the insulator nose\n"
            "  - Look for cracked porcelain, melted electrodes, or heavy white deposits\n"
            "  - If gap exceeds spec by >0.005\" or electrode shows visible erosion, mark "
            "that plug for replacement",
            "Spark plug degradation is the #1 cause of detonation in natural gas compressor "
            "engines. Gap out of spec causes weak spark, leading to incomplete combustion "
            "and pressure spikes.",
            "Record per-cylinder: plug part number, measured gap, visual condition (good / "
            "fouled / eroded / cracked), and whether marked for replacement"
        ),
        (
            "Check fuel gas supply pressure at the unit inlet using a calibrated 0–60 psi "
            "gauge. Expected range: 3–10 psig depending on unit model (consult nameplate "
            "or OEM spec sheet). Then check downstream regulated pressure at the fuel "
            "regulator outlet — should be within ±0.5 psi of setpoint.\n"
            "  - If inlet pressure is low (<3 psi), the issue is upstream supply — contact "
            "operations/pipeline\n"
            "  - If inlet is good but regulated pressure is off, the regulator needs adjustment "
            "or replacement",
            "Fuel pressure outside specification causes lean or rich combustion. Lean mixtures "
            "detonate; rich mixtures foul plugs and produce knock.",
            "Record inlet fuel pressure, regulated fuel pressure, and regulator setpoint (all in psig)"
        ),
        (
            "On the engine control panel, navigate to the BTU/fuel curve settings screen. "
            "Record the current BTU setpoint. Compare against the most recent gas analysis "
            "(from the gas chromatograph report or operations). If no recent analysis is "
            "available, request one.\n"
            "  - If BTU setting differs from actual gas BTU by more than 50 BTU, this is a "
            "likely detonation contributor\n"
            "  - Adjust BTU setting to match the actual gas analysis value\n"
            "  - If BTU is correct, proceed to timing check",
            "Gas composition changes seasonally and with well production changes. A BTU "
            "mismatch causes the engine to run lean or rich, directly causing detonation.",
            "Record current BTU setting, actual gas BTU from analysis (if available), and "
            "any adjustment made (old value → new value)"
        ),
        (
            "Verify ignition timing using a timing light connected to the #1 cylinder plug "
            "wire (engine must be running for this step — remove LOTO temporarily with "
            "spotter present and all covers reinstalled).\n"
            "  - Point timing light at the flywheel timing marks\n"
            "  - Compare observed timing to OEM spec (typically 8°–12° BTDC for natural gas; "
            "consult unit data plate)\n"
            "  - If timing has drifted more than 2° from spec, recalibrate per OEM procedure\n"
            "  - While running, inspect ignition wires for arcing (visible in low-light "
            "conditions) — replace any wires showing arc marks",
            "Timing drift causes combustion to occur at the wrong point in the cycle. "
            "Advanced timing increases peak cylinder pressure and causes detonation.",
            "Record observed timing (degrees BTDC), OEM spec, and any adjustment made; "
            "note any ignition wires replaced"
        ),
        (
            "Replace all spark plugs that were marked for replacement in Step 4. Use OEM "
            "or equivalent plugs (record part number from existing plugs or unit manual). "
            "Set gap on new plugs to OEM spec using a feeler gauge before installation. "
            "Apply anti-seize compound to threads. Torque to spec (typically 25–30 ft-lbs "
            "for 14mm plugs; consult OEM manual). Reconnect plug wire boots firmly — push "
            "until you feel/hear them click.",
            "New plugs restore consistent spark energy across all cylinders. Consistent gap "
            "ensures even combustion and eliminates single-cylinder detonation.",
            "Record per-cylinder: new plug part number, measured gap before install, and "
            "torque applied"
        ),
        (
            "Reinstall all engine covers and guards. Remove LOTO. Open fuel gas supply valve. "
            "Start the engine and allow it to warm up to operating temperature (typically "
            "160°F–185°F coolant temp, 5–10 minutes). Gradually load the compressor to "
            "normal operating load.\n"
            "  - Monitor the control panel for detonation fault codes for a minimum of "
            "30 minutes under load\n"
            "  - Listen for audible knock at each cylinder using a mechanic's stethoscope "
            "or by placing a long screwdriver on each cylinder and listening through the "
            "handle\n"
            "  - If detonation recurs within 30 minutes on the same cylinder(s), the root "
            "cause is deeper (valve seat, piston ring, or head gasket) — escalate to senior "
            "technician\n"
            "  - If no detonation occurs, run for an additional 60 minutes and recheck",
            "Verification under actual operating conditions is the only way to confirm the "
            "repair resolved the detonation. Load testing is critical because detonation "
            "typically occurs under load, not at idle.",
            "Record: total test run time, coolant temp at start/end, any fault codes during "
            "test, and audible check results per cylinder (normal / knock detected)"
        ),
        (
            "Complete the service report:\n"
            "  - List all spark plugs replaced (cylinder number, old condition, new part number)\n"
            "  - Record all fuel/BTU adjustments (old setting → new setting)\n"
            "  - Record timing adjustments if made\n"
            "  - Record current run hours from the panel\n"
            "  - Note the test run duration and result (detonation resolved / not resolved)\n"
            "  - If not resolved, document what was attempted and the escalation recommendation",
            "Complete documentation is critical for pattern analysis. If this detonation "
            "recurs, the next technician must know exactly what was already checked and replaced.",
            None
        ),
    ],
    "leak": [
        (
            "SAFETY: Shut down the unit. Perform lockout/tag-out (LOTO). If a gas leak "
            "is suspected, use a portable gas detector (LEL monitor) to confirm the area "
            "is safe before approaching. Wear safety glasses, nitrile gloves, and "
            "oil-resistant coveralls. If gas is detected above 10% LEL, evacuate and "
            "contact HSE before proceeding.",
            "Leaks may involve pressurized gas, hot oil, or coolant under pressure. "
            "Gas leaks are an explosion/fire hazard and require LEL monitoring.",
            "Record LOTO tag number, time applied, and LEL reading at the unit"
        ),
        (
            "Pull the last 90 days of service history. Identify any prior leak reports — "
            "note the location, fluid type, and repair performed for each. Count how many "
            "leak events have occurred in this period.\n"
            "  - If 3+ leak events at the same location → this is a chronic leak requiring "
            "root cause analysis, not just a repeat repair\n"
            "  - If first occurrence → proceed with standard leak investigation",
            "Recurring leaks at the same location suggest a root cause beyond the seal "
            "itself — misalignment, vibration fatigue, or incorrect torque on previous repair.",
            "Record previous leak dates, locations, fluid types, and repairs performed"
        ),
        (
            "Perform a 360° walk-around inspection of the unit. Start at the engine "
            "front and work clockwise. Look for:\n"
            "  - Active drips, puddles, or wet spots on the skid, frame, or ground\n"
            "  - Spray patterns on adjacent components (indicates pressurized leak)\n"
            "  - Staining or discoloration on hoses, fittings, or the skid\n"
            "  - Coolant residue (green/orange crystalline deposits)\n"
            "  - Oil film on compressor cylinders, crosshead guides, or distance pieces\n"
            "Identify the fluid type by color and feel:\n"
            "  - Engine oil: dark amber to black, slippery\n"
            "  - Compressor oil: lighter amber, may smell different\n"
            "  - Coolant: green, orange, or pink, sweet smell\n"
            "  - Hydraulic fluid: clear to light amber\n"
            "  - Gas: no visible fluid — use LEL detector or soap bubble test",
            "Visual inspection establishes the leak type and narrows the search area. "
            "Spray patterns indicate leak direction and flow rate.",
            "Record each leak location found: component, fluid type, estimated drip rate "
            "(drops/min or steady stream), and take a photo of each"
        ),
        (
            "Trace each identified leak to its source. Work upstream from the puddle or wet "
            "spot. Use a clean rag to wipe the area dry, then watch for the first point "
            "where fluid reappears.\n"
            "  - For fittings: check each connection in the path with a wrench — if it turns, "
            "it was loose\n"
            "  - For hoses: run a gloved hand along the length feeling for wet spots, cracks, "
            "or bulges\n"
            "  - For gasket surfaces: look for fluid weeping from the mating line of flanges "
            "or covers\n"
            "  - For packing: check the distance piece area and packing case for oil weeping "
            "past the rings\n"
            "  - For gas leaks: apply leak detection solution (Snoop or soapy water) to "
            "suspected joints and watch for bubbles",
            "The visible leak point may not be the source — fluid migrates along surfaces. "
            "Tracing upstream prevents repairing the wrong component.",
            "Record the confirmed source: component name/number, connection type "
            "(threaded/flanged/compression), and estimated severity (minor seep / active drip / stream)"
        ),
        (
            "Repair the leak based on the source identified:\n"
            "  - LOOSE FITTING: Tighten using the correct wrench (backup wrench on one side "
            "to prevent rotation). Tighten 1/4 turn past snug for NPT; torque to spec for "
            "JIC/SAE fittings (consult fitting torque chart)\n"
            "  - DAMAGED HOSE: Replace the hose assembly. Match the ID, pressure rating, "
            "and end fitting type exactly. Cut to length and crimp if using field-make ends. "
            "Torque fittings to spec\n"
            "  - GASKET LEAK: Remove the cover or flange. Clean both mating surfaces with "
            "a gasket scraper (no power tools on aluminum surfaces). Install new gasket "
            "using OEM part number. Torque bolts in a star pattern to spec\n"
            "  - PACKING LEAK: If within adjustment range, tighten packing gland nuts 1/6 turn "
            "at a time, alternating sides. If past adjustment range, schedule packing replacement\n"
            "  - GAS LEAK AT FLANGE: Re-torque flange bolts in a star pattern. If still leaking, "
            "replace gasket. Confirm with soap bubble test after repair",
            "The repair method must match the failure mode. Over-tightening fittings can "
            "crack them; under-tightening will not stop the leak.",
            "Record repair action: component repaired, method (tightened / replaced / adjusted), "
            "parts used (part numbers), torque applied where applicable"
        ),
        (
            "After repair, prepare for a pressure/leak test:\n"
            "  - Remove LOTO. Open fuel gas supply and any isolation valves\n"
            "  - Start the unit and allow it to reach normal operating pressure and temperature\n"
            "  - Apply leak detection solution to all repaired areas\n"
            "  - Watch for bubbles for at least 2 minutes at each point\n"
            "  - For oil/coolant leaks: run for 15 minutes minimum and visually check for any "
            "new fluid at the repair location\n"
            "  - If the leak persists, shut down and re-evaluate — the source may have been "
            "misidentified or the replacement component may be defective",
            "Pressure testing under operating conditions is the only reliable verification. "
            "Static pressure tests may miss leaks that only appear under thermal expansion "
            "or vibration.",
            "Record: operating pressure during test, test duration, soap test result "
            "(pass/fail), and whether any fluid was observed at the repair site"
        ),
        (
            "Complete the service report:\n"
            "  - Leak location (component, position on unit)\n"
            "  - Fluid type and estimated volume lost\n"
            "  - Root cause (loose fitting / degraded hose / worn gasket / packing wear)\n"
            "  - Repair performed and parts used (with part numbers)\n"
            "  - Pressure/leak test result\n"
            "  - Current run hours\n"
            "  - If this is a repeat leak: note the recurrence and recommend root cause "
            "investigation (alignment check, vibration analysis, or engineering review)",
            "Detailed leak records allow reliability engineers to identify chronic leak "
            "locations and plan proactive replacements.",
            None
        ),
    ],
    "pressure_abnormality": [
        (
            "SAFETY: If high-pressure alarms are active, do NOT approach the unit until "
            "pressure is confirmed below the relief valve setpoint. Wear safety glasses "
            "and hearing protection. If the unit is running, observe gauge readings from "
            "a safe distance before approaching.",
            "Abnormal pressure can indicate a blocked discharge path or failed relief "
            "valve — both present a rupture hazard.",
            "Record active alarm codes and the time/distance at which you first observed "
            "the pressure readings"
        ),
        (
            "At the control panel, pull the alarm history for the last 7 days. Note all "
            "pressure-related alarms: high discharge, low suction, differential pressure, "
            "and relief valve trip events. Identify:\n"
            "  - Which stage(s) are affected (Stage 1, Stage 2, etc.)\n"
            "  - Whether the condition is sudden onset or gradual trend\n"
            "  - The exact pressure values at each alarm event",
            "Pressure trends reveal whether this is a sudden failure (valve, blockage) or "
            "gradual degradation (valve wear, packing blow-by).",
            "Record each alarm: date/time, alarm type, stage, pressure value, and run hours"
        ),
        (
            "With the unit running, read the current suction and discharge pressures for "
            "each compressor stage using the panel display and/or local mechanical gauges. "
            "Compare against the normal operating range on the unit data plate or operating "
            "envelope chart.\n"
            "  - If mechanical gauge and panel reading disagree by >5%, the sensor or gauge "
            "may be faulty — use a calibrated test gauge to determine which is correct\n"
            "  - Record all pressure readings and ambient temperature",
            "Comparing actual readings to nameplate values identifies which stage and "
            "which direction (suction vs. discharge) is abnormal.",
            "Record per stage: suction pressure, interstage pressure(s), discharge pressure, "
            "and the corresponding normal ranges from the data plate"
        ),
        (
            "Inspect the pressure relief valves (PRVs) on each affected stage:\n"
            "  - Check for visible signs of popping (staining, residue, or warmth at outlet)\n"
            "  - Verify the set pressure stamped on the PRV matches the unit spec\n"
            "  - If a PRV has been popping, it must be tested and re-certified or replaced\n"
            "  - DO NOT manually lift or test PRVs while the system is pressurized unless "
            "using an approved test rig and procedure",
            "A PRV that leaks or has reseated at the wrong pressure can cause false "
            "pressure readings and will not protect the system in an overpressure event.",
            "Record each PRV: tag number, stamped set pressure, last test date, and "
            "observation (normal / signs of popping / leaking)"
        ),
        (
            "Shut down the unit and perform LOTO. Remove compressor valve covers on the "
            "affected stage(s). Inspect the compressor valves:\n"
            "  - Remove each valve assembly and check for:\n"
            "    • Broken or chipped valve plates/rings\n"
            "    • Worn valve seats (run a fingernail across the seat — you should feel no grooves)\n"
            "    • Broken or fatigued valve springs\n"
            "    • Debris or carbon buildup on sealing surfaces\n"
            "  - If suction valves are leaking: discharge pressure drops and suction rises\n"
            "  - If discharge valves are leaking: efficiency drops and temperatures rise\n"
            "  - Replace any valve assembly showing plate damage, seat wear, or spring fatigue",
            "Worn compressor valves are the most common cause of pressure instability in "
            "reciprocating compressors. Even a single leaking valve plate drops stage "
            "efficiency significantly.",
            "Record per valve: valve position (suction/discharge, stage, head/crank end), "
            "condition (good / worn / broken), part number if replaced, and photo of "
            "damaged components"
        ),
        (
            "While valve covers are off, inspect the suction strainer/screen for blockage:\n"
            "  - Remove the strainer element and check for debris, scale, or ice\n"
            "  - Clean or replace the strainer if more than 25% blocked\n"
            "  - Inspect the cylinder bore for scoring (shine a flashlight in and look for "
            "vertical scratch marks)\n"
            "  - Check piston rod for packing blow-by (oil mist or gas leaking from the "
            "packing case)",
            "Blocked suction screens restrict flow and drop suction pressure. Piston ring "
            "or packing wear allows gas to bypass, reducing effective compression.",
            "Record strainer condition (clean / partially blocked / fully blocked), debris "
            "type, cylinder bore condition, and packing blow-by observation"
        ),
        (
            "Reassemble all valve covers with new gaskets (do not reuse compressor valve "
            "cover gaskets). Torque cover bolts to OEM spec in a star pattern. Remove LOTO. "
            "Start the unit and bring to operating conditions.\n"
            "  - Monitor suction and discharge pressures at 5-minute intervals for the first "
            "30 minutes\n"
            "  - Pressures should stabilize within the normal operating range within 10–15 "
            "minutes\n"
            "  - If pressures remain abnormal, the issue may be upstream (supply pressure) "
            "or downstream (back-pressure from piping/vessel) — coordinate with operations",
            "Post-repair verification under load confirms the valve replacement or cleaning "
            "resolved the pressure abnormality.",
            "Record pressures at 5, 10, 15, 20, and 30 minutes after startup; note whether "
            "readings are within normal range"
        ),
        (
            "Complete the service report:\n"
            "  - All pressure readings (before and after repair)\n"
            "  - Valves inspected and replaced (position, condition, part numbers)\n"
            "  - Strainer condition and cleaning performed\n"
            "  - PRV inspection results\n"
            "  - Current run hours\n"
            "  - Startup verification pressures (5-min interval readings)\n"
            "  - If issue persists: document what was checked and cleared, and the "
            "recommended next investigation (operations review, piping check, or "
            "engineering analysis)",
            "Pressure event documentation feeds directly into reliability trending and "
            "helps predict valve replacement intervals.",
            None
        ),
    ],
    "fuel_system": [
        (
            "SAFETY: Shut down the unit. Close the fuel gas supply valve upstream of the "
            "unit. Perform LOTO on the engine and fuel system. Verify zero pressure in the "
            "fuel piping by cracking a fitting downstream of the shutoff valve and checking "
            "with an LEL detector. Wear safety glasses, leather gloves, and have a fire "
            "extinguisher within 25 feet.",
            "Fuel system work involves pressurized natural gas. Even residual pressure can "
            "cause a gas release when fittings are opened.",
            "Record LOTO tag number, fuel supply valve position, and LEL reading after isolation"
        ),
        (
            "Review the last 60 days of service history and alarm logs for fuel-related "
            "events: BTU alarms, fuel pressure faults, lean/rich mixture faults, and any "
            "engine performance complaints. Note whether the gas source or composition has "
            "changed recently (new wells, pipeline blending).",
            "Fuel system issues are frequently caused by upstream gas quality changes. "
            "Knowing the timeline helps distinguish equipment failure from supply change.",
            "Record all fuel-related fault codes, dates, and any known gas supply changes"
        ),
        (
            "Install a calibrated 0–60 psi test gauge at the fuel gas inlet (before the "
            "first regulator). Open the upstream supply valve while LOTO is still on the "
            "engine. Read the static supply pressure.\n"
            "  - Expected range: consult unit data plate (typically 20–60 psig supply)\n"
            "  - If below spec: the issue is upstream supply — contact operations\n"
            "  - If within spec: proceed to regulator check\n"
            "Move the test gauge to the regulator outlet. Verify regulated pressure:\n"
            "  - Expected: per unit data plate (typically 3–10 psig regulated)\n"
            "  - If regulated pressure is high: regulator diaphragm may be failed open\n"
            "  - If regulated pressure is low: regulator may be stuck or undersized for "
            "current flow demand",
            "Fuel pressure is the foundation of correct combustion. Every other fuel system "
            "adjustment is meaningless if supply or regulated pressure is wrong.",
            "Record: supply pressure (psig), regulated pressure (psig), expected values from "
            "data plate, and regulator make/model/setpoint"
        ),
        (
            "On the engine control panel, navigate to the fuel/BTU settings. Record:\n"
            "  - Current BTU setpoint\n"
            "  - Current fuel curve (if configurable — e.g., fuel map table values)\n"
            "  - Any fuel trim or adaptive fuel corrections active\n"
            "Obtain the most recent gas analysis (gas chromatograph report). Compare:\n"
            "  - If BTU setpoint differs from actual gas BTU by >50 BTU → adjust to match\n"
            "  - If no gas analysis is available within the last 30 days, request one from "
            "operations and set the BTU to the best available estimate\n"
            "  - Adjust fuel curve per OEM procedure if gas BTU has changed significantly "
            "(>100 BTU shift)",
            "BTU mismatch is the most common fuel-related root cause of engine performance "
            "issues, detonation, and misfires.",
            "Record old BTU setting, actual gas BTU from analysis, new BTU setting after "
            "adjustment, and fuel curve changes made"
        ),
        (
            "Inspect the fuel system components physically:\n"
            "  - Fuel valves: check for sticking, external leaks, and actuator operation "
            "(manual override to verify full open/close)\n"
            "  - Fuel regulator: check for diaphragm weeping (gas leaking from vent port), "
            "frozen components (ice from pressure drop in high-moisture gas)\n"
            "  - Fuel lines/tubing: check for kinks, corrosion, or damage\n"
            "  - Fuel scrubber/filter: drain the condensate bowl — if more than 1/4 full, "
            "liquid carryover is a concern. Replace the filter element if discolored or "
            "if differential pressure across it exceeds 2 psi\n"
            "  - Fuel bottles (if equipped): check drain valves for condensation. Drain "
            "any accumulated liquid and note the volume",
            "Physical damage or fouling of fuel components causes intermittent symptoms "
            "that do not show up on pressure readings alone.",
            "Record condition of each component inspected: fuel valves (operating normally / "
            "sticking), regulator (normal / weeping / frozen), scrubber condensate volume, "
            "filter differential pressure"
        ),
        (
            "Reassemble any components that were opened. Remove LOTO. Open the fuel gas "
            "supply valve. Start the engine and allow it to reach operating temperature "
            "(160°F–185°F coolant).\n"
            "  - Monitor engine RPM stability — should hold within ±10 RPM of setpoint\n"
            "  - Monitor exhaust temperatures per cylinder (if pyrometers are available) — "
            "spread should be <75°F between cylinders\n"
            "  - Listen for misfires or rough running\n"
            "  - Load the compressor to normal operating load and run for 30 minutes\n"
            "  - If engine runs rough or detonation occurs, recheck BTU and fuel pressure "
            "under load (pressure may drop under flow that was not visible at static test)",
            "Fuel system repairs must be verified under full operating load. Static tests "
            "may not reveal issues that only appear at full fuel demand.",
            "Record: RPM at idle and loaded, exhaust temperatures per cylinder, run time, "
            "and any faults or performance issues observed during test"
        ),
        (
            "Complete the service report:\n"
            "  - Fuel pressures measured (supply and regulated, before and after)\n"
            "  - BTU settings (old → new)\n"
            "  - Components inspected and condition\n"
            "  - Parts replaced (part numbers)\n"
            "  - Scrubber/filter service performed\n"
            "  - Test run results (RPM, temperatures, stability)\n"
            "  - Current run hours\n"
            "  - Recommendation for follow-up gas analysis if one is not current",
            "Fuel system documentation is essential for tracking gas quality trends and "
            "predicting when BTU recalibration will be needed.",
            None
        ),
    ],
    "valve_failure": [
        (
            "SAFETY: Shut down the unit. Perform LOTO. Depressurize the compressor by "
            "opening the blowdown valve(s) or discharge vent. Verify zero pressure on the "
            "suction and discharge gauges before removing any valve covers. Wear safety "
            "glasses, leather gloves, and hearing protection.",
            "Compressor valve covers are under pressure. Removing a cover on a pressurized "
            "cylinder is a life-threatening hazard.",
            "Record LOTO tag number, blowdown time, and confirmed zero-pressure readings "
            "on suction and discharge gauges"
        ),
        (
            "Pull the maintenance history for this unit's compressor and engine valves. "
            "Identify:\n"
            "  - Last valve replacement date and run hours at replacement\n"
            "  - Current run hours (delta since last replacement)\n"
            "  - Any prior notes about valve condition (e.g., 'suction valve plate cracked')\n"
            "  - Whether this is an engine valve or compressor valve issue\n"
            "  ENGINE VALVES: symptoms include rough running, misfires, loss of power, "
            "high exhaust temps on one cylinder\n"
            "  COMPRESSOR VALVES: symptoms include low discharge pressure, high suction "
            "pressure, elevated temperatures, loss of capacity",
            "Distinguishing engine vs. compressor valve failure directs the technician to "
            "the correct component set. Run hours since last replacement indicate whether "
            "the failure is premature or within expected life.",
            "Record last valve replacement date, run hours at replacement, current run hours, "
            "and whether engine or compressor side is suspected"
        ),
        (
            "FOR COMPRESSOR VALVES: Remove the valve cover bolts using the correct socket "
            "(typically 3/4\" or 7/8\"). Remove the cover and set aside. Using the valve "
            "puller tool (or appropriate threaded rod for the valve style), extract the "
            "valve assembly.\n"
            "FOR ENGINE VALVES: Remove the rocker arm cover. Inspect the valve train:\n"
            "  - Rocker arms, push rods, and valve springs visible\n"
            "  - Check for obvious broken springs, bent push rods, or loose adjusters",
            "Physical extraction and inspection is the only definitive way to assess valve "
            "condition. Remote diagnostics can indicate which valve is suspect, but "
            "confirmation requires hands-on inspection.",
            "Record which valves were pulled: stage, position (suction/discharge), end "
            "(head/crank), or cylinder number for engine valves"
        ),
        (
            "Inspect each valve assembly in detail:\n"
            "  COMPRESSOR VALVES:\n"
            "  - Lay the valve flat and check for light passing through the plate-to-seat "
            "interface (no light should pass if sealing properly)\n"
            "  - Check valve plates/rings for chips, cracks, or wear grooves\n"
            "  - Check valve springs for breaks, fatigue marks, or unequal length\n"
            "  - Inspect the seat for erosion, pitting, or groove marks\n"
            "  - Measure spring free length and compare to OEM spec (replace if >10% shorter)\n"
            "  ENGINE VALVES:\n"
            "  - Measure valve lash (clearance) with a feeler gauge at each valve\n"
            "  - Compare to OEM spec (e.g., intake 0.010\", exhaust 0.015\" — consult manual)\n"
            "  - Check for burned or eroded valve faces\n"
            "  - Check valve stem for scoring or excessive play in the guide",
            "Specific measurements eliminate guesswork. A valve that 'looks okay' may still "
            "be out of spec and causing the performance issue.",
            "Record per valve: plate/ring condition, spring condition and free length, seat "
            "condition, and lash measurement (for engine valves). Photo any damaged components"
        ),
        (
            "Replace all components that are out of specification:\n"
            "  COMPRESSOR VALVES: Replace the complete valve assembly (plate, seat, springs, "
            "and guard as a set). Do not mix old and new components within a single valve. "
            "Use OEM part numbers from the unit parts book.\n"
            "  ENGINE VALVES: Adjust lash to OEM spec using a feeler gauge and adjusting "
            "screw. If lash cannot be set within spec, the valve or seat is worn — schedule "
            "a cylinder head removal for valve job.\n"
            "  - Lubricate valve components per OEM instructions before installation\n"
            "  - Ensure valve seats are clean and free of debris before reinstalling",
            "Replacing valve assemblies as complete sets ensures consistent performance. "
            "Mixing components risks mismatched spring rates and sealing failures.",
            "Record all parts replaced: part numbers, quantities, and which position "
            "(stage/end/cylinder) each was installed in"
        ),
        (
            "Reinstall valve assemblies and covers:\n"
            "  - Install new valve cover gaskets (never reuse)\n"
            "  - Torque valve cover bolts to OEM spec in a star pattern\n"
            "  - For engine valves: reinstall rocker arm covers with new gaskets\n"
            "Verify final lash/clearance settings one more time after everything is "
            "reassembled (settles differently under bolt load).",
            "Proper gasket and torque prevents leaks and ensures valve cover does not "
            "loosen under vibration.",
            "Record final torque values and post-assembly lash measurements"
        ),
        (
            "Remove LOTO. Start the unit and bring to operating conditions.\n"
            "  - For compressor valves: monitor suction and discharge pressures — they should "
            "return to normal operating range within 10 minutes\n"
            "  - For engine valves: listen for ticking or knocking at each cylinder. "
            "Abnormal ticking indicates lash is still not correct\n"
            "  - Run under load for 30 minutes minimum\n"
            "  - Monitor discharge temperatures — a repaired valve should show lower "
            "temperature on that stage vs. pre-repair readings\n"
            "  - If performance does not improve, the issue may be piston rings, packing, "
            "or cylinder liner — escalate to engineering",
            "Post-repair operating verification confirms the valve replacement resolved the "
            "issue. Temperature and pressure improvements are the key metrics.",
            "Record: pressures and temperatures at 10 and 30 minutes post-startup, any "
            "abnormal sounds, and comparison to pre-repair readings"
        ),
        (
            "Complete the service report:\n"
            "  - Valves inspected and their condition\n"
            "  - Valves/components replaced (position, part numbers)\n"
            "  - Lash/clearance measurements (before and after adjustment)\n"
            "  - Startup verification readings (pressure, temperature)\n"
            "  - Current run hours\n"
            "  - Recommended next valve inspection interval based on run-hour delta "
            "(e.g., if valve lasted 8,000 hours, recommend inspection at 7,000 hours)",
            "Valve replacement intervals are best set from the unit's own history. "
            "Documenting run hours at failure enables predictive scheduling.",
            None
        ),
    ],
    "cooling_system": [
        (
            "SAFETY: Allow the engine to cool for a minimum of 15 minutes before opening "
            "the coolant system. NEVER open a radiator cap on a hot engine — pressurized "
            "coolant causes severe burns. Wear safety glasses and chemical-resistant gloves. "
            "If the unit is running and overheating, shut it down from the panel and wait "
            "for coolant temp to drop below 120°F.",
            "Coolant systems operate at 12–16 psi and 180°F+. Opening the system while hot "
            "causes violent steam release and scalding.",
            "Record coolant temperature at panel before starting work, and time engine was "
            "allowed to cool"
        ),
        (
            "At the control panel, pull the coolant temperature history for the last 7 days. "
            "Note:\n"
            "  - Maximum temperature reached and when\n"
            "  - Whether temperature has been trending up gradually or spiked suddenly\n"
            "  - Any high-temperature shutdown events\n"
            "  - Ambient temperature at time of high-temp events (overheating on a 100°F day "
            "vs. a 40°F day has very different implications)",
            "Temperature trending distinguishes gradual degradation (blocked radiator, "
            "degraded coolant) from sudden failure (thermostat stuck, pump failure, hose burst).",
            "Record temperature readings with timestamps, any high-temp alarms, and ambient "
            "conditions"
        ),
        (
            "Once engine is cool, remove the radiator cap slowly (1/4 turn to release "
            "pressure, then fully remove). Check coolant level:\n"
            "  - Should be visible at the filler neck (within 1\" of the top)\n"
            "  - If low, estimate how low (e.g., '3 inches below filler neck')\n"
            "Test coolant condition:\n"
            "  - Use a refractometer or test strips to check freeze point and pH\n"
            "  - Freeze point should be per site requirements (typically -34°F / -37°C)\n"
            "  - pH should be 8.0–11.0 (below 8.0 = acidic, causing corrosion)\n"
            "  - Check for oil sheen on coolant surface (indicates head gasket or oil cooler leak)\n"
            "  - Check for rust particles or dark discoloration (indicates internal corrosion)",
            "Low coolant is the #1 cause of overheating. Coolant condition testing identifies "
            "whether the coolant itself has degraded and is causing internal corrosion.",
            "Record: coolant level (inches below filler neck), freeze point, pH, visual "
            "condition (clean / rusty / oil contaminated), and color"
        ),
        (
            "Inspect the cooling system components:\n"
            "  RADIATOR:\n"
            "  - Check for blocked or bent fins (use a fin comb to straighten if >20% bent)\n"
            "  - Look for debris (leaves, insects, cotton) packed between fin rows\n"
            "  - Check for coolant leaking from tanks or tubes\n"
            "  - Blow out debris with compressed air from the engine side outward\n"
            "  HOSES:\n"
            "  - Squeeze each hose — it should be firm but flexible. Spongy or brittle = replace\n"
            "  - Check for cracks, bulges, or soft spots at clamp points\n"
            "  - Check clamp tightness — should not rotate by hand\n"
            "  WATER PUMP:\n"
            "  - Check the weep hole at the bottom of the pump for coolant drips (indicates "
            "seal failure)\n"
            "  - Grab the fan/pulley and check for play in the bearing (should have zero "
            "wobble)\n"
            "  - Listen for bearing noise with a stethoscope when running (if safe to do so)",
            "Systematic inspection of each cooling circuit component prevents replacing parts "
            "that are not the root cause.",
            "Record condition of: radiator fins (% blocked), debris found, each hose "
            "(good / soft / cracked), clamp condition, water pump weep hole (dry / dripping), "
            "and bearing play (none / detectable)"
        ),
        (
            "Check the thermostat operation:\n"
            "  - Remove the thermostat housing (typically 2 bolts on the engine front)\n"
            "  - Pull the thermostat out and inspect: it should be fully closed at room "
            "temperature\n"
            "  - To bench test: place in a pot of water with a thermometer. Heat the water. "
            "The thermostat should start opening at the rated temperature stamped on it "
            "(typically 180°F / 82°C) and be fully open within 20°F above that\n"
            "  - If it does not open at rated temperature, or if it is stuck partially open "
            "at room temperature → replace it\n"
            "  - Install the new thermostat with a new housing gasket. Ensure the thermostat "
            "is oriented correctly (jiggle pin up, sensing element toward engine)",
            "A stuck-closed thermostat causes rapid overheating with no external leaks — it "
            "blocks coolant flow through the radiator entirely.",
            "Record: thermostat condition (open / closed / stuck), rated temperature, bench "
            "test result (opened at ___°F), and whether replaced"
        ),
        (
            "Top off or replace coolant as needed:\n"
            "  - If coolant was low, add premixed coolant matching the existing type "
            "(do NOT mix green and orange/OAT coolant)\n"
            "  - If coolant is contaminated (oil, rust, low pH): drain the entire system, "
            "flush with clean water, and refill with fresh premixed coolant\n"
            "  - Record the volume added or replaced\n"
            "  - After filling, run the engine for 5 minutes with the radiator cap off to "
            "burp air from the system. Top off again as the level drops.",
            "Air pockets in the cooling system create hot spots and prevent proper coolant "
            "circulation. Burping removes trapped air.",
            "Record: coolant type and volume added/replaced, and whether a full flush was performed"
        ),
        (
            "Install the radiator cap. Start the engine and run to operating temperature "
            "(180°F–195°F). Monitor:\n"
            "  - Coolant temperature should stabilize within the normal range (180°F–200°F) "
            "within 15 minutes\n"
            "  - Verify the cooling fan is engaging when temperature reaches the fan-on "
            "setpoint (typically 195°F–205°F)\n"
            "  - Check all repaired areas for leaks\n"
            "  - Run under load for 30 minutes and verify temperature does not climb above "
            "the high-temp alarm setpoint\n"
            "  - If temperature still climbs: the issue may be internal (head gasket blow-by "
            "pressurizing the cooling system) — perform a combustion gas test on the coolant "
            "and escalate if positive",
            "Thermal verification under load is essential. The cooling system may appear fine "
            "at idle but fail under the heat load of full compression.",
            "Record: coolant temperature at 5, 10, 15, and 30 minutes; fan engagement "
            "temperature; and any leaks observed during test"
        ),
        (
            "Complete the service report:\n"
            "  - Initial coolant level and condition\n"
            "  - Components inspected and their condition (radiator, hoses, pump, thermostat)\n"
            "  - Parts replaced (part numbers)\n"
            "  - Coolant added/replaced (type, volume)\n"
            "  - Temperature verification readings during test run\n"
            "  - Current run hours\n"
            "  - If overheating persists: document and recommend combustion gas test and/or "
            "engineering analysis",
            "Cooling system records track degradation rates and help predict when radiator "
            "cleaning or coolant changes should be scheduled.",
            None
        ),
    ],
    "electrical": [
        (
            "SAFETY: Shut down the unit from the control panel. Perform LOTO on the main "
            "disconnect and the engine. Verify zero voltage at the control panel using a "
            "voltmeter before opening any junction boxes or touching wiring. Wear safety "
            "glasses and insulated gloves rated for the system voltage (typically 120VAC "
            "control, 480VAC power).",
            "Electrical faults can cause shock or arc flash. Zero-energy verification with "
            "a meter is mandatory before touching any conductors.",
            "Record LOTO tag number, measured voltage at panel (should read 0V), and "
            "disconnect position"
        ),
        (
            "At the control panel, before shutting down power, read and record all active "
            "and stored fault codes. Navigate through the alarm history and record:\n"
            "  - Fault code number and description\n"
            "  - Date and time of each fault\n"
            "  - Sequence of events (which fault appeared first — this is often the root "
            "cause; subsequent faults are cascade effects)\n"
            "  - Clear all faults. If any return immediately, those are active conditions\n"
            "  - If the panel will not power on: check the main breaker, fuses, and battery "
            "(if equipped)",
            "Fault code sequence analysis identifies the root cause vs. cascade alarms. "
            "The first fault in the sequence is usually the trigger.",
            "Record every fault code: number, description, date/time, and whether it returned "
            "after clearing"
        ),
        (
            "Inspect field wiring and connectors starting at the sensor/component that "
            "generated the first fault code:\n"
            "  - Follow the wire from the sensor to the panel junction box\n"
            "  - Check for: chafed insulation, loose terminals, corroded connectors, "
            "moisture intrusion, rodent damage, and heat damage from proximity to exhaust\n"
            "  - At each connector: disconnect, inspect pins for corrosion or bent contacts, "
            "spray with electrical contact cleaner, and reconnect firmly\n"
            "  - Check conduit seals and weatherproofing for damage\n"
            "  - At the panel: verify the wire lands on the correct terminal per the wiring "
            "diagram. Check terminal tightness with a screwdriver (should not pull out with "
            "gentle tug)",
            "Environmental damage to field wiring is the most common electrical issue on "
            "compressor packages. Vibration, weather, and rodents degrade wiring over time.",
            "Record each wiring issue found: location, type of damage, connector condition, "
            "and photo of damaged wiring"
        ),
        (
            "Test the suspect sensor(s) with a digital multimeter (DMM):\n"
            "  - TEMPERATURE SENSORS (RTD/thermocouple): measure resistance (RTD) or millivolts "
            "(thermocouple). Compare to the sensor's published resistance/voltage table at "
            "ambient temperature. An RTD at 70°F should read ~109.7 ohms for PT100.\n"
            "  - PRESSURE TRANSDUCERS: apply known pressure with a hand pump and verify the "
            "4–20mA output is proportional. 4mA = 0 pressure, 20mA = full scale. Calculate "
            "expected mA for the applied pressure.\n"
            "  - VIBRATION SENSORS: check cable resistance (typically <10 ohms); infinite = "
            "open cable; 0 ohms = short\n"
            "  - PROXIMITY/SPEED SENSORS: check gap (per OEM spec, typically 0.030\"–0.060\") "
            "and measure output signal\n"
            "If sensor reading deviates >5% from expected value at a known reference point, "
            "replace the sensor.",
            "Quantitative sensor testing with a DMM prevents replacing good sensors based "
            "on intermittent panel readings. The fault may be in the wiring, not the sensor.",
            "Record per sensor tested: sensor type, location, measured value, expected value, "
            "and pass/fail determination"
        ),
        (
            "Replace faulty sensors or wiring:\n"
            "  - Use exact replacement sensors (same make, model, and range). Verify the part "
            "number against the unit parts list.\n"
            "  - For wiring repairs: use appropriately rated wire (gauge, insulation type, "
            "temperature rating). Strip 3/8\" of insulation, crimp with proper terminals, "
            "and shrink-tube all connections\n"
            "  - Re-route any wiring that was damaged by heat or chafing — add protection "
            "(loom, conduit, or standoff clamps) to prevent recurrence\n"
            "  - After replacing a sensor, calibrate it per OEM procedure if required "
            "(some pressure transducers require zero/span adjustment)",
            "Exact replacement and proper installation technique prevents repeat failures. "
            "Rerouting damaged wire addresses the root cause of the damage.",
            "Record: sensor replaced (part number, location), wiring repaired (location, "
            "method), and any rerouting performed"
        ),
        (
            "Remove LOTO. Re-energize the panel. Clear all fault codes.\n"
            "  - Verify all sensor readings are displaying correctly on the panel\n"
            "  - Compare panel readings to a handheld reference (e.g., check panel temp "
            "reading vs. an IR thermometer on the engine)\n"
            "  - Start the engine and load the compressor\n"
            "  - Monitor for fault code recurrence for 30 minutes under load\n"
            "  - If faults return: the issue may be intermittent and load/vibration-related — "
            "gently flex wire harnesses while running to try to reproduce the fault (use "
            "insulated tools, do not touch moving parts)",
            "Verification under load is critical for electrical issues because vibration and "
            "heat during operation can cause intermittent faults that do not appear at rest.",
            "Record: all sensor readings at startup and after 30 minutes under load, any "
            "faults that returned, and flex-test results"
        ),
        (
            "Complete the service report:\n"
            "  - All fault codes found (number, description, active/stored)\n"
            "  - Wiring issues found and repaired (location, damage type)\n"
            "  - Sensors tested and results (value vs. expected)\n"
            "  - Sensors/wiring replaced (part numbers)\n"
            "  - Calibration performed\n"
            "  - Startup verification readings\n"
            "  - Current run hours\n"
            "  - If intermittent fault persists: document the conditions under which it "
            "occurs and recommend vibration or thermal monitoring",
            "Electrical fault records enable pattern detection — e.g., if the same sensor "
            "fails on multiple units, it may be a batch defect or environmental issue.",
            None
        ),
    ],
    "lubrication": [
        (
            "SAFETY: Shut down the unit. Wait 5 minutes for oil to drain back to the sump. "
            "Perform LOTO. Wear safety glasses, nitrile gloves, and coveralls. Place a drip "
            "pan under the engine before opening any oil system components. Have absorbent "
            "pads ready for spills.",
            "Hot oil causes burns. Allowing drain-back time gives a more accurate dipstick "
            "reading and reduces the risk of oil spraying from pressurized lines.",
            "Record LOTO tag number and time waited for drain-back"
        ),
        (
            "Check the oil analysis history for this unit:\n"
            "  - Pull the last 3 oil sample reports (if available in the maintenance system "
            "or site office)\n"
            "  - Look for trends in: wear metals (Fe, Cu, Pb, Al), viscosity change, "
            "coolant contamination (Na, K, glycol), fuel dilution, soot, and oxidation\n"
            "  - If Fe (iron) trend is increasing: bearing or cylinder wear is accelerating\n"
            "  - If coolant markers (Na, K, or glycol) are present: head gasket or oil cooler "
            "leak is mixing coolant into oil — this is critical\n"
            "  - If viscosity has dropped >10% from baseline: fuel dilution or thermal "
            "breakdown",
            "Oil analysis trends predict failure before it happens. A single sample shows "
            "current condition; the trend over 3+ samples shows the rate of degradation.",
            "Record the last 3 sample dates, key values (Fe, viscosity, coolant markers), "
            "and trend direction (stable / increasing / critical)"
        ),
        (
            "Pull the engine dipstick. Check the oil level:\n"
            "  - Level should be between the ADD and FULL marks\n"
            "  - If below ADD: the engine has consumed or leaked oil since last service\n"
            "  - If above FULL: possible coolant or fuel contamination diluting the oil\n"
            "Check oil condition visually:\n"
            "  - Wipe a sample on a white paper towel and observe:\n"
            "    • Amber/brown = normal for used oil\n"
            "    • Black and gritty = high soot or extended interval\n"
            "    • Milky or creamy = water/coolant contamination (STOP — do not run the engine)\n"
            "    • Shiny metallic particles = bearing or component failure (STOP — investigate)\n"
            "  - Smell the oil: fuel smell indicates fuel dilution from misfires or injector "
            "leaks",
            "Visual and sensory oil checks catch critical conditions that oil analysis "
            "reports (sent to a lab) take days to reveal.",
            "Record: dipstick level (below ADD / ADD to FULL / above FULL), color, clarity, "
            "smell, and presence of any metallic particles"
        ),
        (
            "Inspect the engine and compressor for external oil leaks:\n"
            "  - Check the valve cover gaskets (common leak point — look for oil running "
            "down the sides of the engine)\n"
            "  - Check the oil pan gasket and drain plug\n"
            "  - Check the front and rear crankshaft seals (look for oil at the harmonic "
            "balancer and flywheel housing)\n"
            "  - Check the oil filter housing and oil cooler fittings\n"
            "  - On the compressor side: check the compressor crankcase gasket, packing "
            "case area, and oil supply/return lines\n"
            "  - Trace any oil found to its highest point to identify the actual source",
            "External oil loss causes low level and eventually low pressure. Finding the "
            "leak source prevents simply adding oil without fixing the problem.",
            "Record each leak found: location, severity (seep / drip / stream), and estimated "
            "volume loss"
        ),
        (
            "Check oil pressure:\n"
            "  - If the unit has a mechanical oil pressure gauge, record the reading "
            "(engine must be at operating temperature for accurate reading)\n"
            "  - If panel only: record the panel oil pressure reading\n"
            "  - Compare to OEM spec:\n"
            "    • Typical: 40–60 psi at operating speed, >10 psi at idle\n"
            "    • If below spec at operating speed: suspect worn bearings, worn oil pump, "
            "or oil dilution reducing viscosity\n"
            "    • If pressure fluctuates: suspect aerated oil (level too low or too high), "
            "oil pump cavitation, or pickup tube leak\n"
            "  - If oil pressure is critically low (<10 psi at operating speed): DO NOT "
            "continue running the engine — immediate shutdown to prevent bearing damage",
            "Oil pressure is the single most critical engine protection parameter. Running "
            "with low oil pressure destroys crankshaft bearings in minutes.",
            "Record: oil pressure at idle, oil pressure at operating speed, OEM spec, and "
            "comparison result (within spec / low / critical)"
        ),
        (
            "If an oil change is due (by run hours, calendar, or condition):\n"
            "  1. Place drain pan under the oil pan drain plug\n"
            "  2. Remove drain plug with correct wrench (typically 3/4\" or 15/16\")\n"
            "  3. Allow all oil to drain completely (10–15 minutes minimum)\n"
            "  4. While draining, remove the old oil filter using a filter wrench. Note the "
            "filter part number\n"
            "  5. Apply a thin film of clean oil to the new filter gasket\n"
            "  6. Install the new filter — hand tighten until gasket contacts, then 3/4 turn "
            "more (do NOT use a wrench to tighten)\n"
            "  7. Reinstall drain plug with new crush washer. Torque to spec (typically "
            "25–35 ft-lbs)\n"
            "  8. Fill engine with correct oil type and volume per OEM spec (e.g., CAT DEO "
            "15W-40, typical fill 6–12 gallons depending on engine model)\n"
            "  9. Install dipstick, start engine, and run for 30 seconds at idle\n"
            "  10. Shut down, wait 2 minutes, and recheck dipstick — top off to FULL mark\n"
            "  11. Dispose of used oil and filter per site hazmat procedures",
            "Proper oil change procedure ensures complete old oil removal and prevents "
            "common mistakes (double-gasketed filter, wrong viscosity, under/over fill).",
            "Record: volume drained, volume added, oil type and brand, filter part number, "
            "drain plug torque, and disposal method"
        ),
        (
            "After oil change or top-off, remove LOTO. Start the engine:\n"
            "  - Verify oil pressure comes up within 10 seconds of start (if not, shut down "
            "immediately and investigate)\n"
            "  - Run at idle for 2 minutes, check for leaks at the filter and drain plug\n"
            "  - Record oil pressure at idle and at operating speed\n"
            "  - Check the dipstick one more time after 5 minutes of running\n"
            "  - Run under load for 15 minutes and verify pressure remains stable",
            "Post-service oil pressure verification catches filter misinstallation, drain "
            "plug leaks, and confirms oil level is correct under operating conditions.",
            "Record: oil pressure at idle, at operating speed, at 15 minutes under load; "
            "dipstick level; and any leaks observed"
        ),
        (
            "Complete the service report:\n"
            "  - Oil level and condition (before service)\n"
            "  - Oil analysis trends (from last 3 samples if available)\n"
            "  - Leaks found and repaired\n"
            "  - Oil change performed: volume drained/added, oil type, filter part number\n"
            "  - Oil pressure readings (before and after)\n"
            "  - Current run hours\n"
            "  - Recommendation for next oil sample date and next oil change interval",
            "Oil service records feed directly into condition-based maintenance intervals. "
            "Accurate records enable extending or shortening intervals based on actual "
            "oil condition.",
            None
        ),
    ],
    "filter_maintenance": [
        (
            "SAFETY: Shut down the unit. Perform LOTO. Allow turbocharger (if equipped) to "
            "coast down fully before opening the air intake. Wear safety glasses and a dust "
            "mask when removing dirty filters. Have a new filter and clean rags ready.",
            "Air filter service requires the engine to be stopped. Turbocharger coast-down "
            "takes 30–60 seconds — opening the intake before coast-down risks foreign object "
            "ingestion and impeller damage.",
            "Record LOTO tag number and confirm turbo coast-down complete"
        ),
        (
            "Check the air filter restriction indicator (if equipped):\n"
            "  - Read the indicator gauge (typically a color-coded gauge or inches-of-water "
            "reading on the air filter housing)\n"
            "  - GREEN zone or <15\" H2O = filter is okay\n"
            "  - YELLOW zone or 15\"–25\" H2O = filter is loading, plan replacement\n"
            "  - RED zone or >25\" H2O = filter is restricted, replace now\n"
            "  - Reset the indicator after reading (push the reset button)\n"
            "  - If no indicator: remove the filter and visually inspect. Hold up to light — "
            "if you cannot see light through the media, it needs replacement",
            "The restriction indicator gives an objective measure of filter loading. "
            "Relying only on visual inspection can miss internal contamination.",
            "Record restriction indicator reading (inches H2O or zone color), and whether "
            "filter was replaced or passed"
        ),
        (
            "Replace the air filter:\n"
            "  1. Unlatch or unbolt the air filter housing cover\n"
            "  2. Carefully remove the dirty filter — do NOT tap or shake it over the "
            "open intake (debris will fall into the engine)\n"
            "  3. Before installing the new filter, wipe the inside of the housing and "
            "the sealing surfaces with a clean damp rag to remove accumulated dust\n"
            "  4. Inspect the new filter for shipping damage (torn media, crushed seals)\n"
            "  5. Install the new filter — ensure the sealing gasket seats evenly all "
            "the way around. There should be no gaps\n"
            "  6. Close and latch/bolt the housing cover\n"
            "  7. Verify the filter is seated by checking that the cover closes flush "
            "(if the filter is misaligned, the cover will not close properly)\n"
            "Record the old filter condition and the new filter part number.",
            "Improper air filter installation allows unfiltered air into the engine, "
            "causing accelerated cylinder and ring wear. Clean sealing surfaces are critical.",
            "Record: old filter condition (light dust / heavy loading / damaged), new filter "
            "part number, and housing condition (clean / debris present)"
        ),
        (
            "Check the oil filter:\n"
            "  - Refer to the PM schedule for the oil filter change interval (typically "
            "every oil change or every 500–1,000 hours)\n"
            "  - If due: replace the oil filter following the oil change procedure (drain oil "
            "first, install new filter with oiled gasket, hand-tight plus 3/4 turn)\n"
            "  - If not due: visually inspect the filter housing for leaks and note the run "
            "hours remaining until the next scheduled change\n"
            "Check the fuel filter (if equipped):\n"
            "  - Gas fuel filters/strainers: check differential pressure across the filter "
            "(if gauge equipped). Replace if >2 psi differential\n"
            "  - Clean fuel strainer screens if applicable\n"
            "  - Check fuel filter bowl for condensation — drain if liquid is present",
            "Checking all filters during a filter service visit prevents unscheduled return "
            "trips. Filter service is most cost-effective when done together.",
            "Record per filter: type, current run hours, last change date, and action taken "
            "(replaced / inspected / not due)"
        ),
        (
            "Remove LOTO. Start the engine and run for 5 minutes:\n"
            "  - Verify no air leaks around the filter housing (listen for whistling or "
            "hissing at the housing seal)\n"
            "  - If the oil filter was replaced: verify oil pressure is normal and no leaks "
            "at the filter base\n"
            "  - Check the restriction indicator reading with a clean filter installed — "
            "it should read zero or green zone",
            "Post-installation verification catches installation errors before the unit "
            "is left running unattended.",
            "Record: restriction indicator reading with new filter, any leaks observed, "
            "and oil pressure if oil filter was replaced"
        ),
        (
            "Complete the service report:\n"
            "  - Filters replaced: type, old condition, new part number\n"
            "  - Restriction readings (before and after replacement)\n"
            "  - Run hours at replacement\n"
            "  - Fuel filter/strainer condition\n"
            "  - Next scheduled filter change date/hours\n"
            "  - Any housing or seal issues noted",
            "Filter replacement records drive interval optimization. Tracking restriction "
            "at replacement helps determine if intervals should be shortened or extended.",
            None
        ),
    ],
    "shutdown": [
        (
            "SAFETY: Approach the unit cautiously. A recent shutdown may have been caused "
            "by a hazardous condition (gas leak, fire, overspeed). Check for:\n"
            "  - Gas smell or visible gas leak (use LEL detector if available)\n"
            "  - Signs of fire or overheating (smoke, discoloration, hot surfaces)\n"
            "  - Fluid puddles under the unit\n"
            "If any hazard is detected, do NOT attempt to restart. Secure the area and "
            "contact HSE / supervision. If the area is safe, proceed to diagnosis.",
            "Unplanned shutdowns can be triggered by dangerous conditions. The first "
            "priority is technician safety, not getting the unit running.",
            "Record: time of arrival, visual assessment of unit condition (safe / hazard "
            "detected), LEL reading if taken, and any visible damage"
        ),
        (
            "At the control panel, read the shutdown fault code:\n"
            "  - Record the EXACT code number and description (e.g., 'SD-101: High Jacket "
            "Water Temperature')\n"
            "  - Check the alarm history for events leading up to the shutdown — often a "
            "warning alarm precedes the shutdown by minutes or hours\n"
            "  - Record the sequence: warning alarm → shutdown alarm → any post-shutdown faults\n"
            "  - Note the run hours and operating parameters at the time of shutdown "
            "(the panel may store a 'snapshot' of readings at trip)\n"
            "  - Classify the shutdown type:\n"
            "    • HIGH TEMPERATURE → go to Cooling System workflow\n"
            "    • LOW OIL PRESSURE → go to Lubrication workflow\n"
            "    • DETONATION → go to Detonation workflow\n"
            "    • HIGH VIBRATION → go to Vibration/Noise workflow\n"
            "    • OVERSPEED → check governor and fuel system\n"
            "    • PANEL/ELECTRICAL → go to Electrical workflow\n"
            "    • UNKNOWN/GENERIC → proceed with this workflow",
            "The fault code is the most important diagnostic data point. The correct "
            "sub-workflow depends entirely on the shutdown cause classification.",
            "Record: fault code number, description, alarm sequence with timestamps, "
            "operating parameters at trip (temperature, pressure, RPM, oil pressure), "
            "and run hours"
        ),
        (
            "If the shutdown cause is clear and has been addressed (per the appropriate "
            "sub-workflow), prepare for a restart attempt:\n"
            "  - Verify all repairs are complete and covers/guards are reinstalled\n"
            "  - Walk around the unit and check for tools, rags, or loose items\n"
            "  - Verify oil level, coolant level, and fuel supply\n"
            "  - Clear all fault codes from the panel\n"
            "  - If the shutdown was HIGH TEMPERATURE or LOW OIL PRESSURE, verify the "
            "condition is corrected (coolant temp below alarm, oil pressure at rest)\n"
            "  - Stand clear of the unit (not in line with rotating components) during start",
            "Pre-start checks prevent a second immediate shutdown and ensure the unit is "
            "safe to restart. A hasty restart without checking can cause additional damage.",
            "Record: pre-start checklist completion (oil level, coolant level, fuel status, "
            "faults cleared, visual inspection)"
        ),
        (
            "Start the unit using the panel START sequence:\n"
            "  - Monitor the startup closely — watch for:\n"
            "    • Oil pressure to come up within 10 seconds\n"
            "    • Engine to reach idle speed smoothly (no stumbling or misfires)\n"
            "    • No immediate fault codes\n"
            "  - If the engine fails to start after 3 cranking attempts (per OEM limit — "
            "typically 10–15 seconds per crank), STOP and investigate further (do not over-crank)\n"
            "  - If the engine starts and runs, allow it to warm up to operating temperature "
            "at idle (5–10 minutes)\n"
            "  - Gradually load the compressor\n"
            "  - Monitor the parameter that caused the original shutdown for 30 minutes:\n"
            "    • If high-temp shutdown: watch coolant temp continuously\n"
            "    • If low-oil shutdown: watch oil pressure continuously\n"
            "    • If detonation shutdown: listen for knock and watch fault codes",
            "Careful monitoring during and after restart catches recurring conditions "
            "before they cause another shutdown or additional equipment damage.",
            "Record: start result (successful / failed), time to oil pressure, idle RPM, "
            "any faults during startup, and monitored parameter readings at 5, 15, and "
            "30 minutes under load"
        ),
        (
            "If the shutdown recurs during the test run, or if the original fault returns:\n"
            "  - Do NOT attempt more than 2 restarts for the same fault\n"
            "  - Record the exact conditions at the second shutdown (parameters, time since "
            "restart, load level)\n"
            "  - Escalate to senior technician or engineering with a summary of:\n"
            "    • Original fault code and conditions\n"
            "    • Repairs attempted\n"
            "    • Second shutdown conditions\n"
            "  - Leave the unit shut down with LOTO applied until the escalation is reviewed",
            "Repeated shutdowns for the same cause indicate the root cause was not fully "
            "addressed. Continued restart attempts risk equipment damage.",
            "Record: second shutdown fault code, conditions, and escalation contact/time"
        ),
        (
            "Complete the service report:\n"
            "  - Original shutdown fault code and time\n"
            "  - Alarm sequence leading to shutdown\n"
            "  - Operating parameters at trip\n"
            "  - Root cause investigation findings\n"
            "  - Repairs performed (with part numbers if components replaced)\n"
            "  - Restart result and 30-minute monitoring data\n"
            "  - If escalated: escalation details and status\n"
            "  - Current run hours\n"
            "  - Recommendation for follow-up (e.g., 'monitor for 24 hours', 'schedule "
            "engineering review')",
            "Shutdown events are the highest-value data for reliability analysis. Every "
            "shutdown should be fully documented regardless of severity.",
            None
        ),
    ],
    "vibration_noise": [
        (
            "SAFETY: If the unit is running and vibration is severe (visible shaking, "
            "loose bolts, or guard contact), shut it down immediately from the panel. "
            "Do NOT approach rotating components until the unit is fully stopped. Perform "
            "LOTO. Wear safety glasses and hearing protection.",
            "Severe vibration can cause guard failure, bolt ejection, or coupling "
            "disintegration. Approach only after the unit is fully stopped and locked out.",
            "Record: was the unit running when you arrived? Severity of vibration "
            "(slight / moderate / severe / visible shaking), and any loose or damaged "
            "guards observed"
        ),
        (
            "Interview operations staff or review the alarm log:\n"
            "  - When did the vibration/noise start? (Sudden = component failure; gradual = wear)\n"
            "  - Does it change with load or speed?\n"
            "  - Is it continuous or intermittent?\n"
            "  - Where does it seem to come from? (Engine, compressor, coupling, auxiliary)\n"
            "  - Any recent maintenance that could have caused a change? (Coupling "
            "reinstallation, bearing replacement, belt change)\n"
            "  - Pull vibration alarm history from the panel if available",
            "Characterizing the vibration before inspection narrows the possible sources. "
            "Sudden onset after maintenance strongly suggests the recent work introduced "
            "the issue.",
            "Record: onset timing, load/speed relationship, continuous vs. intermittent, "
            "perceived location, and any recent maintenance performed"
        ),
        (
            "With the unit stopped and locked out, perform a hands-on mechanical inspection:\n"
            "  COUPLING:\n"
            "  - Remove the coupling guard. Check the coupling element (rubber, disc, or "
            "grid) for wear, cracking, or missing pieces\n"
            "  - Check coupling alignment using a straight edge and feeler gauges (or dial "
            "indicator if available). Angular and offset misalignment should be within "
            "OEM tolerance (typically <0.005\" offset, <0.001\" per inch angular)\n"
            "  - Check coupling bolts for tightness\n"
            "  BEARINGS:\n"
            "  - Grab the engine flywheel or crankshaft pulley and push/pull to check for "
            "main bearing play (should have zero detectable play by hand)\n"
            "  - On the compressor, grab the crosshead and push/pull to check crosshead "
            "bearing and pin play\n"
            "  MOUNTING:\n"
            "  - Check all skid mounting bolts — torque-check or tap with a hammer (loose "
            "bolts will sound dull instead of ringing)\n"
            "  - Check engine and compressor mounting bolts to the sub-base\n"
            "  BELTS (if equipped):\n"
            "  - Check belt tension (deflection per OEM spec, typically 1/2\" per foot of span)\n"
            "  - Check for cracking, glazing, or uneven wear",
            "Systematic mechanical inspection covers the most common vibration sources in "
            "priority order: coupling, bearings, mounting, and belts.",
            "Record per component: condition (good / worn / damaged / loose), measurements "
            "(alignment values, belt deflection, bolt torque), and photo of any damage"
        ),
        (
            "If no obvious issue was found with the unit stopped, prepare for a running "
            "vibration assessment (requires experienced technician):\n"
            "  - Remove LOTO temporarily. Ensure all guards are reinstalled\n"
            "  - Start the unit and bring to idle\n"
            "  - Using a vibration meter or mechanic's stethoscope, check vibration levels "
            "at each bearing housing (engine front/rear, compressor main bearings, and "
            "each crosshead)\n"
            "  - Compare to baseline readings if available (from commissioning or previous PM)\n"
            "  - General guideline: <0.3 ips velocity = good; 0.3–0.7 ips = acceptable; "
            ">0.7 ips = investigate; >1.0 ips = shut down\n"
            "  - Listen with the stethoscope at each bearing and cylinder for metallic "
            "knocking, grinding, or periodic thumping\n"
            "  - Increase to operating speed and load — note if vibration increases with "
            "speed (imbalance) or load (mechanical clearance)",
            "Running vibration assessment pinpoints the source that cannot be identified "
            "with the unit stopped. Vibration meters quantify severity objectively.",
            "Record per measurement point: location, vibration reading (ips), and "
            "subjective description of sound (smooth / rough / knocking / grinding)"
        ),
        (
            "Based on findings, perform repairs:\n"
            "  - COUPLING MISALIGNMENT: Realign per OEM procedure. Loosen mounting bolts, "
            "use shims or jack bolts to correct offset and angular alignment, re-torque "
            "mounting bolts, and reverify alignment\n"
            "  - WORN COUPLING ELEMENT: Replace with OEM part. Realign after installation\n"
            "  - LOOSE MOUNTING: Torque all bolts to spec. Apply thread-locking compound "
            "if bolts have loosened repeatedly\n"
            "  - BELT ISSUES: Replace belts as a matched set (never replace just one belt "
            "in a multi-belt drive). Tension to OEM spec\n"
            "  - BEARING NOISE: If bearing is confirmed noisy, schedule bearing replacement. "
            "Do not continue running with a damaged bearing — escalate if bearing replacement "
            "is beyond field capability",
            "Each vibration root cause requires a specific repair method. Treating the wrong "
            "root cause wastes time and does not resolve the vibration.",
            "Record: repair performed, parts replaced (part numbers), alignment readings "
            "(before and after), and torque values applied"
        ),
        (
            "Reinstall all guards. Remove LOTO. Start the unit and load:\n"
            "  - Repeat vibration measurements at the same points as the pre-repair assessment\n"
            "  - Compare before and after readings — vibration should have decreased\n"
            "  - Run under load for 30 minutes and verify vibration is stable (not increasing)\n"
            "  - If vibration has not improved: the source was not correctly identified — "
            "shut down and escalate to vibration analysis specialist (recommend portable "
            "vibration analyzer/FFT for frequency-based diagnosis)",
            "Post-repair vibration comparison is the only objective way to confirm the "
            "repair was effective.",
            "Record: post-repair vibration readings at each point, comparison to pre-repair, "
            "and 30-minute stability observation"
        ),
        (
            "Complete the service report:\n"
            "  - Vibration complaint description and onset timing\n"
            "  - All inspection findings (coupling, bearings, mounting, belts)\n"
            "  - Running vibration measurements (before and after repair)\n"
            "  - Repair performed and parts used\n"
            "  - Current run hours\n"
            "  - If unresolved: escalation recommendation with supporting data for the "
            "vibration specialist",
            "Vibration records with quantitative measurements enable trend-based predictive "
            "maintenance and early detection of developing bearing or coupling issues.",
            None
        ),
    ],
    "seal_gasket": [
        (
            "SAFETY: Shut down the unit. Perform LOTO. If the seal/gasket involves a "
            "pressurized system (compressor cylinders, gas piping), depressurize by opening "
            "the blowdown valve and verify zero pressure before disassembly. Wear safety "
            "glasses, chemical-resistant gloves, and coveralls.",
            "Pressurized systems can spray fluids or gas when seals or gasket joints are "
            "opened. Full depressurization is mandatory before any disassembly.",
            "Record LOTO tag number, blowdown time, and zero-pressure verification"
        ),
        (
            "Review the maintenance history for this seal/gasket location:\n"
            "  - Has this seal or gasket been replaced before? When and at what run hours?\n"
            "  - If this is a repeat failure at the same location: the root cause may be "
            "misalignment, incorrect spec, or operating condition (e.g., excessive temperature "
            "or pressure)\n"
            "  - If first occurrence: determine the run hours since installation to "
            "establish a baseline life expectancy",
            "Seal/gasket life data is critical for predicting future replacements. "
            "Repeat failures at the same location always have an underlying root cause.",
            "Record: last replacement date, run hours at last replacement, current run hours, "
            "and whether this is a first or repeat failure"
        ),
        (
            "Identify the specific failing component:\n"
            "  - COMPRESSOR PACKING: check distance piece for oil mist or gas leaking past "
            "the packing rings. Measure packing leak rate if a monitoring system is installed.\n"
            "    • Slight weeping is normal for new packing break-in\n"
            "    • Steady drip or visible gas flow = packing is worn\n"
            "  - GASKETS: identify the joint (valve cover, flange, crankcase, oil cooler, "
            "heat exchanger). Look for fluid weeping along the mating line\n"
            "  - O-RINGS: identify the groove location and the fluid being sealed\n"
            "  - SHAFT SEALS: check for fluid leaking along the shaft path (crankshaft, "
            "pump shafts, etc.)\n"
            "Record the exact location, component type, and fluid/gas being sealed.",
            "Correct identification of the component type and its location determines the "
            "correct replacement procedure and part number.",
            "Record: component type (packing / gasket / O-ring / shaft seal), exact location "
            "(e.g., 'Stage 2 compressor packing case'), and fluid/gas being sealed"
        ),
        (
            "Disassemble to access the component:\n"
            "  - Follow OEM disassembly sequence for the specific joint\n"
            "  - Mark bolts and covers with a paint pen for reassembly reference if needed\n"
            "  - After removing the old seal/gasket, inspect it:\n"
            "    • Extrusion (material pushed out of the groove) = excessive pressure or wrong "
            "material hardness\n"
            "    • Hardening/cracking = thermal degradation or chemical attack\n"
            "    • Abrasion/scoring = shaft or bore surface damage\n"
            "    • Flat/compressed with no spring-back = normal end-of-life wear\n"
            "  - Inspect the mating surfaces:\n"
            "    • Run a fingernail across sealing surfaces — grooves, scratches, or pitting "
            "will destroy a new seal\n"
            "    • For flanges: check with a straightedge for warping (no light should pass "
            "under the straightedge)\n"
            "    • Polish minor scratches with 400-grit emery cloth. If deep grooves are "
            "present, the component must be machined or replaced",
            "The condition of the old seal reveals why it failed. Mating surface condition "
            "must be verified — installing a new seal on a damaged surface guarantees early "
            "re-failure.",
            "Record: old seal condition (extruded / hardened / abraded / worn flat), mating "
            "surface condition (smooth / scratched / grooved / warped), and photo of both"
        ),
        (
            "Install the new seal, gasket, or packing:\n"
            "  - Verify the replacement part number matches the OEM specification. Measure "
            "the new component against the old one (ID, OD, cross-section) as a double-check\n"
            "  - For O-RINGS: lightly lubricate with compatible grease/oil before installation. "
            "Do not roll or twist — seat evenly in the groove\n"
            "  - For GASKETS: position on clean, dry mating surfaces. Ensure all bolt holes "
            "align before starting any bolts. Never use sealant unless OEM specifically calls "
            "for it\n"
            "  - For PACKING: install rings one at a time with staggered gaps (120° offset "
            "for 3-ring sets). Do not force — rings should slide into the case. Snug packing "
            "gland nuts finger-tight plus 1/6 turn alternating sides\n"
            "  - For SHAFT SEALS: press in evenly using a seal driver (never hammer directly "
            "on the seal face). Ensure the lip faces the correct direction (lip toward "
            "pressure/fluid side)",
            "Each seal type has a specific installation technique. Incorrect installation "
            "is the most common cause of new seal failure.",
            "Record: new part number installed, installation method, and any notes on fit "
            "(e.g., 'required light pressing', 'gasket alignment required shifting')"
        ),
        (
            "Reassemble the joint per OEM torque and sequence specifications:\n"
            "  - Torque flange/cover bolts in a star pattern to OEM spec in at least 3 "
            "passes (50%, 75%, 100% of final torque)\n"
            "  - For packing: do NOT over-tighten. Packing should have slight clearance "
            "for initial break-in. Plan to retighten after 2–4 hours of run time\n"
            "  - Remove LOTO. Re-pressurize the system slowly\n"
            "  - Check for leaks at the repaired joint before starting the unit\n"
            "  - Start the unit and run to operating temperature and pressure\n"
            "  - Recheck the joint for leaks after 15 minutes under load\n"
            "  - For packing: check leak rate after 1 hour of running and tighten gland "
            "nuts 1/6 turn if weeping is excessive",
            "Gradual torque sequencing prevents uneven loading which warps gaskets and "
            "causes leaks. Packing requires break-in time before final adjustment.",
            "Record: torque values applied, re-pressurization result (leak / no leak), "
            "and post-start leak check result"
        ),
        (
            "Complete the service report:\n"
            "  - Component replaced (type, location, OEM part number)\n"
            "  - Old component condition and failure mode\n"
            "  - Mating surface condition\n"
            "  - Installation details (torque, method)\n"
            "  - Leak test result\n"
            "  - Current run hours\n"
            "  - If repeat failure: root cause assessment and recommendation (e.g., "
            "'alignment check needed', 'upgrade seal material', 'reduce operating temperature')\n"
            "  - Schedule follow-up packing adjustment if applicable (2–4 hours after startup)",
            "Seal/gasket records with failure mode analysis enable material upgrades and "
            "interval optimization for future replacements.",
            None
        ),
    ],
    "ignition_system": [
        (
            "SAFETY: Shut down the unit. Perform LOTO. Disconnect the ignition system "
            "power supply (usually a fuse or breaker in the panel). Verify no spark by "
            "grounding a plug wire to the engine block and cranking briefly (observe from "
            "a safe distance — no spark should occur). Wear safety glasses and insulated "
            "gloves.",
            "Ignition system components carry high voltage (20,000–40,000V for some "
            "systems). De-energizing and verifying is mandatory before handling plug wires "
            "or ignition modules.",
            "Record LOTO tag number, ignition power disconnect confirmation, and no-spark "
            "verification"
        ),
        (
            "Review the ignition system maintenance history:\n"
            "  - Last spark plug replacement date and run hours\n"
            "  - Last ignition timing check date\n"
            "  - Any prior notes about misfires, detonation, or ignition component replacement\n"
            "  - Current run hours (calculate hours since last plug change)\n"
            "  - OEM recommended plug change interval (typically 4,000–8,000 hours for "
            "natural gas engines)\n"
            "  If run hours since last change exceed 80% of the OEM interval, replacement "
            "is recommended regardless of visual condition.",
            "Run hours since last replacement determine whether the plugs have reached "
            "their expected service life. Proactive replacement prevents misfires.",
            "Record: last plug change date, run hours at change, current run hours, "
            "hours since change, and OEM interval"
        ),
        (
            "Remove and inspect each spark plug (one cylinder at a time to maintain "
            "firing order):\n"
            "  1. Pull the plug wire boot by gripping the boot (not the wire) and twisting "
            "while pulling\n"
            "  2. Use compressed air to blow debris out of the plug well before removing "
            "the plug (prevents debris falling into the cylinder)\n"
            "  3. Remove the plug with the correct spark plug socket (13/16\" or 18mm)\n"
            "  4. Inspect each plug:\n"
            "    - ELECTRODE GAP: measure with a wire-type feeler gauge. OEM spec is "
            "typically 0.010\"–0.015\" (consult engine manual)\n"
            "    - ELECTRODE CONDITION: sharp square edges = good; rounded/eroded = worn; "
            "melted = severe detonation\n"
            "    - INSULATOR: clean white/tan = good; sooty black = rich mixture or misfire; "
            "oil-wet = oil contamination; heavy white crust = ash buildup\n"
            "    - PORCELAIN: check for cracks (even hairline cracks cause misfire under "
            "compression)\n"
            "  5. Record findings per cylinder before moving to the next plug",
            "Per-cylinder inspection identifies whether the ignition issue is isolated "
            "(one bad plug) or systemic (all plugs similar condition).",
            "Record per cylinder: gap measurement, electrode condition, insulator color/"
            "condition, porcelain condition, and overall assessment (good / worn / replace)"
        ),
        (
            "Inspect the ignition wiring and components:\n"
            "  - Pull each plug wire and check for:\n"
            "    • Burn marks or carbon tracks on the inside of the boot (arcing to ground)\n"
            "    • Cracked or hardened insulation (heat damage)\n"
            "    • Corrosion on the terminal inside the boot\n"
            "  - Measure plug wire resistance with a DMM: OEM spec typically <10,000 ohms "
            "per foot. Infinite = open wire; 0 ohms = short\n"
            "  - Inspect the ignition module/coil(s):\n"
            "    • Check for cracks, heat damage, or burn marks on the housing\n"
            "    • Verify connector pins are clean and tight\n"
            "    • Check the module mounting — loose modules vibrate and develop internal "
            "connection failures\n"
            "  - If the engine uses a magneto: check the air gap between rotor and stator "
            "(per OEM spec, typically 0.008\"–0.012\")",
            "Plug wires and ignition modules degrade from heat and vibration. High-resistance "
            "wires cause weak spark; arcing boots waste spark energy to ground.",
            "Record per wire: resistance (ohms), boot condition, insulation condition; "
            "and ignition module condition, mounting tightness, and air gap (if magneto)"
        ),
        (
            "Replace all spark plugs that are worn, fouled, or beyond the OEM interval:\n"
            "  - Replace as a complete set for consistent performance across all cylinders\n"
            "  - Verify new plug part number matches OEM specification\n"
            "  - Set gap on each new plug to OEM spec BEFORE installation (gaps may not be "
            "pre-set from the box)\n"
            "  - Apply a thin coat of anti-seize to the plug threads (keep anti-seize off "
            "the electrode and insulator)\n"
            "  - Thread plugs in BY HAND first to avoid cross-threading\n"
            "  - Torque to OEM spec (typically 25–30 ft-lbs for 14mm; 11–18 ft-lbs for "
            "10mm — consult engine manual)\n"
            "  - Push plug wire boots on firmly until they click/seat\n"
            "  - Replace any plug wires that failed the resistance test or show boot damage",
            "Replacing plugs as a set ensures uniform spark energy across all cylinders. "
            "Hand-starting threads prevents the common and expensive mistake of cross-threading "
            "a plug into an aluminum head.",
            "Record per cylinder: old plug removed, new plug part number installed, gap "
            "set (inches), torque applied, and any plug wires replaced (with part numbers)"
        ),
        (
            "Verify ignition timing (requires the engine to be running):\n"
            "  - Reconnect ignition power. Remove LOTO\n"
            "  - Start the engine and warm to operating temperature\n"
            "  - Connect a timing light to the #1 cylinder plug wire\n"
            "  - Point the timing light at the flywheel timing marks\n"
            "  - Read the timing: OEM spec is typically 8°–12° BTDC for natural gas "
            "(consult the engine manual for the exact spec)\n"
            "  - If timing is off by >2° from spec, adjust per OEM procedure:\n"
            "    • Electronic ignition: adjust via the panel/module software\n"
            "    • Mechanical ignition: rotate the distributor or adjust the magneto\n"
            "  - After adjustment, recheck timing and verify RPM stability\n"
            "  - Load the compressor and run for 30 minutes — listen for misfires and watch "
            "for fault codes",
            "Timing drift is a progressive condition that worsens engine performance and "
            "can cause detonation if advanced too far.",
            "Record: timing reading (degrees BTDC), OEM spec, adjustment made (if any), "
            "RPM at idle and loaded, and 30-minute test results"
        ),
        (
            "Complete the service report:\n"
            "  - Spark plugs: per-cylinder condition, gaps, and replacement status\n"
            "  - Plug wires: resistance values and replacement status\n"
            "  - Ignition module/coil condition\n"
            "  - Timing: reading before and after adjustment\n"
            "  - Test run results (RPM, stability, fault codes)\n"
            "  - Current run hours\n"
            "  - Recommended next plug change interval (based on hours at this change "
            "and observed wear rate)",
            "Ignition system records with per-cylinder data enable plug interval optimization "
            "and early detection of individual cylinder issues.",
            None
        ),
    ],
    "routine_service": [
        (
            "SAFETY: Shut down the unit. Perform LOTO. Wear safety glasses, hearing "
            "protection, gloves, and steel-toed boots. Review the site-specific safety "
            "requirements (H2S monitoring, fire permits, etc.) before starting work.",
            "Even routine PM work requires full LOTO. The familiarity of routine tasks "
            "is when complacency causes the most accidents.",
            "Record LOTO tag number and any site-specific safety requirements acknowledged"
        ),
        (
            "Verify which PM tasks are due by reviewing:\n"
            "  - The unit's PM schedule (from the maintenance management system or site PM book)\n"
            "  - Current run hours (from the panel or hour meter)\n"
            "  - Last PM date and run hours at last PM\n"
            "  - Determine which interval has been reached:\n"
            "    • 250-hour / monthly: fluid checks, visual inspection, belt/hose check\n"
            "    • 500-hour / quarterly: above + filter changes, oil sample\n"
            "    • 1,000-hour / semi-annual: above + oil change, valve lash check, cooling "
            "system service\n"
            "    • 4,000-hour / annual: above + spark plug change, comprehensive inspection, "
            "alignment check\n"
            "  (Intervals are typical — consult OEM manual for unit-specific schedule)",
            "Performing only the tasks that are actually due prevents over-maintenance "
            "(wasteful) and under-maintenance (risky). Run hours are the primary driver; "
            "calendar intervals are the backup.",
            "Record: current run hours, last PM date/hours, and which interval level applies "
            "for this visit"
        ),
        (
            "Check all fluid levels with the engine cool and oil drained back:\n"
            "  ENGINE OIL:\n"
            "  - Pull dipstick, wipe, reinsert, pull again. Level should be between ADD "
            "and FULL marks\n"
            "  - Note condition (color, clarity, smell) on a white paper towel\n"
            "  COMPRESSOR OIL (if separate system):\n"
            "  - Check sight glass or dipstick. Level should be in the operating range\n"
            "  COOLANT:\n"
            "  - Check expansion tank or radiator level (engine must be COOL)\n"
            "  - Check condition: freeze point, pH, color\n"
            "  If any fluid is low, top off with the correct specification fluid and note "
            "the volume added. Investigate the cause of any significant fluid loss.",
            "Fluid levels are the baseline health check. Low levels caught during PM prevent "
            "unscheduled shutdowns between PM visits.",
            "Record per fluid: level (low / normal / high), condition, volume added, and "
            "fluid specification used"
        ),
        (
            "Perform a visual inspection of the entire unit (360° walk-around):\n"
            "  - ENGINE: check for oil/coolant leaks, loose wiring, cracked hoses, belt "
            "condition and tension, exhaust leaks (black soot stains at manifold joints)\n"
            "  - COMPRESSOR: check for oil leaks at packing, crosshead, and crankcase; "
            "listen for unusual noises if briefly running; check cylinder cooling "
            "jackets/lines for leaks\n"
            "  - PIPING: check for gas leaks at flanges and connections (soap test if suspected)\n"
            "  - ELECTRICAL: check for damaged conduit, loose junction box covers, or animal "
            "nesting in the panel enclosure\n"
            "  - SKID/STRUCTURE: check mounting bolts, guard condition, and drainage\n"
            "  - SAFETY DEVICES: verify fire extinguisher is present and charged, emergency "
            "shutdown button is accessible and labeled",
            "The walk-around catches developing issues that are not yet causing alarms. "
            "Many significant problems are first detected visually during routine PM.",
            "Record all findings: OK items and any deficiencies (location, description, "
            "severity). Use a standardized PM checklist form if available"
        ),
        (
            "Perform filter service (if due per the PM interval):\n"
            "  - AIR FILTER: check restriction indicator, replace if in yellow/red zone or "
            "if visually loaded (see Filter Maintenance workflow for detailed procedure)\n"
            "  - OIL FILTER: replace with oil change (see Lubrication workflow for procedure)\n"
            "  - FUEL FILTER/STRAINER: clean screen or replace element; drain fuel scrubber "
            "condensate bowl\n"
            "Record all filter part numbers and run hours at replacement.",
            "Filter service at PM intervals prevents restriction-related shutdowns and "
            "maintains engine protection between PM visits.",
            "Record per filter: type, part number removed, part number installed, restriction "
            "reading (if applicable), and run hours"
        ),
        (
            "Perform oil change (if due per the PM interval):\n"
            "  Follow the detailed procedure in the Lubrication workflow:\n"
            "  - Drain old oil, record volume\n"
            "  - Replace oil filter\n"
            "  - Fill with correct oil type and volume\n"
            "  - Check level and verify on startup\n"
            "  Take an oil sample BEFORE draining if oil analysis is part of the PM program:\n"
            "  - Use a sample valve or extract from the dipstick tube with a vacuum pump\n"
            "  - Fill the sample bottle 3/4 full, label with unit ID, date, and run hours\n"
            "  - Send to the oil analysis lab per site procedures",
            "Oil analysis samples must be taken from running-temperature oil before draining "
            "to capture accurate wear metal and condition data.",
            "Record: oil sample taken (yes/no), sample bottle number, oil change performed "
            "(volume, type), and filter part number"
        ),
        (
            "Remove LOTO. Start the unit and run through a post-PM operational check:\n"
            "  - Verify oil pressure comes up within 10 seconds\n"
            "  - Monitor coolant temperature — should reach operating range within 15 minutes\n"
            "  - Check for any new leaks at filter, drain plug, or disturbed connections\n"
            "  - Listen for abnormal noise\n"
            "  - Load the compressor and verify key operating parameters:\n"
            "    • Suction and discharge pressures (within normal range)\n"
            "    • Exhaust temperatures per cylinder (within normal range, <75°F spread)\n"
            "    • Oil pressure at operating speed\n"
            "    • Coolant temperature stabilized\n"
            "  - Run under load for 15 minutes minimum before leaving the site",
            "Post-PM operational verification catches installation errors and ensures the "
            "unit is running correctly before the technician leaves.",
            "Record: oil pressure, coolant temp, suction/discharge pressures, exhaust temps, "
            "and any observations during the 15-minute test run"
        ),
        (
            "Complete the PM service report:\n"
            "  - PM interval level performed (250/500/1,000/4,000 hour)\n"
            "  - Current run hours\n"
            "  - All fluid levels and conditions (before and after service)\n"
            "  - All filters replaced (part numbers)\n"
            "  - Oil change performed (type, volume, sample taken)\n"
            "  - Visual inspection findings (OK items and deficiencies)\n"
            "  - Startup verification readings\n"
            "  - Any follow-up work identified during PM (list separately with priority)\n"
            "  - Next PM date/hours recommendation",
            "Complete PM records are essential for compliance, warranty, and insurance "
            "requirements. Follow-up items must be documented to ensure they are scheduled.",
            None
        ),
    ],
}

_DEFAULT_WORKFLOW: list[tuple[str, str, str | None]] = [
    (
        "SAFETY: Shut down the unit. Perform lockout/tag-out (LOTO). Wear safety glasses, "
        "gloves, and hearing protection. Confirm zero energy state before touching any "
        "components.",
        "LOTO is mandatory before any hands-on inspection of compressor equipment. "
        "Even a 'general inspection' requires the unit to be safely isolated.",
        "Record LOTO tag number and time applied"
    ),
    (
        "Review the last 90 days of service history for this compressor in the maintenance "
        "system. Note:\n"
        "  - Total service events and their categories\n"
        "  - Any recurring issues or patterns\n"
        "  - Last PM date and run hours\n"
        "  - Current run hours from the panel",
        "Historical context prevents duplicating previous work and identifies whether "
        "the current visit is related to a known ongoing issue.",
        "Record: number of recent events, any patterns noted, and current run hours"
    ),
    (
        "Perform a 360° walk-around inspection of the unit:\n"
        "  - Check for fluid leaks (oil, coolant, gas) — look for drips, puddles, stains\n"
        "  - Check for unusual noise (with hearing protection, listen from a safe distance "
        "before LOTO was applied, or note what operations reported)\n"
        "  - Check for visible damage, loose guards, or missing components\n"
        "  - Check fluid levels: engine oil dipstick, compressor oil sight glass, coolant "
        "expansion tank\n"
        "  - Check belt condition and tension (if equipped)\n"
        "  - Check air filter restriction indicator",
        "A systematic walk-around catches the most common issues before any specialized "
        "testing. Many significant problems are visible or audible.",
        "Record all findings: OK items and any anomalies (location, description, photo)"
    ),
    (
        "Inspect belts, hoses, and filters:\n"
        "  - BELTS: check for cracks, glazing, proper tension (1/2\" deflection per foot "
        "of span), and alignment\n"
        "  - HOSES: squeeze each hose — firm and flexible = good; spongy, hard, or "
        "cracked = schedule replacement. Check clamp tightness\n"
        "  - FILTERS: check air filter restriction, oil filter for leaks, fuel filter/"
        "strainer for condensation",
        "Belts, hoses, and filters are the most common wear items. Catching them during "
        "inspection prevents unscheduled failures.",
        "Record condition of each: belts (good / worn / cracked), hoses (good / soft / "
        "cracked), filters (clean / loaded / restricted)"
    ),
    (
        "Check for unusual noise, vibration, or leaks with the unit running (if safe "
        "to start and issue does not prevent running):\n"
        "  - Remove LOTO. Start the unit with all guards in place\n"
        "  - Listen at each bearing housing with a mechanic's stethoscope\n"
        "  - Feel for vibration at mounting points and bearing housings\n"
        "  - Check for leaks that only appear under pressure/temperature\n"
        "  - Record key operating parameters from the panel: pressures, temperatures, "
        "RPM, oil pressure",
        "Many conditions (leaks, vibration, noise) only manifest under operating "
        "conditions. Static inspection alone may miss the issue.",
        "Record: operating parameters, any abnormal sounds/vibration/leaks noted with "
        "location and description"
    ),
    (
        "Run the unit under normal operating load for 15 minutes and record key parameters:\n"
        "  - Suction pressure, discharge pressure (per stage)\n"
        "  - Coolant temperature\n"
        "  - Oil pressure (at idle and at operating speed)\n"
        "  - Engine RPM\n"
        "  - Any fault codes that appear during the run",
        "Operating data under load is the most revealing diagnostic information. "
        "Comparing to normal ranges identifies any developing issues.",
        "Record all parameters at 5 and 15 minutes: pressures, temperatures, RPM, "
        "oil pressure, and fault codes"
    ),
    (
        "Complete the service report:\n"
        "  - All inspection findings (OK items and deficiencies)\n"
        "  - Operating parameters recorded during test run\n"
        "  - Any repairs or adjustments made\n"
        "  - Parts used (with part numbers)\n"
        "  - Current run hours\n"
        "  - Recommendations for follow-up work (if any issues identified)\n"
        "  - If the issue was not resolved or identified: document what was checked and "
        "recommend the next diagnostic step (e.g., 'oil sample', 'vibration analysis', "
        "'senior technician review')",
        "Even negative findings are valuable. A complete report saves the next "
        "technician from repeating the same checks.",
        None
    ),
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
            instruction=(
                "RECURRENCE ALERT: This issue has been reported previously on this unit. "
                "Before starting the standard workflow, pull all prior service records for "
                "this issue category. Review:\n"
                "  - What was done last time (parts replaced, adjustments made)\n"
                "  - How long the repair lasted (run hours between events)\n"
                "  - Whether the same component or a different one failed\n"
                "  - Whether the operating conditions have changed since the last repair\n"
                "This visit must investigate ROOT CAUSE, not just repeat the previous repair."
            ),
            rationale=recurrence_description or (
                "Recurring issues require investigation of the underlying root cause. "
                "Repeating the same repair without understanding why it failed will result "
                "in another repeat failure."
            ),
            required_evidence=(
                "Record: previous repair details, run hours between failures, and assessment "
                "of whether the same or different root cause is suspected"
            ),
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
                "LOW CONFIDENCE ESCALATION: The system has low confidence in this diagnosis. "
                "After completing the steps above, if the issue is not clearly identified "
                "and resolved:\n"
                "  1. Contact the senior technician or area supervisor with your findings\n"
                "  2. Provide: all measurements taken, photos of components inspected, "
                "operating parameters, and your assessment\n"
                "  3. Do NOT leave the unit running if the original complaint is unresolved\n"
                "  4. Apply LOTO and leave the unit safe until the escalation is reviewed\n"
                "  5. Request engineering support if the senior technician also cannot "
                "determine root cause"
            ),
            rationale=(
                "System confidence is low — insufficient historical data to recommend a "
                "specific resolution with certainty. Escalation ensures the issue is not "
                "left unresolved or misdiagnosed."
            ),
            required_evidence=(
                "Record: escalation contact name, time, summary provided, and response/decision"
            ),
        ))
        step_num += 1
        notes.append("Low confidence — escalation step added to workflow")

    return GeneratedWorkflow(
        issue_category=issue_category,
        steps=steps,
        notes=notes,
    )
