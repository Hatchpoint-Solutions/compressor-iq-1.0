"""Descriptive analytics and recurrence detection.

Layer 1 of the intelligence stack: data-driven pattern extraction.

Provides:
- Action frequency analysis per machine and machine family
- Issue category recurrence detection
- Repeat-event interval calculation
- Escalation pattern detection (adjustments → component replacement)
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.event_models import ServiceEvent, ServiceEventAction
from app.models.master_models import Compressor, IssueCategory


@dataclass
class ActionFrequency:
    """How often a specific action occurs in a given context."""
    action_type: str
    count: int
    percentage: float
    context: str  # e.g., "machine MC6068" or "family reciprocating"


@dataclass
class RecurrenceSignal:
    """Detected pattern of recurring events."""
    signal_type: str  # repeat_action, escalation, chronic_issue
    description: str
    event_count: int
    time_span_days: int | None
    severity: str  # low, medium, high
    related_event_ids: list[str] = field(default_factory=list)


@dataclass
class AnalyticsSummary:
    """Aggregated analytics for a machine or query context."""
    total_events: int
    action_frequencies: list[ActionFrequency]
    issue_frequencies: list[ActionFrequency]
    recurrence_signals: list[RecurrenceSignal]
    recent_event_count_30d: int
    recent_event_count_90d: int
    avg_days_between_events: float | None


def get_action_frequencies_for_machine(
    db: Session,
    compressor_id: str,
    limit: int = 10,
) -> list[ActionFrequency]:
    """Compute the most frequent action types for a specific machine."""
    actions = (
        db.query(ServiceEventAction)
        .join(ServiceEvent, ServiceEventAction.service_event_id == ServiceEvent.id)
        .filter(ServiceEvent.compressor_id == compressor_id)
        .all()
    )

    counter: Counter[str] = Counter()
    for a in actions:
        if a.action_type_raw:
            counter[a.action_type_raw] += 1

    total = sum(counter.values())
    if total == 0:
        return []

    return [
        ActionFrequency(
            action_type=action_type,
            count=count,
            percentage=round(count / total, 3),
            context=f"machine {compressor_id}",
        )
        for action_type, count in counter.most_common(limit)
    ]


def get_action_frequencies_for_model(
    db: Session,
    compressor_type: str | None,
    limit: int = 10,
) -> list[ActionFrequency]:
    """Compute action frequencies across all machines of the same type/model."""
    if not compressor_type:
        return []

    actions = (
        db.query(ServiceEventAction)
        .join(ServiceEvent, ServiceEventAction.service_event_id == ServiceEvent.id)
        .join(Compressor, ServiceEvent.compressor_id == Compressor.id)
        .filter(Compressor.compressor_type == compressor_type)
        .all()
    )

    counter: Counter[str] = Counter()
    for a in actions:
        if a.action_type_raw:
            counter[a.action_type_raw] += 1

    total = sum(counter.values())
    if total == 0:
        return []

    return [
        ActionFrequency(
            action_type=action_type,
            count=count,
            percentage=round(count / total, 3),
            context=f"model {compressor_type}",
        )
        for action_type, count in counter.most_common(limit)
    ]


def get_issue_frequencies_for_machine(
    db: Session,
    compressor_id: str,
) -> list[ActionFrequency]:
    """Compute issue category frequencies for a specific machine."""
    events = (
        db.query(ServiceEvent)
        .filter(ServiceEvent.compressor_id == compressor_id)
        .all()
    )

    counter: Counter[str] = Counter()
    for e in events:
        cat = e.event_category or "other"
        counter[cat] += 1

    total = sum(counter.values())
    if total == 0:
        return []

    return [
        ActionFrequency(
            action_type=cat,
            count=count,
            percentage=round(count / total, 3),
            context=f"machine {compressor_id}",
        )
        for cat, count in counter.most_common()
    ]


def detect_recurrence_signals(
    db: Session,
    compressor_id: str,
    lookback_days: int = 90,
) -> list[RecurrenceSignal]:
    """Detect recurring patterns in recent service history for a machine.

    Checks for:
    1. Repeated identical actions within the lookback window
    2. Escalation patterns (e.g., repeated adjustments → replacement)
    3. Chronic issue categories recurring frequently
    """
    cutoff = date.today() - timedelta(days=lookback_days)

    recent_events = (
        db.query(ServiceEvent)
        .filter(
            ServiceEvent.compressor_id == compressor_id,
            ServiceEvent.event_date >= cutoff,
        )
        .order_by(ServiceEvent.event_date.desc())
        .all()
    )

    signals: list[RecurrenceSignal] = []

    if len(recent_events) < 2:
        return signals

    # 1. Repeated action types
    action_events: dict[str, list[ServiceEvent]] = {}
    for event in recent_events:
        for action in event.actions:
            if action.action_type_raw:
                action_events.setdefault(action.action_type_raw, []).append(event)

    for action_type, events_list in action_events.items():
        if len(events_list) >= 2:
            dates = sorted(
                [e.event_date for e in events_list if e.event_date],
            )
            if len(dates) >= 2:
                span = (dates[-1] - dates[0]).days
                severity = "high" if len(events_list) >= 3 else "medium"
                signals.append(RecurrenceSignal(
                    signal_type="repeat_action",
                    description=(
                        f"Action '{action_type}' has been performed "
                        f"{len(events_list)} times in the last {lookback_days} days"
                    ),
                    event_count=len(events_list),
                    time_span_days=span,
                    severity=severity,
                    related_event_ids=[e.id for e in events_list],
                ))

    # 2. Escalation pattern: adjustments followed by replacements
    adjustment_count = 0
    replacement_after = False
    for event in sorted(recent_events, key=lambda e: e.event_date or date.min):
        for action in event.actions:
            raw = (action.action_type_raw or "").lower()
            if raw in ("adjusted", "adjustment", "calibrated"):
                adjustment_count += 1
            elif raw in ("replaced", "component_replacement") and adjustment_count >= 2:
                replacement_after = True

    if adjustment_count >= 2 and replacement_after:
        signals.append(RecurrenceSignal(
            signal_type="escalation",
            description=(
                f"{adjustment_count} adjustment events preceded a component replacement — "
                "this pattern suggests the underlying issue may not have been fully resolved "
                "by adjustments alone"
            ),
            event_count=adjustment_count + 1,
            time_span_days=lookback_days,
            severity="high",
        ))
    elif adjustment_count >= 3:
        signals.append(RecurrenceSignal(
            signal_type="escalation",
            description=(
                f"{adjustment_count} adjustment events in {lookback_days} days without "
                "a definitive repair — consider deeper investigation"
            ),
            event_count=adjustment_count,
            time_span_days=lookback_days,
            severity="medium",
        ))

    # 3. Chronic issue category
    category_counter: Counter[str] = Counter()
    for event in recent_events:
        if event.event_category:
            category_counter[event.event_category] += 1

    for cat, count in category_counter.items():
        if count >= 3 and cat != "preventive_maintenance":
            signals.append(RecurrenceSignal(
                signal_type="chronic_issue",
                description=(
                    f"Issue category '{cat}' has occurred {count} times "
                    f"in the last {lookback_days} days"
                ),
                event_count=count,
                time_span_days=lookback_days,
                severity="high" if count >= 4 else "medium",
            ))

    return signals


def compute_resolution_rate(
    db: Session,
    compressor_id: str | None = None,
    issue_category_name: str | None = None,
) -> float | None:
    """Compute fraction of events with feedback marked as resolved.

    Returns None if no feedback data exists.
    """
    from app.models.analytics_models import FeedbackOutcome

    query = db.query(FeedbackOutcome)

    if compressor_id:
        query = (
            query.join(ServiceEvent, FeedbackOutcome.service_event_id == ServiceEvent.id)
            .filter(ServiceEvent.compressor_id == compressor_id)
        )

    feedbacks = query.all()
    if not feedbacks:
        return None

    resolved = sum(1 for f in feedbacks if f.issue_resolved is True)
    return round(resolved / len(feedbacks), 3) if feedbacks else None


def get_recent_event_counts(
    db: Session,
    compressor_id: str,
) -> tuple[int, int]:
    """Return (count_last_30_days, count_last_90_days) for a machine."""
    now = date.today()
    c30 = (
        db.query(func.count(ServiceEvent.id))
        .filter(
            ServiceEvent.compressor_id == compressor_id,
            ServiceEvent.event_date >= now - timedelta(days=30),
        )
        .scalar() or 0
    )
    c90 = (
        db.query(func.count(ServiceEvent.id))
        .filter(
            ServiceEvent.compressor_id == compressor_id,
            ServiceEvent.event_date >= now - timedelta(days=90),
        )
        .scalar() or 0
    )
    return c30, c90


def compute_avg_days_between_events(
    db: Session,
    compressor_id: str,
) -> float | None:
    """Average interval in days between service events for a machine."""
    events = (
        db.query(ServiceEvent.event_date)
        .filter(
            ServiceEvent.compressor_id == compressor_id,
            ServiceEvent.event_date.isnot(None),
        )
        .order_by(ServiceEvent.event_date)
        .all()
    )

    dates = [e[0] for e in events if e[0] is not None]
    if len(dates) < 2:
        return None

    intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
    return round(sum(intervals) / len(intervals), 1) if intervals else None


def build_analytics_summary(
    db: Session,
    compressor_id: str,
) -> AnalyticsSummary:
    """Build a full analytics summary for a machine."""
    total = (
        db.query(func.count(ServiceEvent.id))
        .filter(ServiceEvent.compressor_id == compressor_id)
        .scalar() or 0
    )

    action_freqs = get_action_frequencies_for_machine(db, compressor_id)
    issue_freqs = get_issue_frequencies_for_machine(db, compressor_id)
    recurrence = detect_recurrence_signals(db, compressor_id)
    c30, c90 = get_recent_event_counts(db, compressor_id)
    avg_interval = compute_avg_days_between_events(db, compressor_id)

    return AnalyticsSummary(
        total_events=total,
        action_frequencies=action_freqs,
        issue_frequencies=issue_freqs,
        recurrence_signals=recurrence,
        recent_event_count_30d=c30,
        recent_event_count_90d=c90,
        avg_days_between_events=avg_interval,
    )
