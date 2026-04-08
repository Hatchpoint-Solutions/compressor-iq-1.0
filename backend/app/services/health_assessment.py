"""Proactive health assessment service.

Gathers the latest compressor data—maintenance history, recurrence
patterns, run hours—and combines internal analytics with an optional
OpenAI call to produce a structured health report for the operator.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.event_models import ServiceEvent
from app.models.master_models import Compressor
from app.schemas.recommendation_schemas import (
    HealthAlertItem,
    HealthAssessmentResponse,
)
from app.services.intelligence.analytics_service import (
    compute_avg_days_between_events,
    detect_recurrence_signals,
    get_action_frequencies_for_machine,
    get_recent_event_counts,
)

logger = logging.getLogger(__name__)


def generate_health_assessment(
    compressor: Compressor,
    db: Session,
) -> HealthAssessmentResponse:
    """Build a health assessment combining internal data + optional LLM."""

    c30, c90 = get_recent_event_counts(db, compressor.id)
    avg_interval = compute_avg_days_between_events(db, compressor.id)
    recurrence_signals = detect_recurrence_signals(db, compressor.id)
    action_freqs = get_action_frequencies_for_machine(db, compressor.id, limit=7)

    total_events = (
        db.query(func.count(ServiceEvent.id))
        .filter(ServiceEvent.compressor_id == compressor.id)
        .scalar() or 0
    )

    last_date = (
        db.query(func.max(ServiceEvent.event_date))
        .filter(ServiceEvent.compressor_id == compressor.id)
        .scalar()
    )

    thirty_days_ago = date.today() - timedelta(days=30)
    recent_events = (
        db.query(ServiceEvent)
        .filter(
            ServiceEvent.compressor_id == compressor.id,
            ServiceEvent.event_date >= thirty_days_ago,
        )
        .order_by(ServiceEvent.event_date.desc())
        .limit(20)
        .all()
    )

    top_categories = (
        db.query(ServiceEvent.event_category, func.count(ServiceEvent.id).label("cnt"))
        .filter(
            ServiceEvent.compressor_id == compressor.id,
            ServiceEvent.event_category.isnot(None),
        )
        .group_by(ServiceEvent.event_category)
        .order_by(func.count(ServiceEvent.id).desc())
        .limit(5)
        .all()
    )
    top_issues = [row[0] for row in top_categories]

    alerts: list[HealthAlertItem] = []
    health_score = 100.0

    alerts, health_score = _generate_rule_based_alerts(
        compressor, c30, c90, avg_interval, recurrence_signals,
        action_freqs, recent_events, total_events, health_score,
    )

    overall_health = _score_to_label(health_score)

    ai_summary = None
    ai_powered = False
    if settings.llm_enabled:
        ai_result = _try_llm_assessment(
            compressor, recent_events, recurrence_signals,
            action_freqs, c30, c90, avg_interval, total_events,
            top_issues, alerts,
        )
        if ai_result is not None:
            ai_powered = True
            ai_summary = ai_result.get("summary")
            for alert_data in ai_result.get("alerts", []):
                alerts.append(HealthAlertItem(
                    severity=alert_data.get("severity", "medium"),
                    title=alert_data.get("title", "AI-detected concern"),
                    description=alert_data.get("description", ""),
                    recommended_action=alert_data.get("recommended_action", "Investigate further"),
                ))
            if ai_result.get("health_score") is not None:
                health_score = float(ai_result["health_score"])
                overall_health = _score_to_label(health_score)

    summary = ai_summary or _build_rule_summary(
        compressor, overall_health, c30, c90, total_events, recurrence_signals,
    )

    from app.services.work_order_service import create_work_orders_from_health_alerts

    work_orders_created = create_work_orders_from_health_alerts(db, compressor, alerts)

    return HealthAssessmentResponse(
        compressor_id=compressor.id,
        unit_id=compressor.unit_id,
        overall_health=overall_health,
        health_score=round(health_score, 1),
        summary=summary,
        alerts=alerts,
        recent_event_count_30d=c30,
        recent_event_count_90d=c90,
        total_events=total_events,
        current_run_hours=compressor.current_run_hours,
        last_service_date=last_date,
        top_issues=top_issues,
        ai_powered=ai_powered,
        assessed_at=datetime.utcnow(),
        work_orders_created=work_orders_created,
    )


def _score_to_label(score: float) -> str:
    if score >= 80:
        return "good"
    if score >= 60:
        return "fair"
    if score >= 40:
        return "warning"
    return "critical"


def _generate_rule_based_alerts(
    compressor: Compressor,
    c30: int, c90: int,
    avg_interval: float | None,
    recurrence_signals: list,
    action_freqs: list,
    recent_events: list[ServiceEvent],
    total_events: int,
    health_score: float,
) -> tuple[list[HealthAlertItem], float]:
    alerts: list[HealthAlertItem] = []

    corrective_recent = sum(
        1 for e in recent_events if e.event_category == "corrective"
    )
    if corrective_recent >= 3:
        alerts.append(HealthAlertItem(
            severity="high",
            title="High corrective event frequency",
            description=f"{corrective_recent} corrective events in the last 30 days indicates a persistent or worsening issue.",
            recommended_action="Schedule comprehensive inspection to identify root cause of recurring failures.",
        ))
        health_score -= 25
    elif corrective_recent >= 1:
        alerts.append(HealthAlertItem(
            severity="medium",
            title="Recent corrective maintenance",
            description=f"{corrective_recent} corrective event(s) in the last 30 days.",
            recommended_action="Monitor closely and review technician notes for emerging patterns.",
        ))
        health_score -= 10

    for sig in recurrence_signals:
        sev = sig.severity if hasattr(sig, "severity") else "medium"
        desc = sig.description if hasattr(sig, "description") else str(sig)
        alerts.append(HealthAlertItem(
            severity=sev,
            title="Recurring issue detected",
            description=desc,
            recommended_action="Investigate root cause to break the recurrence cycle.",
        ))
        health_score -= 15 if sev == "high" else 10

    if avg_interval is not None and avg_interval < 14:
        alerts.append(HealthAlertItem(
            severity="high",
            title="Very frequent service intervals",
            description=f"Average interval between events is only {avg_interval:.0f} days, well below typical thresholds.",
            recommended_action="Consider a major overhaul or component replacement to extend service life.",
        ))
        health_score -= 15

    if compressor.current_run_hours and compressor.current_run_hours > 40000:
        alerts.append(HealthAlertItem(
            severity="medium",
            title="High accumulated run hours",
            description=f"Unit has {compressor.current_run_hours:,.0f} run hours. Critical wear components may need proactive replacement.",
            recommended_action="Review OEM guidelines for component replacement intervals at this run-hour milestone.",
        ))
        health_score -= 5

    health_score = max(0, min(100, health_score))
    return alerts, health_score


def _build_rule_summary(
    compressor: Compressor,
    overall_health: str,
    c30: int, c90: int,
    total_events: int,
    recurrence_signals: list,
) -> str:
    parts = [f"Unit {compressor.unit_id} is rated as '{overall_health}'."]
    if compressor.current_run_hours:
        parts.append(f"It has accumulated {compressor.current_run_hours:,.0f} run hours.")
    parts.append(f"There are {total_events} total service events on record, with {c30} in the last 30 days and {c90} in the last 90 days.")
    if recurrence_signals:
        parts.append(f"{len(recurrence_signals)} recurrence pattern(s) have been detected, indicating potential systemic issues.")
    if overall_health in ("warning", "critical"):
        parts.append("Immediate attention is recommended to prevent unplanned downtime.")
    return " ".join(parts)


_ASSESSMENT_SYSTEM_PROMPT = """\
You are CompressorIQ Health Assessor — an expert compressor reliability engineer.
Given maintenance data for a compressor unit, produce a JSON health assessment.

Respond ONLY with valid JSON matching this schema:
{
  "summary": "<3-5 sentence plain-language health summary for an operator>",
  "health_score": <0-100 numeric score>,
  "alerts": [
    {
      "severity": "<low|medium|high|critical>",
      "title": "<short alert title>",
      "description": "<1-2 sentence explanation>",
      "recommended_action": "<specific action for the operator>"
    }
  ]
}

RULES:
1. Ground every alert in the DATA provided — never invent problems.
2. Distinguish symptoms from root causes.
3. Score generously (80+) when data looks healthy; penalize for recurrence patterns, high corrective frequency, or short service intervals.
4. If data is sparse, say so and recommend baseline inspection.
5. Be specific — reference actual run hours, event counts, and patterns from the data.
"""


def _try_llm_assessment(
    compressor: Compressor,
    recent_events: list[ServiceEvent],
    recurrence_signals: list,
    action_freqs: list,
    c30: int, c90: int,
    avg_interval: float | None,
    total_events: int,
    top_issues: list[str],
    existing_alerts: list[HealthAlertItem],
) -> dict | None:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        sections = []
        sections.append(f"== COMPRESSOR: {compressor.unit_id} ==")
        if compressor.compressor_type:
            sections.append(f"Type: {compressor.compressor_type}")
        if compressor.current_run_hours:
            sections.append(f"Current run hours: {compressor.current_run_hours:,.0f}")
        sections.append(f"Status: {compressor.status}")

        sections.append(f"\n== MAINTENANCE STATISTICS ==")
        sections.append(f"Total events on record: {total_events}")
        sections.append(f"Events in last 30 days: {c30}")
        sections.append(f"Events in last 90 days: {c90}")
        if avg_interval is not None:
            sections.append(f"Average days between events: {avg_interval:.0f}")
        if top_issues:
            sections.append(f"Top issue categories: {', '.join(top_issues)}")

        if recent_events:
            sections.append(f"\n== RECENT EVENTS (last 30 days) ==")
            for ev in recent_events[:10]:
                parts = []
                if ev.event_date:
                    parts.append(f"Date: {ev.event_date}")
                if ev.event_category:
                    parts.append(f"Category: {ev.event_category}")
                if ev.order_description:
                    parts.append(f"Description: {ev.order_description[:200]}")
                if ev.run_hours_at_event:
                    parts.append(f"Run hours: {ev.run_hours_at_event:,.0f}")
                if ev.technician_notes_raw:
                    parts.append(f"Notes: {ev.technician_notes_raw[:300]}")
                sections.append("  - " + " | ".join(parts))

        if recurrence_signals:
            sections.append(f"\n== RECURRENCE PATTERNS ==")
            for sig in recurrence_signals:
                desc = sig.description if hasattr(sig, "description") else str(sig)
                sev = sig.severity if hasattr(sig, "severity") else "medium"
                sections.append(f"  - [{sev.upper()}] {desc}")

        if action_freqs:
            sections.append(f"\n== TOP MAINTENANCE ACTIONS ==")
            for af in action_freqs[:7]:
                sections.append(f"  - {af.action_type}: {af.count} times ({af.percentage:.0%})")

        if existing_alerts:
            sections.append(f"\n== RULE-BASED ALERTS ALREADY DETECTED ==")
            for a in existing_alerts:
                sections.append(f"  - [{a.severity.upper()}] {a.title}: {a.description}")

        sections.append(
            "\n== YOUR TASK ==\n"
            "Produce a health assessment JSON. Include any ADDITIONAL alerts "
            "the rule engine may have missed, and provide a comprehensive summary."
        )

        user_prompt = "\n".join(sections)

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _ASSESSMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw = response.choices[0].message.content
        if not raw:
            return None
        return json.loads(raw)

    except Exception:
        logger.exception("LLM health assessment failed — using rule-based results only")
        return None
