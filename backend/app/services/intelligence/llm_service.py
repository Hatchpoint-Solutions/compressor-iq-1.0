"""LLM-powered compressor intelligence service.

Replaces the hardcoded rules engine, workflow templates, and explanation
templates with OpenAI-driven diagnosis, workflow generation, and
evidence-based explanations grounded in compressor domain expertise.

Falls back to the existing rule-based system on any failure or when
the OpenAI API key is not configured.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt: compressor maintenance expert persona
# ---------------------------------------------------------------------------

COMPRESSOR_EXPERT_SYSTEM_PROMPT = """\
You are CompressorIQ — a senior compressor maintenance engineer and \
reliability specialist with 20+ years of field experience diagnosing and \
resolving issues on natural gas compressor packages (reciprocating and \
screw-type, Caterpillar / Waukesha / Ariel / Ajax frames).

You are writing workflow steps that will be handed directly to a field \
service technician standing in front of the compressor with tools in hand. \
Every step must be EXECUTABLE — not a summary, not a concept, but a \
specific action with enough detail that the technician knows exactly \
what to do without guessing.

DOMAIN EXPERTISE
================
Failure modes you are deeply familiar with:
- Detonation / knock — root causes include spark plug degradation, \
  BTU/fuel-curve mis-calibration, ignition timing drift, carbon buildup, \
  and gas composition changes.
- Fluid leaks — oil, coolant, and gas leaks from fittings, gaskets, \
  packing, hose degradation, and thermal-cycle fatigue on connections.
- Pressure anomalies — suction/discharge instability from worn compressor \
  valves, blocked suction screens, failed relief valves, or pulsation \
  dampener issues.
- Cooling system — overheating from low coolant, thermostat failure, \
  blocked radiator fins, water pump cavitation, or internal head-gasket \
  leaks.
- Valve wear — compressor plate/ring valves and engine intake/exhaust \
  valves, lash drift, spring fatigue, seat erosion.
- Electrical / sensor — control panel faults, wiring harness damage \
  from vibration or rodents, sensor drift, grounding issues.
- Ignition — spark plug fouling, plug wire arcing, timing module \
  degradation.
- Lubrication — oil degradation from extended intervals, coolant \
  cross-contamination, bearing-metal in samples, low oil pressure.
- Unplanned shutdowns — interpreting fault codes, high-temperature trips, \
  low-oil-pressure trips, overspeed, and vibration trips.
- Seal / gasket / packing — identifying worn packing rings, rod-seal \
  leakage, crankcase pressure indicators.
- Vibration / noise — bearing wear, coupling misalignment, loose \
  mounting bolts, piston slap.

Maintenance standards you follow:
- API 11P (reciprocating compressors), API 618.
- OEM maintenance interval guidelines (run-hour and calendar based).
- OSHA and site-specific safety lock-out / tag-out requirements.

INTERPRETING TECHNICIAN NOTES
=============================
Field technicians use shorthand. Common patterns:
- "ck" / "chk" = check, "adj" = adjusted, "rpl" / "rplcd" = replaced
- "stg" = stage, "disch" = discharge, "suc" = suction
- "det" / "detnation" = detonation (often misspelled)
- Run hours may appear as "47231 hrs" or "RH: 47231"
- Actions are often embedded in free text, not structured

RULES FOR YOUR RESPONSES
=========================
1. Always ground your diagnosis in the DATA provided — technician notes, \
   event history, recurrence patterns, similar cases, and run hours. \
   Never invent data that was not supplied.
2. Distinguish SYMPTOMS from ROOT CAUSES. A leak is a symptom; a cracked \
   fitting from thermal fatigue at 45,000+ run hours is a root cause.
3. When evidence is limited, say so — lower your severity and recommend \
   broader triage steps.
4. When generating workflows, be SPECIFIC to this situation. Reference \
   actual data points (e.g., "Given the 3 leak events in 30 days at the \
   stage 2 discharge…"). Do NOT produce generic SOPs.
5. Always include safety-relevant steps (isolation, depressurization, \
   LOTO) before invasive work.
6. Adapt workflow depth to severity: critical issues get 8-12 detailed \
   steps; routine PM gets 5-7 focused steps.
7. For each workflow step, explain WHY it matters and WHAT evidence the \
   technician should capture.

WORKFLOW STEP DETAIL REQUIREMENTS
==================================
Each workflow step must be written as a FIELD-EXECUTABLE INSTRUCTION, \
not a generic concept. Every step must include AS MANY of the following \
as applicable:

a) SAFETY FIRST: If the step requires isolation, LOTO, PPE, or \
   depressurization — state it explicitly with the specific actions \
   (e.g., "Close the fuel gas supply valve, apply LOTO tag, verify \
   zero pressure with gauge").
b) SPECIFIC TOOLS: Name the tools and equipment needed (e.g., \
   "Using a 13/16 inch spark plug socket...", "Connect a 0-60 psi \
   test gauge to the fuel inlet...").
c) EXACT LOCATIONS: Tell the technician WHERE on the unit to go \
   (e.g., "At the Stage 2 discharge flange...", "On the engine \
   front cover behind the harmonic balancer...").
d) MEASURABLE CRITERIA: Provide specifications and acceptance ranges \
   (e.g., "Spark plug gap: 0.010-0.015 inch", "Oil pressure must be \
   >10 psi at idle and 40-60 psi at operating speed").
e) DECISION LOGIC: Include if/then branching when findings determine \
   the next action (e.g., "If gap exceeds spec by >0.005 inch, mark \
   plug for replacement. If gap is within spec, clean and reinstall.").
f) VERIFICATION METHOD: Describe how to confirm the step was done \
   correctly (e.g., "Apply soap solution and watch for bubbles for \
   2 minutes", "Run for 30 minutes under load and monitor for fault \
   code recurrence").
g) DOCUMENTATION: State exactly what to record and in what format \
   (e.g., "Record per cylinder: plug gap, electrode condition, and \
   replacement decision").

NEVER write steps like:
- "Check the spark plugs" (too vague — check HOW? measure WHAT? \
  compare to WHAT spec?)
- "Inspect for leaks" (WHERE? what kind of leak? how to trace it?)
- "Service the fuel system" (which components? in what order? \
  what measurements?)

ALWAYS write steps like:
- "Remove each spark plug using a 13/16 inch socket. Measure the \
  electrode gap with a wire feeler gauge. Compare to OEM spec \
  (0.010-0.015 inch). If gap exceeds spec by more than 0.005 inch \
  or electrode shows visible erosion, mark for replacement. Record \
  per cylinder: measured gap, electrode condition, and decision."
- "Perform a 360-degree walk-around starting at the engine front. \
  Look for active drips, puddles, spray patterns, and staining. \
  Identify fluid type by color and feel: dark amber = engine oil; \
  green/orange = coolant; clear = hydraulic. For gas leaks, apply \
  Snoop solution to suspected joints."
"""

# ---------------------------------------------------------------------------
# Data structures for LLM input/output
# ---------------------------------------------------------------------------

@dataclass
class LLMContext:
    """All evidence assembled for the LLM prompt."""
    unit_id: str
    compressor_type: str | None
    event_date: str | None
    event_category: str | None
    order_description: str | None
    technician_notes: str | None
    run_hours: float | None
    order_cost: float | None

    # Analytics (Layer 1)
    recent_event_count_30d: int = 0
    recent_event_count_90d: int = 0
    avg_days_between_events: float | None = None
    recurrence_signals: list[dict[str, Any]] = field(default_factory=list)
    action_frequencies: list[dict[str, Any]] = field(default_factory=list)

    # Similar cases (Layer 3)
    similar_cases: list[dict[str, Any]] = field(default_factory=list)

    # Confidence (Layer 5) — passed through for context
    confidence_score: float = 0.0
    confidence_label: str = "low"

    resolution_rate: float | None = None


@dataclass
class LLMDiagnosis:
    """Structured output from the LLM diagnosis."""
    issue_category: str
    issue_label: str
    severity: str
    root_cause_hypothesis: str
    matched_signals: list[str]
    confidence_note: str


@dataclass
class LLMWorkflowStep:
    """A single step from the LLM-generated workflow."""
    step_number: int
    instruction: str
    rationale: str
    required_evidence: str | None = None


@dataclass
class LLMRecommendation:
    """Complete LLM output: diagnosis + workflow + explanation."""
    diagnosis: LLMDiagnosis
    workflow_steps: list[LLMWorkflowStep]
    explanation: str
    recommended_action: str


# ---------------------------------------------------------------------------
# Context formatting — builds the user message for the LLM
# ---------------------------------------------------------------------------

def _build_user_prompt(ctx: LLMContext) -> str:
    """Assemble a structured user prompt from the evidence package."""
    sections: list[str] = []

    sections.append("== CURRENT SERVICE EVENT ==")
    sections.append(f"Unit: {ctx.unit_id}")
    if ctx.compressor_type:
        sections.append(f"Compressor type: {ctx.compressor_type}")
    if ctx.event_date:
        sections.append(f"Event date: {ctx.event_date}")
    if ctx.event_category:
        sections.append(f"Event category: {ctx.event_category}")
    if ctx.run_hours is not None:
        sections.append(f"Run hours at event: {ctx.run_hours:,.0f}")
    if ctx.order_cost is not None:
        sections.append(f"Order cost: ${ctx.order_cost:,.2f}")
    if ctx.order_description:
        sections.append(f"Order description: {ctx.order_description}")
    if ctx.technician_notes:
        sections.append(f"Technician notes:\n{ctx.technician_notes}")

    sections.append("\n== MACHINE HISTORY (ANALYTICS) ==")
    sections.append(f"Service events in last 30 days: {ctx.recent_event_count_30d}")
    sections.append(f"Service events in last 90 days: {ctx.recent_event_count_90d}")
    if ctx.avg_days_between_events is not None:
        sections.append(
            f"Average interval between events: {ctx.avg_days_between_events:.0f} days"
        )
    if ctx.resolution_rate is not None:
        sections.append(
            f"Historical resolution rate: {ctx.resolution_rate:.0%}"
        )

    if ctx.recurrence_signals:
        sections.append("\nRecurrence signals detected:")
        for sig in ctx.recurrence_signals:
            sections.append(
                f"  - [{sig.get('severity', 'medium').upper()}] "
                f"{sig.get('description', 'unknown signal')}"
            )

    if ctx.action_frequencies:
        sections.append("\nTop maintenance actions (historical):")
        for af in ctx.action_frequencies[:7]:
            sections.append(
                f"  - {af.get('action_type', '?')}: "
                f"{af.get('count', 0)} times "
                f"({af.get('percentage', 0):.0%})"
            )

    if ctx.similar_cases:
        sections.append(f"\n== SIMILAR HISTORICAL CASES ({len(ctx.similar_cases)}) ==")
        for i, sc in enumerate(ctx.similar_cases[:8], 1):
            parts = [f"Case {i} (similarity: {sc.get('similarity_score', 0):.0%})"]
            if sc.get("event_date"):
                parts.append(f"Date: {sc['event_date']}")
            if sc.get("event_category"):
                parts.append(f"Category: {sc['event_category']}")
            if sc.get("action_summary"):
                parts.append(f"Actions: {sc['action_summary']}")
            if sc.get("resolution_status"):
                parts.append(f"Resolution: {sc['resolution_status']}")
            if sc.get("match_reasons"):
                parts.append(f"Matched because: {sc['match_reasons']}")
            sections.append("  " + " | ".join(parts))

    sections.append(f"\n== CONFIDENCE CONTEXT ==")
    sections.append(
        f"System confidence: {ctx.confidence_label} ({ctx.confidence_score:.0%})"
    )

    sections.append(
        "\n== YOUR TASK ==\n"
        "Based on ALL evidence above, provide:\n"
        "1. DIAGNOSIS — the most likely issue, severity, and root cause hypothesis\n"
        "2. WORKFLOW — field-executable step-by-step maintenance procedure for THIS "
        "situation. Each step must be detailed enough that a technician with a wrench "
        "in hand can follow it without guessing. Include: specific tools needed, exact "
        "measurement specs, if/then decision points, safety requirements (LOTO, PPE), "
        "and what to record. NEVER write vague steps like 'check the system' — always "
        "say HOW to check, WHAT to measure, WHAT spec to compare against, and WHAT to "
        "do based on the finding.\n"
        "3. EXPLANATION — plain-language summary for the technician\n"
        "4. RECOMMENDED ACTION — single-sentence primary action\n\n"
        "CRITICAL: The first workflow step must ALWAYS be a safety/isolation step "
        "(LOTO, PPE, depressurization as applicable). The last step must be "
        "documentation/reporting. Steps in between must be specific executable "
        "actions, not summaries.\n\n"
        "Respond ONLY with valid JSON matching this exact schema:\n"
        "{\n"
        '  "diagnosis": {\n'
        '    "issue_category": "<snake_case category name>",\n'
        '    "issue_label": "<Human-Readable Label>",\n'
        '    "severity": "<low|medium|high|critical>",\n'
        '    "root_cause_hypothesis": "<2-3 sentences>",\n'
        '    "matched_signals": ["<signal1>", "<signal2>"],\n'
        '    "confidence_note": "<1 sentence on evidence quality>"\n'
        "  },\n"
        '  "workflow_steps": [\n'
        "    {\n"
        '      "step_number": 1,\n'
        '      "instruction": "<detailed executable action — include tools, specs, '
        'locations, decision points, and safety requirements as applicable. '
        'Minimum 2-3 sentences per step. Use sub-bullets for multi-part steps.>",\n'
        '      "rationale": "<why this specific step matters for THIS case, '
        'referencing the evidence provided above>",\n'
        '      "required_evidence": "<exactly what to measure and record, '
        'with units and format>" or null\n'
        "    }\n"
        "  ],\n"
        '  "explanation": "<3-5 sentence evidence-grounded explanation>",\n'
        '  "recommended_action": "<single sentence primary action>"\n'
        "}"
    )

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# LLM call and response parsing
# ---------------------------------------------------------------------------

def _get_client() -> OpenAI:
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _parse_llm_response(raw: str) -> LLMRecommendation:
    """Parse the JSON response from the LLM into typed dataclasses."""
    data = json.loads(raw)

    diag = data["diagnosis"]
    diagnosis = LLMDiagnosis(
        issue_category=diag["issue_category"],
        issue_label=diag["issue_label"],
        severity=diag["severity"],
        root_cause_hypothesis=diag["root_cause_hypothesis"],
        matched_signals=diag.get("matched_signals", []),
        confidence_note=diag.get("confidence_note", ""),
    )

    steps = []
    for s in data.get("workflow_steps", []):
        steps.append(LLMWorkflowStep(
            step_number=s["step_number"],
            instruction=s["instruction"],
            rationale=s["rationale"],
            required_evidence=s.get("required_evidence"),
        ))

    return LLMRecommendation(
        diagnosis=diagnosis,
        workflow_steps=steps,
        explanation=data.get("explanation", ""),
        recommended_action=data.get("recommended_action", ""),
    )


def generate_llm_recommendation(ctx: LLMContext) -> LLMRecommendation:
    """Call OpenAI and return a structured recommendation.

    Raises on any failure — the caller is responsible for falling back
    to the rule-based engine.
    """
    client = _get_client()
    user_prompt = _build_user_prompt(ctx)

    logger.info("Calling OpenAI %s for unit %s", settings.OPENAI_MODEL, ctx.unit_id)

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": COMPRESSOR_EXPERT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_content = response.choices[0].message.content
    if not raw_content:
        raise ValueError("Empty response from OpenAI")

    logger.info(
        "OpenAI response received — %d tokens used",
        response.usage.total_tokens if response.usage else 0,
    )

    return _parse_llm_response(raw_content)
