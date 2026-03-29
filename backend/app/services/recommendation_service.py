"""Recommendation engine — orchestrator for all intelligence layers.

Ties together:
  Layer 1: analytics_service    — frequency analysis, recurrence detection
  Layer 2: rules_engine         — issue inference, action mapping
  Layer 3: similarity_service   — similar case retrieval
  Layer 4: workflow_service     — prescriptive workflow generation
  Layer 5: confidence_service   — multi-factor confidence scoring
  Layer 5b: explanation_service — evidence-based explanations

This module is the single entry point called by the API routes.
"""

from __future__ import annotations

from collections import Counter
from typing import Optional

from sqlalchemy.orm import Session

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


def generate_recommendation(
    event: ServiceEvent,
    db: Session,
    current_description: str | None = None,
    current_notes: str | None = None,
) -> Recommendation:
    """Generate a full recommendation for a service event.

    This is the main entry point for the intelligence engine.  It
    runs all 6 layers and persists the result.
    """
    compressor = db.query(Compressor).filter(Compressor.id == event.compressor_id).first()
    unit_id = compressor.unit_id if compressor else event.compressor_id

    # ── Layer 1: Descriptive analytics ────────────────────────────────
    recurrence_signals = detect_recurrence_signals(db, event.compressor_id)
    c30, c90 = get_recent_event_counts(db, event.compressor_id)
    avg_interval = compute_avg_days_between_events(db, event.compressor_id)
    resolution_rate = compute_resolution_rate(db, compressor_id=event.compressor_id)

    # ── Layer 2: Issue inference ──────────────────────────────────────
    notes_text = current_notes or event.technician_notes_raw
    desc_text = current_description or event.order_description

    action_type_raws = [a.action_type_raw for a in event.actions if a.action_type_raw]

    issue_result = infer_issue_category(
        notes=notes_text,
        description=desc_text,
        event_category=event.event_category,
        action_types=action_type_raws,
    )

    # Resolve issue_category_id from the database
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

    # ── Layer 3: Similar case retrieval ───────────────────────────────
    similar_cases: list[SimilarCaseResult] = find_similar_cases(event, db, limit=15)

    # Determine most frequent action from similar cases
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

    # Determine recommended action: prefer data-driven, fall back to rules
    recommended_action_label = top_action_label
    if not recommended_action_label or top_action_freq < 0.3:
        rule_action = get_primary_action_for_issue(issue_cat_name)
        if rule_action:
            recommended_action_label = rule_action.action_label

    # Infer suggested parts/checks from similar case actions
    suggested_parts = _infer_suggested_parts(similar_event_ids, db)

    # ── Layer 5: Confidence scoring ───────────────────────────────────
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

    # ── Layer 5b: Explanation generation ──────────────────────────────
    recurrence_dicts = [
        {
            "signal_type": rs.signal_type,
            "description": rs.description,
            "event_count": rs.event_count,
            "severity": rs.severity,
        }
        for rs in recurrence_signals
    ]

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

    # ── Layer 4: Workflow generation ──────────────────────────────────
    has_recurrence = len(recurrence_signals) > 0
    recurrence_desc = recurrence_signals[0].description if recurrence_signals else None

    workflow = generate_workflow(
        issue_category=issue_cat_name,
        has_recurrence=has_recurrence,
        recurrence_description=recurrence_desc,
        confidence_label=confidence_result.label,
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

    # Persist similar cases
    for sc in similar_cases[:10]:
        db.add(SimilarCase(
            recommendation_id=rec.id,
            service_event_id=sc.event.id,
            similarity_score=sc.similarity_score,
            match_reason="; ".join(sc.match_reasons),
        ))

    # Persist workflow steps
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
