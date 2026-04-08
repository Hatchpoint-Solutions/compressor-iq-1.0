"""Recommendation engine — orchestrator for all intelligence layers.

Ties together:
  Layer 1: analytics_service    — frequency analysis, recurrence detection
  Layer 2: rules_engine         — issue inference, action mapping (fallback)
  Layer 3: similarity_service   — similar case retrieval
  Layer 4: workflow_service     — prescriptive workflow generation (fallback)
  Layer 5: confidence_service   — multi-factor confidence scoring
  Layer 5b: explanation_service — evidence-based explanations (fallback)
  LLM:     llm_service          — OpenAI-powered diagnosis, workflows, explanations

When OPENAI_API_KEY is configured, Layers 2/4/5b are replaced by the LLM
service.  If the LLM call fails for any reason, we fall back transparently
to the rule-based engine.

This module is the single entry point called by the API routes.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analytics_models import Recommendation, SimilarCase, WorkflowStep
from app.models.event_models import ServiceEvent, ServiceEventAction
from app.models.master_models import Compressor, IssueCategory

from app.services.intelligence.analytics_service import (
    compute_avg_days_between_events,
    compute_resolution_rate,
    detect_recurrence_signals,
    get_action_frequencies_for_machine,
    get_recent_event_counts,
)
from app.services.intelligence.confidence_service import (
    compute_confidence,
    compute_data_completeness,
)
from app.services.intelligence.explanation_service import (
    EvidencePackage,
    build_evidence_summary_dict,
    generate_explanation,
    generate_fallback_note,
)
from app.services.intelligence.keyword_normalization import (
    get_action_label,
    normalize_action,
)
from app.services.intelligence.rules_engine import (
    get_primary_action_for_issue,
    infer_issue_category,
)
from app.services.intelligence.similarity_service import (
    SimilarCaseResult,
    find_similar_cases,
)
from app.services.intelligence.workflow_service import generate_workflow

logger = logging.getLogger(__name__)


def generate_recommendation(
    event: ServiceEvent,
    db: Session,
    current_description: str | None = None,
    current_notes: str | None = None,
) -> Recommendation:
    """Generate a full recommendation for a service event.

    This is the main entry point for the intelligence engine.  It runs
    the data layers (analytics, similarity, confidence), then delegates
    diagnosis/workflow/explanation to the LLM when available or falls
    back to the rule-based engine.
    """
    compressor = db.query(Compressor).filter(Compressor.id == event.compressor_id).first()
    unit_id = compressor.unit_id if compressor else event.compressor_id

    notes_text = current_notes or event.technician_notes_raw
    desc_text = current_description or event.order_description

    # ── Layer 1: Descriptive analytics (always runs) ──────────────────
    recurrence_signals = detect_recurrence_signals(db, event.compressor_id)
    c30, c90 = get_recent_event_counts(db, event.compressor_id)
    avg_interval = compute_avg_days_between_events(db, event.compressor_id)
    resolution_rate = compute_resolution_rate(db, compressor_id=event.compressor_id)
    action_freqs = get_action_frequencies_for_machine(db, event.compressor_id, limit=7)

    # ── Layer 3: Similar case retrieval (always runs) ─────────────────
    similar_cases: list[SimilarCaseResult] = find_similar_cases(event, db, limit=15)

    similar_event_ids = [sc.event.id for sc in similar_cases]
    frequent_actions = _determine_frequent_actions(similar_event_ids, db)

    top_action_code = None
    top_action_label = None
    top_action_freq = 0.0
    total_actions_in_similar = sum(c for _, c in frequent_actions) if frequent_actions else 0

    if frequent_actions:
        raw_action, count = frequent_actions[0]
        top_action_freq = count / total_actions_in_similar if total_actions_in_similar else 0
        normalized = normalize_action(raw_action)
        top_action_code = normalized.code if normalized.code != "unknown" else raw_action
        top_action_label = normalized.label if normalized.code != "unknown" else raw_action

    suggested_parts = _infer_suggested_parts(similar_event_ids, db)

    # ── Layer 2: Issue inference (rule-based — needed for confidence) ─
    action_type_raws = [a.action_type_raw for a in event.actions if a.action_type_raw]
    issue_result = infer_issue_category(
        notes=notes_text,
        description=desc_text,
        event_category=event.event_category,
        action_types=action_type_raws,
    )

    issue_category_id = event.issue_category_id
    issue_cat_name = issue_result.category_name
    issue_cat_label = issue_result.category_label

    if not issue_category_id and issue_cat_name != "unknown":
        cat_row = db.query(IssueCategory).filter(IssueCategory.name == issue_cat_name).first()
        if cat_row:
            issue_category_id = cat_row.id
    elif issue_category_id:
        cat_row = db.query(IssueCategory).filter(IssueCategory.id == issue_category_id).first()
        if cat_row:
            issue_cat_name = cat_row.name
            issue_cat_label = cat_row.name.replace("_", " ").title()

    # ── Layer 5: Confidence scoring (always runs — auditable math) ────
    data_completeness = compute_data_completeness(
        has_notes=bool(notes_text),
        has_description=bool(desc_text),
        has_event_date=event.event_date is not None,
        has_run_hours=event.run_hours_at_event is not None,
        has_event_category=bool(event.event_category),
        has_actions=len(event.actions) > 0,
    )

    confidence_result = compute_confidence(
        similar_case_count=len(similar_cases),
        top_action_frequency=top_action_freq,
        has_issue_category=issue_cat_name != "unknown",
        issue_inference_confidence=issue_result.confidence,
        recurrence_signal_count=len(recurrence_signals),
        data_completeness_score=data_completeness,
        resolution_rate=resolution_rate,
    )

    recurrence_dicts = [
        {
            "signal_type": rs.signal_type,
            "description": rs.description,
            "event_count": rs.event_count,
            "severity": rs.severity,
        }
        for rs in recurrence_signals
    ]

    evidence_summary = build_evidence_summary_dict(
        similar_case_count=len(similar_cases),
        top_action=top_action_code,
        top_action_label=top_action_label,
        top_action_frequency=top_action_freq,
        resolution_rate=resolution_rate,
        recent_event_count_30d=c30,
        recent_event_count_90d=c90,
        recurrence_signal_count=len(recurrence_signals),
        avg_days_between_events=avg_interval,
    )

    # ── LLM path (or fallback to rule-based) ──────────────────────────
    llm_result = None
    if settings.llm_enabled:
        llm_result = _try_llm_recommendation(
            event=event,
            unit_id=unit_id,
            compressor=compressor,
            notes_text=notes_text,
            desc_text=desc_text,
            recurrence_dicts=recurrence_dicts,
            action_freqs=action_freqs,
            similar_cases=similar_cases,
            confidence_result=confidence_result,
            c30=c30,
            c90=c90,
            avg_interval=avg_interval,
            resolution_rate=resolution_rate,
        )

    if llm_result is not None:
        # LLM succeeded — use its diagnosis, workflow, and explanation
        explanation_text = llm_result.explanation
        recommended_action_label = llm_result.recommended_action
        fallback_note = None

        # Override issue category if LLM provided one
        if llm_result.diagnosis.issue_category:
            issue_cat_name = llm_result.diagnosis.issue_category
            issue_cat_label = llm_result.diagnosis.issue_label or issue_cat_label
            cat_row = db.query(IssueCategory).filter(
                IssueCategory.name == issue_cat_name,
            ).first()
            if cat_row:
                issue_category_id = cat_row.id

        workflow_steps_data = [
            (s.step_number, s.instruction, s.rationale, s.required_evidence)
            for s in llm_result.workflow_steps
        ]
    else:
        # Fallback: use the existing rule-based engine
        explanation_text, recommended_action_label, fallback_note, workflow_steps_data = (
            _rule_based_recommendation(
                issue_cat_name=issue_cat_name,
                issue_cat_label=issue_cat_label,
                unit_id=unit_id,
                top_action_code=top_action_code,
                top_action_label=top_action_label,
                top_action_freq=top_action_freq,
                resolution_rate=resolution_rate,
                recurrence_dicts=recurrence_dicts,
                recurrence_signals=recurrence_signals,
                c30=c30,
                c90=c90,
                avg_interval=avg_interval,
                similar_cases=similar_cases,
                issue_result=issue_result,
                confidence_result=confidence_result,
                compressor=compressor,
            )
        )

    # ── Persist ───────────────────────────────────────────────────────
    rec = Recommendation(
        service_event_id=event.id,
        compressor_id=event.compressor_id,
        issue_category_id=issue_category_id,
        likely_issue_category=issue_cat_name if issue_cat_name != "unknown" else None,
        recommended_action=recommended_action_label,
        confidence_score=confidence_result.score,
        confidence_label=confidence_result.label,
        reasoning=explanation_text,
        evidence_summary=evidence_summary,
        recurrence_signals=recurrence_dicts if recurrence_dicts else None,
        suggested_parts_or_checks=suggested_parts if suggested_parts else None,
        similar_case_count=len(similar_cases),
        most_frequent_action=top_action_label,
        resolution_rate=resolution_rate,
        fallback_note=fallback_note,
        status="pending",
    )
    db.add(rec)
    db.flush()

    for sc in similar_cases[:10]:
        db.add(SimilarCase(
            recommendation_id=rec.id,
            service_event_id=sc.event.id,
            similarity_score=sc.similarity_score,
            match_reason="; ".join(sc.match_reasons),
        ))

    for step_num, instruction, rationale, evidence in workflow_steps_data:
        db.add(WorkflowStep(
            recommendation_id=rec.id,
            step_number=step_num,
            instruction=instruction,
            rationale=rationale,
            required_evidence=evidence,
        ))

    db.commit()
    return rec


# ── LLM integration ──────────────────────────────────────────────────────

def _try_llm_recommendation(
    event: ServiceEvent,
    unit_id: str,
    compressor: Compressor | None,
    notes_text: str | None,
    desc_text: str | None,
    recurrence_dicts: list[dict],
    action_freqs: list,
    similar_cases: list[SimilarCaseResult],
    confidence_result,
    c30: int,
    c90: int,
    avg_interval: float | None,
    resolution_rate: float | None,
):
    """Attempt to generate a recommendation via the LLM.

    Returns an LLMRecommendation on success, or None on any failure.
    """
    try:
        from app.services.intelligence.llm_service import (
            LLMContext,
            generate_llm_recommendation,
        )

        similar_case_dicts = [
            {
                "similarity_score": sc.similarity_score,
                "event_date": str(sc.event_date) if sc.event_date else None,
                "event_category": sc.event_category,
                "action_summary": sc.action_summary,
                "resolution_status": sc.resolution_status,
                "match_reasons": "; ".join(sc.match_reasons),
            }
            for sc in similar_cases[:8]
        ]

        action_freq_dicts = [
            {
                "action_type": af.action_type,
                "count": af.count,
                "percentage": af.percentage,
            }
            for af in action_freqs[:7]
        ]

        ctx = LLMContext(
            unit_id=unit_id,
            compressor_type=compressor.compressor_type if compressor else None,
            event_date=str(event.event_date) if event.event_date else None,
            event_category=event.event_category,
            order_description=desc_text,
            technician_notes=notes_text,
            run_hours=event.run_hours_at_event,
            order_cost=event.order_cost,
            recent_event_count_30d=c30,
            recent_event_count_90d=c90,
            avg_days_between_events=avg_interval,
            recurrence_signals=recurrence_dicts,
            action_frequencies=action_freq_dicts,
            similar_cases=similar_case_dicts,
            confidence_score=confidence_result.score,
            confidence_label=confidence_result.label,
            resolution_rate=resolution_rate,
        )

        return generate_llm_recommendation(ctx)

    except Exception:
        logger.exception("LLM recommendation failed — falling back to rule-based engine")
        return None


# ── Rule-based fallback (original logic, extracted) ───────────────────────

def _rule_based_recommendation(
    issue_cat_name: str,
    issue_cat_label: str,
    unit_id: str,
    top_action_code: str | None,
    top_action_label: str | None,
    top_action_freq: float,
    resolution_rate: float | None,
    recurrence_dicts: list[dict],
    recurrence_signals: list,
    c30: int,
    c90: int,
    avg_interval: float | None,
    similar_cases: list[SimilarCaseResult],
    issue_result,
    confidence_result,
    compressor: Compressor | None,
) -> tuple[str, str | None, str | None, list[tuple[int, str, str, str | None]]]:
    """Run the original rule-based layers 2/4/5b and return their outputs.

    Returns (explanation_text, recommended_action, fallback_note, workflow_steps).
    workflow_steps is a list of (step_number, instruction, rationale, evidence).
    """
    recommended_action_label = top_action_label
    if not recommended_action_label or top_action_freq < 0.3:
        rule_action = get_primary_action_for_issue(issue_cat_name)
        if rule_action:
            recommended_action_label = rule_action.action_label

    evidence_pkg = EvidencePackage(
        machine_unit_id=unit_id,
        similar_case_count=len(similar_cases),
        top_action=top_action_code,
        top_action_label=top_action_label,
        top_action_frequency=top_action_freq,
        resolution_rate=resolution_rate,
        recurrence_signals=recurrence_dicts,
        recent_event_count_30d=c30,
        recent_event_count_90d=c90,
        issue_category_name=issue_cat_name,
        issue_category_label=issue_cat_label,
        issue_inference_confidence=issue_result.confidence,
        matched_keywords=issue_result.matched_keywords,
        confidence_label=confidence_result.label,
        confidence_score=confidence_result.score,
        avg_days_between_events=avg_interval,
        compressor_type=compressor.compressor_type if compressor else None,
    )

    explanation_text = generate_explanation(evidence_pkg)
    fallback_note = generate_fallback_note(
        confidence_label=confidence_result.label,
        similar_case_count=len(similar_cases),
        has_issue_category=issue_cat_name != "unknown",
    )

    has_recurrence = len(recurrence_signals) > 0
    recurrence_desc = recurrence_signals[0].description if recurrence_signals else None

    workflow = generate_workflow(
        issue_category=issue_cat_name,
        has_recurrence=has_recurrence,
        recurrence_description=recurrence_desc,
        confidence_label=confidence_result.label,
    )

    workflow_steps_data = [
        (step.step_number, step.instruction, step.rationale, step.required_evidence)
        for step in workflow.steps
    ]

    return explanation_text, recommended_action_label, fallback_note, workflow_steps_data


def generate_recommendation_for_machine(
    compressor_id: str,
    db: Session,
    description: str | None = None,
    notes: str | None = None,
) -> Recommendation:
    """Generate a recommendation for a machine without a specific event.

    Finds the most recent event for the machine and uses it as the
    reference, augmented by any additional description/notes provided.
    """
    latest_event = (
        db.query(ServiceEvent)
        .filter(ServiceEvent.compressor_id == compressor_id)
        .order_by(ServiceEvent.event_date.desc().nullslast())
        .first()
    )

    if not latest_event:
        # No history at all — create a minimal recommendation
        return _generate_no_history_recommendation(compressor_id, db, description, notes)

    return generate_recommendation(latest_event, db, description, notes)


def _generate_no_history_recommendation(
    compressor_id: str,
    db: Session,
    description: str | None,
    notes: str | None,
) -> Recommendation:
    """Handle the case where a machine has no service history at all."""
    issue_result = infer_issue_category(notes=notes, description=description)

    workflow = generate_workflow(
        issue_category=issue_result.category_name,
        confidence_label="low",
    )

    rec = Recommendation(
        compressor_id=compressor_id,
        likely_issue_category=issue_result.category_name if issue_result.category_name != "unknown" else None,
        recommended_action="Perform general inspection",
        confidence_score=0.10,
        confidence_label="low",
        reasoning=(
            f"No service history available for this machine. "
            f"Recommendation is based on general rules."
            + (f" Possible issue: {issue_result.category_label}." if issue_result.category_name != "unknown" else "")
        ),
        evidence_summary={"similar_case_count": 0, "note": "No historical data available"},
        similar_case_count=0,
        fallback_note=(
            "No historical service data exists for this machine. "
            "Recommend thorough manual inspection and documentation of findings."
        ),
        status="pending",
    )
    db.add(rec)
    db.flush()

    for step in workflow.steps:
        db.add(WorkflowStep(
            recommendation_id=rec.id,
            step_number=step.step_number,
            instruction=step.instruction,
            rationale=step.rationale,
            required_evidence=step.required_evidence,
        ))

    db.commit()
    return rec


# ── Internal helpers ──────────────────────────────────────────────────────

def _determine_frequent_actions(
    event_ids: list[str],
    db: Session,
) -> list[tuple[str, int]]:
    """Find the most common action types from a set of events."""
    if not event_ids:
        return []

    actions = (
        db.query(ServiceEventAction)
        .filter(ServiceEventAction.service_event_id.in_(event_ids))
        .all()
    )

    counter: Counter[str] = Counter()
    for a in actions:
        if a.action_type_raw:
            counter[a.action_type_raw] += 1

    return counter.most_common(5)


def _infer_suggested_parts(
    event_ids: list[str],
    db: Session,
) -> list[str]:
    """Infer commonly mentioned components from similar case actions."""
    if not event_ids:
        return []

    actions = (
        db.query(ServiceEventAction)
        .filter(ServiceEventAction.service_event_id.in_(event_ids))
        .all()
    )

    component_counter: Counter[str] = Counter()
    for a in actions:
        if a.component:
            component_counter[a.component] += 1

    return [comp for comp, _ in component_counter.most_common(5)]
