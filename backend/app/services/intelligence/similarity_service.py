"""Similar case retrieval with weighted multi-factor scoring.

Layer 3 of the intelligence stack.

Searches across the full event history and scores candidates on multiple
dimensions.  Designed so that vector / embedding search can be plugged in
later as an additional scoring factor.

Similarity weights (configurable):
- Same machine:          0.20
- Same machine family:   0.10
- Same issue category:   0.25
- Same event category:   0.15
- Same site:             0.05
- Keyword overlap:       0.15  (Jaccard on technical keyword sets)
- Temporal proximity:    0.10  (closer events score higher)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.event_models import ServiceEvent, ServiceEventAction
from app.models.master_models import Compressor

from app.services.intelligence.keyword_normalization import extract_keyword_set


# ── Configuration ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SimilarityWeights:
    same_machine: float = 0.20
    same_machine_family: float = 0.10
    same_issue_category: float = 0.25
    same_event_category: float = 0.15
    same_site: float = 0.05
    keyword_overlap: float = 0.15
    temporal_proximity: float = 0.10

DEFAULT_WEIGHTS = SimilarityWeights()

TEMPORAL_DECAY_DAYS = 365 * 2  # events older than 2 years get minimal temporal score


# ── Output types ──────────────────────────────────────────────────────────

@dataclass
class SimilarCaseResult:
    """A single similar historical case with its score and match reasons."""
    event: ServiceEvent
    similarity_score: float
    match_reasons: list[str]
    event_date: date | None
    machine_id: str
    issue_category_name: str | None
    event_category: str | None
    action_summary: str
    resolution_status: str | None


# ── Core similarity logic ─────────────────────────────────────────────────

def find_similar_cases(
    event: ServiceEvent,
    db: Session,
    limit: int = 15,
    weights: SimilarityWeights = DEFAULT_WEIGHTS,
    include_same_machine: bool = True,
    include_cross_machine: bool = True,
) -> list[SimilarCaseResult]:
    """Find historical events most similar to the given event.

    Searches both same-machine history and cross-machine cases (same
    model/family and same site).

    Returns up to ``limit`` cases sorted by similarity score descending.
    """
    # Gather reference data about the current event's machine
    compressor = db.query(Compressor).filter(Compressor.id == event.compressor_id).first()

    # Build candidate query — exclude the event itself
    candidates: list[ServiceEvent] = []

    if include_same_machine:
        same_machine = (
            db.query(ServiceEvent)
            .filter(
                ServiceEvent.id != event.id,
                ServiceEvent.compressor_id == event.compressor_id,
            )
            .all()
        )
        candidates.extend(same_machine)

    if include_cross_machine and compressor:
        cross_filters = []
        if compressor.compressor_type:
            sibling_ids = (
                db.query(Compressor.id)
                .filter(
                    Compressor.compressor_type == compressor.compressor_type,
                    Compressor.id != compressor.id,
                )
                .all()
            )
            cross_filters.extend([sid[0] for sid in sibling_ids])

        if compressor.site_id:
            site_ids = (
                db.query(Compressor.id)
                .filter(
                    Compressor.site_id == compressor.site_id,
                    Compressor.id != compressor.id,
                )
                .all()
            )
            cross_filters.extend([sid[0] for sid in site_ids])

        if cross_filters:
            unique_comp_ids = list(set(cross_filters))
            cross_events = (
                db.query(ServiceEvent)
                .filter(
                    ServiceEvent.id != event.id,
                    ServiceEvent.compressor_id.in_(unique_comp_ids),
                )
                .all()
            )
            # Deduplicate against same-machine results
            existing_ids = {c.id for c in candidates}
            candidates.extend(e for e in cross_events if e.id not in existing_ids)

    if not candidates:
        return []

    # Pre-compute keyword set for the reference event
    ref_keywords = _event_keywords(event)

    # Score each candidate
    scored: list[SimilarCaseResult] = []

    for candidate in candidates:
        score, reasons = _compute_similarity(
            ref_event=event,
            candidate=candidate,
            ref_compressor=compressor,
            ref_keywords=ref_keywords,
            db=db,
            weights=weights,
        )

        if score < 0.05:
            continue

        # Summarize the candidate's actions
        action_summary = _action_summary(candidate)
        resolution_status = _infer_resolution(candidate)

        # Get the candidate's issue category name
        issue_cat_name = None
        if candidate.issue_category:
            issue_cat_name = candidate.issue_category.name

        scored.append(SimilarCaseResult(
            event=candidate,
            similarity_score=round(score, 3),
            match_reasons=reasons,
            event_date=candidate.event_date,
            machine_id=candidate.compressor_id,
            issue_category_name=issue_cat_name,
            event_category=candidate.event_category,
            action_summary=action_summary,
            resolution_status=resolution_status,
        ))

    scored.sort(key=lambda x: x.similarity_score, reverse=True)
    return scored[:limit]


def _compute_similarity(
    ref_event: ServiceEvent,
    candidate: ServiceEvent,
    ref_compressor: Compressor | None,
    ref_keywords: set[str],
    db: Session,
    weights: SimilarityWeights,
) -> tuple[float, list[str]]:
    """Compute a weighted similarity score between two events."""
    score = 0.0
    reasons: list[str] = []

    # Same machine
    if ref_event.compressor_id == candidate.compressor_id:
        score += weights.same_machine
        reasons.append("Same machine")

    # Same machine family/type
    if ref_compressor and ref_compressor.compressor_type:
        cand_comp = db.query(Compressor).filter(Compressor.id == candidate.compressor_id).first()
        if cand_comp and cand_comp.compressor_type == ref_compressor.compressor_type:
            if ref_event.compressor_id != candidate.compressor_id:
                score += weights.same_machine_family
                reasons.append(f"Same machine family: {ref_compressor.compressor_type}")

    # Same issue category
    if ref_event.issue_category_id and candidate.issue_category_id:
        if ref_event.issue_category_id == candidate.issue_category_id:
            score += weights.same_issue_category
            reasons.append("Same issue category")

    # Same event category
    if ref_event.event_category and candidate.event_category:
        if ref_event.event_category == candidate.event_category:
            score += weights.same_event_category
            reasons.append(f"Same event category: {ref_event.event_category}")

    # Same site
    if ref_compressor and ref_compressor.site_id:
        cand_comp = db.query(Compressor).filter(Compressor.id == candidate.compressor_id).first()
        if cand_comp and cand_comp.site_id == ref_compressor.site_id:
            if ref_event.compressor_id != candidate.compressor_id:
                score += weights.same_site
                reasons.append("Same site/location")

    # Keyword overlap (Jaccard similarity)
    cand_keywords = _event_keywords(candidate)
    if ref_keywords and cand_keywords:
        intersection = ref_keywords & cand_keywords
        union = ref_keywords | cand_keywords
        jaccard = len(intersection) / len(union) if union else 0
        if jaccard > 0.05:
            keyword_score = jaccard * weights.keyword_overlap
            score += keyword_score
            common = sorted(intersection)[:5]
            reasons.append(f"Shared keywords: {', '.join(common)}")

    # Temporal proximity
    if ref_event.event_date and candidate.event_date:
        days_apart = abs((ref_event.event_date - candidate.event_date).days)
        if days_apart < TEMPORAL_DECAY_DAYS:
            temporal_score = (1 - days_apart / TEMPORAL_DECAY_DAYS) * weights.temporal_proximity
            score += temporal_score
            if days_apart <= 30:
                reasons.append(f"Very recent: {days_apart} days apart")
            elif days_apart <= 90:
                reasons.append(f"Recent: {days_apart} days apart")

    return score, reasons


def _event_keywords(event: ServiceEvent) -> set[str]:
    """Extract the combined keyword set from an event's text fields."""
    text_parts: list[str] = []
    if event.technician_notes_raw:
        text_parts.append(event.technician_notes_raw)
    if event.order_description:
        text_parts.append(event.order_description)
    if event.technician_notes_clean:
        text_parts.append(event.technician_notes_clean)
    combined = " ".join(text_parts)
    return extract_keyword_set(combined)


def _action_summary(event: ServiceEvent) -> str:
    """Build a brief summary of the actions taken for an event."""
    if not event.actions:
        return "No structured actions recorded"

    action_types = [a.action_type_raw for a in event.actions if a.action_type_raw]
    if not action_types:
        return "Actions present but not typed"

    unique_actions = list(dict.fromkeys(action_types))
    return ", ".join(unique_actions[:3])


def _infer_resolution(event: ServiceEvent) -> str | None:
    """Infer resolution status from order status or feedback."""
    if event.feedback and event.feedback.issue_resolved is not None:
        return "resolved" if event.feedback.issue_resolved else "unresolved"

    if event.order_status:
        status_lower = event.order_status.lower()
        if status_lower in ("teco", "closed"):
            return "closed"
        if status_lower in ("released", "created"):
            return "open"

    return None
