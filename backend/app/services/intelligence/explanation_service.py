"""Evidence-based plain-language explanation generation.

Layer 5b of the intelligence stack.

Every recommendation must include a human-readable explanation that
references the actual evidence used to produce it. This module
generates those explanations from structured evidence, avoiding
vague AI language.

Design rule: every sentence in the explanation must be traceable to
a data point. If no data supports a claim, the explanation must say so.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class EvidencePackage:
    """All evidence inputs needed to generate an explanation."""
    machine_unit_id: str
    similar_case_count: int
    top_action: str | None
    top_action_label: str | None
    top_action_frequency: float  # 0.0–1.0
    resolution_rate: float | None
    recurrence_signals: list[dict]  # from analytics_service
    recent_event_count_30d: int
    recent_event_count_90d: int
    issue_category_name: str | None
    issue_category_label: str | None
    issue_inference_confidence: float
    matched_keywords: list[str]
    confidence_label: str
    confidence_score: float
    avg_days_between_events: float | None
    compressor_type: str | None


def generate_explanation(evidence: EvidencePackage) -> str:
    """Generate a plain-language explanation from evidence.

    Returns a multi-sentence string suitable for display in the UI.
    Every sentence is directly supported by a data point.
    """
    lines: list[str] = []

    # Issue identification
    if evidence.issue_category_label and evidence.issue_inference_confidence > 0:
        if evidence.issue_inference_confidence >= 0.6:
            lines.append(
                f"Identified issue pattern: {evidence.issue_category_label}."
            )
        else:
            lines.append(
                f"Possible issue pattern: {evidence.issue_category_label} "
                f"(moderate confidence based on available keywords)."
            )

        if evidence.matched_keywords:
            kw_str = ", ".join(evidence.matched_keywords[:5])
            lines.append(f"Matched keywords in notes/description: {kw_str}.")

    # Similar cases
    if evidence.similar_case_count > 0:
        context = f"for compressor {evidence.machine_unit_id}"
        if evidence.compressor_type:
            context = f"for this compressor family ({evidence.compressor_type})"

        lines.append(
            f"{evidence.similar_case_count} similar historical cases "
            f"were found {context}."
        )

        if evidence.top_action_label and evidence.top_action_frequency > 0:
            pct = round(evidence.top_action_frequency * 100)
            lines.append(
                f"In {pct}% of those cases, technicians performed: "
                f"{evidence.top_action_label}."
            )

        if evidence.resolution_rate is not None:
            res_pct = round(evidence.resolution_rate * 100)
            lines.append(
                f"{res_pct}% of similar cases were resolved on the first visit."
            )
    else:
        lines.append(
            f"No similar historical cases were found for compressor "
            f"{evidence.machine_unit_id}. Recommendation is based on "
            f"general rules and issue classification."
        )

    # Recurrence
    if evidence.recurrence_signals:
        for signal in evidence.recurrence_signals[:2]:
            desc = signal.get("description", "")
            if desc:
                lines.append(desc + ".")

    # Recent activity
    if evidence.recent_event_count_30d >= 3:
        lines.append(
            f"This machine has had {evidence.recent_event_count_30d} service "
            f"events in the last 30 days, indicating elevated activity."
        )
    elif evidence.recent_event_count_90d >= 5:
        lines.append(
            f"This machine has had {evidence.recent_event_count_90d} service "
            f"events in the last 90 days."
        )

    # Average interval
    if evidence.avg_days_between_events is not None:
        lines.append(
            f"Average interval between service events for this machine: "
            f"{evidence.avg_days_between_events:.0f} days."
        )

    return " ".join(lines)


def generate_fallback_note(
    confidence_label: str,
    similar_case_count: int,
    has_issue_category: bool,
) -> str | None:
    """Generate a fallback note when confidence is low.

    Returns None if confidence is adequate.
    """
    if confidence_label == "high":
        return None

    reasons: list[str] = []

    if similar_case_count == 0:
        reasons.append("no similar historical cases were found")
    elif similar_case_count < 3:
        reasons.append("very few similar historical cases are available")

    if not has_issue_category:
        reasons.append("the issue category could not be confidently identified")

    if confidence_label == "low":
        if reasons:
            reason_str = " and ".join(reasons)
            return (
                f"Confidence is low because {reason_str}. "
                "Recommend manual inspection and senior technician review. "
                "The suggested workflow is a safe general triage procedure."
            )
        return (
            "Confidence is low due to limited evidence. "
            "Recommend manual inspection and senior technician review."
        )

    if confidence_label == "medium" and reasons:
        reason_str = " and ".join(reasons)
        return (
            f"Confidence is moderate. Note that {reason_str}. "
            "Consider additional investigation if the recommended action "
            "does not resolve the issue."
        )

    return None


def build_evidence_summary_dict(
    similar_case_count: int,
    top_action: str | None,
    top_action_label: str | None,
    top_action_frequency: float,
    resolution_rate: float | None,
    recent_event_count_30d: int,
    recent_event_count_90d: int,
    recurrence_signal_count: int,
    avg_days_between_events: float | None,
) -> dict:
    """Build the structured evidence_summary dict for the Recommendation model."""
    return {
        "similar_case_count": similar_case_count,
        "top_action": top_action,
        "top_action_label": top_action_label,
        "top_action_frequency": round(top_action_frequency, 3),
        "resolution_rate": resolution_rate,
        "recent_events_last_30_days": recent_event_count_30d,
        "recent_events_last_90_days": recent_event_count_90d,
        "recurrence_signal_count": recurrence_signal_count,
        "avg_days_between_events": avg_days_between_events,
    }
