"""Explainable confidence scoring.

Layer 5 of the intelligence stack.

Computes a bounded confidence score (0.0–1.0) from multiple evidence
factors, each contributing a documented, auditable portion of the score.

Factors:
1. Similar case volume     — more cases = more confidence
2. Action consistency      — if similar cases converge on one action
3. Issue category clarity  — was a clear category identified?
4. Recurrence strength     — recurrence signals increase or decrease confidence
5. Data completeness       — missing fields reduce confidence
6. Resolution history      — historical resolution rate
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ConfidenceFactor:
    """A single factor contributing to the confidence score."""
    name: str
    weight: float
    raw_score: float  # 0.0–1.0 for this factor
    weighted_score: float  # weight * raw_score
    explanation: str


@dataclass
class ConfidenceResult:
    """Full confidence computation result."""
    score: float  # final bounded score 0.0–1.0
    label: str  # high / medium / low
    factors: list[ConfidenceFactor] = field(default_factory=list)
    summary: str = ""


# ── Thresholds ────────────────────────────────────────────────────────────

HIGH_THRESHOLD = 0.65
MEDIUM_THRESHOLD = 0.35


def _label_from_score(score: float) -> str:
    if score >= HIGH_THRESHOLD:
        return "high"
    if score >= MEDIUM_THRESHOLD:
        return "medium"
    return "low"


# ── Factor computation ────────────────────────────────────────────────────

def compute_confidence(
    similar_case_count: int,
    top_action_frequency: float,
    has_issue_category: bool,
    issue_inference_confidence: float,
    recurrence_signal_count: int,
    data_completeness_score: float,
    resolution_rate: float | None,
) -> ConfidenceResult:
    """Compute a multi-factor confidence score.

    All inputs are simple scalars; the caller gathers them from the
    analytics, similarity, and rules layers.

    Returns a ConfidenceResult with the score, label, individual factor
    contributions, and a human-readable summary.
    """
    factors: list[ConfidenceFactor] = []

    # Factor 1: Similar case volume (weight: 0.25)
    if similar_case_count >= 10:
        vol_raw = 1.0
        vol_expl = f"{similar_case_count} similar cases — strong evidence base"
    elif similar_case_count >= 5:
        vol_raw = 0.7
        vol_expl = f"{similar_case_count} similar cases — moderate evidence"
    elif similar_case_count >= 2:
        vol_raw = 0.4
        vol_expl = f"{similar_case_count} similar cases — limited evidence"
    elif similar_case_count == 1:
        vol_raw = 0.2
        vol_expl = "Only 1 similar case found — very limited evidence"
    else:
        vol_raw = 0.0
        vol_expl = "No similar historical cases found"

    w_vol = 0.25
    factors.append(ConfidenceFactor(
        name="similar_case_volume", weight=w_vol,
        raw_score=vol_raw, weighted_score=round(w_vol * vol_raw, 4),
        explanation=vol_expl,
    ))

    # Factor 2: Action consistency (weight: 0.25)
    w_act = 0.25
    if top_action_frequency >= 0.7:
        act_raw = 1.0
        act_expl = (
            f"Top action accounts for {top_action_frequency:.0%} of similar cases — "
            "very consistent"
        )
    elif top_action_frequency >= 0.4:
        act_raw = 0.6
        act_expl = (
            f"Top action accounts for {top_action_frequency:.0%} of similar cases — "
            "moderately consistent"
        )
    elif top_action_frequency > 0:
        act_raw = 0.3
        act_expl = (
            f"Top action accounts for {top_action_frequency:.0%} of similar cases — "
            "low consistency"
        )
    else:
        act_raw = 0.0
        act_expl = "No action pattern found in similar cases"

    factors.append(ConfidenceFactor(
        name="action_consistency", weight=w_act,
        raw_score=act_raw, weighted_score=round(w_act * act_raw, 4),
        explanation=act_expl,
    ))

    # Factor 3: Issue category clarity (weight: 0.20)
    w_issue = 0.20
    if has_issue_category and issue_inference_confidence >= 0.6:
        issue_raw = 1.0
        issue_expl = "Clear issue category identified with high confidence"
    elif has_issue_category:
        issue_raw = 0.5 + (issue_inference_confidence * 0.5)
        issue_expl = f"Issue category identified (confidence: {issue_inference_confidence:.0%})"
    else:
        issue_raw = 0.1
        issue_expl = "No clear issue category could be identified"

    factors.append(ConfidenceFactor(
        name="issue_category_clarity", weight=w_issue,
        raw_score=round(issue_raw, 4), weighted_score=round(w_issue * issue_raw, 4),
        explanation=issue_expl,
    ))

    # Factor 4: Recurrence strength (weight: 0.10)
    w_rec = 0.10
    if recurrence_signal_count >= 2:
        rec_raw = 1.0
        rec_expl = (
            f"{recurrence_signal_count} recurrence signals detected — "
            "strong pattern of repeated events"
        )
    elif recurrence_signal_count == 1:
        rec_raw = 0.5
        rec_expl = "1 recurrence signal detected"
    else:
        rec_raw = 0.2
        rec_expl = "No recurrence patterns detected (not necessarily bad)"

    factors.append(ConfidenceFactor(
        name="recurrence_strength", weight=w_rec,
        raw_score=rec_raw, weighted_score=round(w_rec * rec_raw, 4),
        explanation=rec_expl,
    ))

    # Factor 5: Data completeness (weight: 0.10)
    w_data = 0.10
    data_raw = max(0.0, min(1.0, data_completeness_score))
    if data_raw >= 0.8:
        data_expl = "Event data is mostly complete"
    elif data_raw >= 0.5:
        data_expl = "Some data fields are missing — reduces certainty"
    else:
        data_expl = "Significant data gaps — confidence reduced"

    factors.append(ConfidenceFactor(
        name="data_completeness", weight=w_data,
        raw_score=round(data_raw, 4), weighted_score=round(w_data * data_raw, 4),
        explanation=data_expl,
    ))

    # Factor 6: Historical resolution rate (weight: 0.10)
    w_res = 0.10
    if resolution_rate is not None:
        res_raw = resolution_rate
        res_expl = (
            f"Historical resolution rate: {resolution_rate:.0%} of similar cases resolved"
        )
    else:
        res_raw = 0.3  # neutral score when no feedback data exists
        res_expl = "No resolution feedback available yet — using neutral baseline"

    factors.append(ConfidenceFactor(
        name="resolution_history", weight=w_res,
        raw_score=round(res_raw, 4), weighted_score=round(w_res * res_raw, 4),
        explanation=res_expl,
    ))

    # Compute final score
    total = sum(f.weighted_score for f in factors)
    # Apply floor — even with zero evidence, we give a small base confidence
    final_score = max(0.10, min(0.95, round(total, 2)))
    label = _label_from_score(final_score)

    summary = _build_confidence_summary(final_score, label, factors)

    return ConfidenceResult(
        score=final_score,
        label=label,
        factors=factors,
        summary=summary,
    )


def _build_confidence_summary(
    score: float,
    label: str,
    factors: list[ConfidenceFactor],
) -> str:
    """Build a one-sentence summary of the confidence assessment."""
    top_factors = sorted(factors, key=lambda f: f.weighted_score, reverse=True)[:2]
    drivers = " and ".join(f.name.replace("_", " ") for f in top_factors)
    return (
        f"Confidence is {label} ({score:.0%}), primarily driven by {drivers}."
    )


def compute_data_completeness(
    has_notes: bool,
    has_description: bool,
    has_event_date: bool,
    has_run_hours: bool,
    has_event_category: bool,
    has_actions: bool,
) -> float:
    """Score data completeness from 0.0 to 1.0 based on field availability.

    Each field contributes equally. These are the fields most important
    for the recommendation engine to function well.
    """
    fields = [has_notes, has_description, has_event_date,
              has_run_hours, has_event_category, has_actions]
    return round(sum(1 for f in fields if f) / len(fields), 3)
