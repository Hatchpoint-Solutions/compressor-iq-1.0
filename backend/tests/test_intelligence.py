"""Comprehensive tests for the intelligence layer services.

Covers:
- Keyword normalization
- Issue category inference (rules engine)
- Similarity scoring
- Workflow generation
- Confidence scoring
- Explanation generation
- Low-data fallback behavior
- End-to-end recommendation generation
"""

import pytest
from datetime import date, timedelta

from app.models.event_models import ServiceEvent, ServiceEventAction
from app.models.master_models import Compressor, IssueCategory, Site
from app.models.analytics_models import Recommendation, WorkflowStep, SimilarCase


# ═══════════════════════════════════════════════════════════════════════════
# 1. Keyword Normalization Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestKeywordNormalization:
    def test_normalize_oil_change(self):
        from app.services.intelligence.keyword_normalization import normalize_action
        result = normalize_action("changed engine oil and replaced filter")
        assert result.code == "oil_change"
        assert result.confidence > 0

    def test_normalize_spark_plug_replacement(self):
        from app.services.intelligence.keyword_normalization import normalize_action
        result = normalize_action("replaced spark plug on cylinder 5")
        assert result.code == "spark_plug_replacement"
        assert result.confidence >= 0.9

    def test_normalize_adjustment(self):
        from app.services.intelligence.keyword_normalization import normalize_action
        result = normalize_action("adjusted setpoint and calibrated controller")
        assert result.code == "adjustment"

    def test_normalize_unknown_action(self):
        from app.services.intelligence.keyword_normalization import normalize_action
        result = normalize_action("performed mysterious ritual on unit")
        assert result.code == "unknown"
        assert result.confidence == 0.0

    def test_normalize_empty_string(self):
        from app.services.intelligence.keyword_normalization import normalize_action
        result = normalize_action("")
        assert result.code == "unknown"

    def test_extract_keywords(self):
        from app.services.intelligence.keyword_normalization import extract_keywords
        result = extract_keywords(
            "unit down on detonation, pulled spark plug and checked oil pressure"
        )
        assert "detonation" in result.single_keywords
        assert "oil" in result.single_keywords
        assert "spark_plug" in result.compound_keywords

    def test_extract_keywords_empty(self):
        from app.services.intelligence.keyword_normalization import extract_keywords
        result = extract_keywords("")
        assert result.single_keywords == []
        assert result.compound_keywords == []

    def test_extract_keyword_set(self):
        from app.services.intelligence.keyword_normalization import extract_keyword_set
        tokens = extract_keyword_set("replaced filter and checked oil")
        assert "filter" in tokens or "oil" in tokens

    def test_normalize_batch(self):
        from app.services.intelligence.keyword_normalization import normalize_action_batch
        results = normalize_action_batch(["oil change", "adjusted settings", "xyz"])
        assert len(results) == 3
        assert results[0].code == "oil_change"
        assert results[2].code == "unknown"


# ═══════════════════════════════════════════════════════════════════════════
# 2. Rules Engine Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestRulesEngine:
    def test_infer_detonation(self):
        from app.services.intelligence.rules_engine import infer_issue_category
        result = infer_issue_category(notes="cylinder #5 detonation event, checked timing")
        assert result.category_name == "detonation"
        assert result.severity == "high"
        assert result.confidence > 0.4

    def test_infer_leak(self):
        from app.services.intelligence.rules_engine import infer_issue_category
        result = infer_issue_category(notes="found oil leak near compressor seal")
        assert result.category_name == "leak"

    def test_infer_fuel_system(self):
        from app.services.intelligence.rules_engine import infer_issue_category
        result = infer_issue_category(notes="adjusted fuel curve and BTU settings")
        assert result.category_name == "fuel_system"

    def test_infer_with_description(self):
        from app.services.intelligence.rules_engine import infer_issue_category
        result = infer_issue_category(description="CORRECTIVE - pressure abnormality")
        assert result.category_name == "pressure_abnormality"

    def test_infer_unknown(self):
        from app.services.intelligence.rules_engine import infer_issue_category
        result = infer_issue_category(notes="performed standard work")
        assert result.category_name == "unknown"
        assert result.confidence == 0.0

    def test_infer_pm_fallback(self):
        from app.services.intelligence.rules_engine import infer_issue_category
        result = infer_issue_category(
            notes="standard work", event_category="preventive_maintenance",
        )
        assert result.category_name == "routine_service"

    def test_recommended_actions_for_detonation(self):
        from app.services.intelligence.rules_engine import get_recommended_actions
        actions = get_recommended_actions("detonation")
        assert len(actions) >= 1
        assert actions[0].priority == 1

    def test_recommended_actions_for_unknown(self):
        from app.services.intelligence.rules_engine import get_recommended_actions
        actions = get_recommended_actions("unknown")
        assert len(actions) >= 1

    def test_primary_action(self):
        from app.services.intelligence.rules_engine import get_primary_action_for_issue
        action = get_primary_action_for_issue("lubrication")
        assert action is not None
        assert "oil" in action.action_label.lower() or "inspect" in action.action_label.lower()

    def test_secondary_categories(self):
        from app.services.intelligence.rules_engine import infer_issue_category
        result = infer_issue_category(
            notes="found oil leak near fuel valve with pressure drop",
        )
        assert len(result.secondary_categories) > 0


# ═══════════════════════════════════════════════════════════════════════════
# 3. Confidence Scoring Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestConfidenceScoring:
    def test_high_confidence(self):
        from app.services.intelligence.confidence_service import compute_confidence
        result = compute_confidence(
            similar_case_count=15,
            top_action_frequency=0.8,
            has_issue_category=True,
            issue_inference_confidence=0.8,
            recurrence_signal_count=2,
            data_completeness_score=0.9,
            resolution_rate=0.7,
        )
        assert result.label == "high"
        assert result.score >= 0.65

    def test_medium_confidence(self):
        from app.services.intelligence.confidence_service import compute_confidence
        result = compute_confidence(
            similar_case_count=4,
            top_action_frequency=0.5,
            has_issue_category=True,
            issue_inference_confidence=0.5,
            recurrence_signal_count=0,
            data_completeness_score=0.6,
            resolution_rate=None,
        )
        assert result.label in ("medium", "high")
        assert result.score >= 0.35

    def test_low_confidence(self):
        from app.services.intelligence.confidence_service import compute_confidence
        result = compute_confidence(
            similar_case_count=0,
            top_action_frequency=0.0,
            has_issue_category=False,
            issue_inference_confidence=0.0,
            recurrence_signal_count=0,
            data_completeness_score=0.2,
            resolution_rate=None,
        )
        assert result.label == "low"
        assert result.score <= 0.35

    def test_confidence_has_factors(self):
        from app.services.intelligence.confidence_service import compute_confidence
        result = compute_confidence(
            similar_case_count=5,
            top_action_frequency=0.6,
            has_issue_category=True,
            issue_inference_confidence=0.7,
            recurrence_signal_count=1,
            data_completeness_score=0.8,
            resolution_rate=0.6,
        )
        assert len(result.factors) == 6
        assert all(f.name for f in result.factors)
        assert result.summary

    def test_confidence_bounded(self):
        from app.services.intelligence.confidence_service import compute_confidence
        result = compute_confidence(
            similar_case_count=100,
            top_action_frequency=1.0,
            has_issue_category=True,
            issue_inference_confidence=1.0,
            recurrence_signal_count=5,
            data_completeness_score=1.0,
            resolution_rate=1.0,
        )
        assert result.score <= 0.95

    def test_data_completeness(self):
        from app.services.intelligence.confidence_service import compute_data_completeness
        score = compute_data_completeness(
            has_notes=True, has_description=True, has_event_date=True,
            has_run_hours=True, has_event_category=True, has_actions=True,
        )
        assert score == 1.0

        score_partial = compute_data_completeness(
            has_notes=True, has_description=False, has_event_date=True,
            has_run_hours=False, has_event_category=True, has_actions=False,
        )
        assert score_partial == 0.5


# ═══════════════════════════════════════════════════════════════════════════
# 4. Workflow Generation Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestWorkflowGeneration:
    def test_detonation_workflow(self):
        from app.services.intelligence.workflow_service import generate_workflow
        wf = generate_workflow("detonation")
        assert len(wf.steps) >= 5
        assert wf.issue_category == "detonation"
        assert all(s.instruction for s in wf.steps)
        assert all(s.rationale for s in wf.steps)

    def test_unknown_workflow_uses_default(self):
        from app.services.intelligence.workflow_service import generate_workflow
        wf = generate_workflow("nonexistent_category")
        assert len(wf.steps) >= 5

    def test_recurrence_adds_step(self):
        from app.services.intelligence.workflow_service import generate_workflow
        wf_no_rec = generate_workflow("lubrication", has_recurrence=False)
        wf_with_rec = generate_workflow(
            "lubrication", has_recurrence=True,
            recurrence_description="Oil change repeated 3 times in 60 days",
        )
        assert len(wf_with_rec.steps) == len(wf_no_rec.steps) + 1
        assert "recurrence" in wf_with_rec.steps[0].instruction.lower()

    def test_low_confidence_adds_escalation(self):
        from app.services.intelligence.workflow_service import generate_workflow
        wf = generate_workflow("leak", confidence_label="low")
        last_step = wf.steps[-1]
        assert "escalat" in last_step.instruction.lower()

    def test_steps_have_sequential_numbers(self):
        from app.services.intelligence.workflow_service import generate_workflow
        wf = generate_workflow("valve_failure")
        for i, step in enumerate(wf.steps):
            assert step.step_number == i + 1


# ═══════════════════════════════════════════════════════════════════════════
# 5. Explanation Generation Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestExplanationGeneration:
    def test_explanation_with_evidence(self):
        from app.services.intelligence.explanation_service import (
            EvidencePackage, generate_explanation,
        )
        evidence = EvidencePackage(
            machine_unit_id="MC6068",
            similar_case_count=12,
            top_action="oil_change",
            top_action_label="Oil Change",
            top_action_frequency=0.72,
            resolution_rate=0.65,
            recurrence_signals=[],
            recent_event_count_30d=2,
            recent_event_count_90d=5,
            issue_category_name="lubrication",
            issue_category_label="Lubrication / Oil Service",
            issue_inference_confidence=0.7,
            matched_keywords=["oil", "lubrication"],
            confidence_label="high",
            confidence_score=0.78,
            avg_days_between_events=14.5,
            compressor_type="reciprocating",
        )
        text = generate_explanation(evidence)
        assert "12 similar" in text
        assert "72%" in text
        assert "Oil Change" in text
        assert "MC6068" not in text or "reciprocating" in text

    def test_explanation_no_similar_cases(self):
        from app.services.intelligence.explanation_service import (
            EvidencePackage, generate_explanation,
        )
        evidence = EvidencePackage(
            machine_unit_id="MC9999",
            similar_case_count=0,
            top_action=None,
            top_action_label=None,
            top_action_frequency=0.0,
            resolution_rate=None,
            recurrence_signals=[],
            recent_event_count_30d=0,
            recent_event_count_90d=0,
            issue_category_name="unknown",
            issue_category_label=None,
            issue_inference_confidence=0.0,
            matched_keywords=[],
            confidence_label="low",
            confidence_score=0.10,
            avg_days_between_events=None,
            compressor_type=None,
        )
        text = generate_explanation(evidence)
        assert "No similar" in text
        assert "general rules" in text

    def test_fallback_note_low_confidence(self):
        from app.services.intelligence.explanation_service import generate_fallback_note
        note = generate_fallback_note(
            confidence_label="low", similar_case_count=0,
            has_issue_category=False,
        )
        assert note is not None
        assert "low" in note.lower()
        assert "manual" in note.lower() or "senior" in note.lower()

    def test_fallback_note_high_confidence(self):
        from app.services.intelligence.explanation_service import generate_fallback_note
        note = generate_fallback_note(
            confidence_label="high", similar_case_count=15,
            has_issue_category=True,
        )
        assert note is None

    def test_evidence_summary_dict(self):
        from app.services.intelligence.explanation_service import (
            build_evidence_summary_dict,
        )
        summary = build_evidence_summary_dict(
            similar_case_count=10,
            top_action="oil_change",
            top_action_label="Oil Change",
            top_action_frequency=0.7,
            resolution_rate=0.65,
            recent_event_count_30d=3,
            recent_event_count_90d=8,
            recurrence_signal_count=2,
            avg_days_between_events=15.0,
        )
        assert summary["similar_case_count"] == 10
        assert summary["top_action"] == "oil_change"
        assert summary["resolution_rate"] == 0.65


# ═══════════════════════════════════════════════════════════════════════════
# 6. Database-dependent tests (similarity, analytics, end-to-end)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def seeded_db(db):
    """Seed the test database with realistic compressor service data."""
    import uuid
    import app.models  # noqa: F401 — register all models

    tag = uuid.uuid4().hex[:6]

    site = Site(plant_code=f"T{tag[:4]}", customer_name=f"TestCorp-{tag}")
    db.add(site)
    db.flush()

    comp = Compressor(
        unit_id=f"MC{tag}",
        equipment_number="500021946",
        compressor_type="reciprocating",
        site_id=site.id,
    )
    db.add(comp)
    db.flush()

    cat_deton = IssueCategory(name=f"detonation_{tag}", severity_default="high")
    cat_lube = IssueCategory(name=f"lubrication_{tag}", severity_default="medium")
    db.add_all([cat_deton, cat_lube])
    db.flush()

    today = date.today()

    events_data = [
        {
            "order_number": f"ORD001-{tag}",
            "order_description": "JANUARY 2020 CALLOUTS",
            "event_date": today - timedelta(days=90),
            "event_category": "corrective",
            "maintenance_activity_type": "unscheduled_repair",
            "technician_notes_raw": "unit down on detonation, replaced spark plug",
            "issue_category_id": cat_deton.id,
            "order_status": "TECO",
        },
        {
            "order_number": f"ORD002-{tag}",
            "order_description": "CORRECTIVE - detonation issue",
            "event_date": today - timedelta(days=60),
            "event_category": "corrective",
            "maintenance_activity_type": "unscheduled_repair",
            "technician_notes_raw": "detonation on cylinder 3, adjusted fuel curve and BTU",
            "issue_category_id": cat_deton.id,
            "order_status": "TECO",
        },
        {
            "order_number": f"ORD003-{tag}",
            "order_description": "Oil service",
            "event_date": today - timedelta(days=30),
            "event_category": "corrective",
            "maintenance_activity_type": "unscheduled_repair",
            "technician_notes_raw": "changed engine oil, replaced oil filter, checked coolant",
            "issue_category_id": cat_lube.id,
            "order_status": "TECO",
        },
        {
            "order_number": f"ORD004-{tag}",
            "order_description": "PM-1 Maintenance",
            "event_date": today - timedelta(days=15),
            "event_category": "preventive_maintenance",
            "maintenance_activity_type": "preventive_maintenance",
            "technician_notes_raw": "completed PM1, checked filters, oil level good",
            "order_status": "TECO",
        },
        {
            "order_number": f"ORD005-{tag}",
            "order_description": "CORRECTIVE - detonation recurrence",
            "event_date": today - timedelta(days=5),
            "event_category": "corrective",
            "maintenance_activity_type": "unscheduled_repair",
            "technician_notes_raw": "detonation again on cylinder 5, pulled spark plug and gapped",
            "issue_category_id": cat_deton.id,
            "order_status": "Released",
        },
    ]

    events = []
    for data in events_data:
        event = ServiceEvent(compressor_id=comp.id, **data)
        db.add(event)
        db.flush()
        events.append(event)

    actions_data = [
        (events[0].id, "replaced", "spark_plug", "replaced spark plug on cylinder 5"),
        (events[1].id, "adjusted", "fuel_system", "adjusted fuel curve and BTU settings"),
        (events[1].id, "inspected", "spark_plug", "inspected spark plugs all cylinders"),
        (events[2].id, "replaced", "oil", "changed engine oil"),
        (events[2].id, "replaced", "filter", "replaced oil filter"),
        (events[3].id, "inspected", "filter", "checked air filters"),
        (events[3].id, "inspected", "oil", "checked oil level"),
        (events[4].id, "inspected", "spark_plug", "pulled and gapped spark plug"),
        (events[4].id, "adjusted", "spark_plug", "regapped spark plug cylinder 5"),
    ]

    for event_id, action_type, component, desc in actions_data:
        db.add(ServiceEventAction(
            service_event_id=event_id,
            action_type_raw=action_type,
            component=component,
            description=desc,
        ))

    db.flush()
    return db, comp, events, cat_deton, cat_lube


class TestSimilarityService:
    def test_find_similar_cases(self, seeded_db):
        db, comp, events, cat_deton, _ = seeded_db
        from app.services.intelligence.similarity_service import find_similar_cases

        results = find_similar_cases(events[4], db, limit=10)
        assert len(results) >= 1
        scores = [r.similarity_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_similar_cases_have_reasons(self, seeded_db):
        db, comp, events, _, _ = seeded_db
        from app.services.intelligence.similarity_service import find_similar_cases

        results = find_similar_cases(events[4], db)
        for result in results:
            assert len(result.match_reasons) >= 1

    def test_similar_cases_exclude_self(self, seeded_db):
        db, comp, events, _, _ = seeded_db
        from app.services.intelligence.similarity_service import find_similar_cases

        results = find_similar_cases(events[0], db)
        result_ids = {r.event.id for r in results}
        assert events[0].id not in result_ids


class TestAnalyticsService:
    def test_action_frequencies(self, seeded_db):
        db, comp, events, _, _ = seeded_db
        from app.services.intelligence.analytics_service import (
            get_action_frequencies_for_machine,
        )
        freqs = get_action_frequencies_for_machine(db, comp.id)
        assert len(freqs) >= 1
        total_pct = sum(f.percentage for f in freqs)
        assert abs(total_pct - 1.0) < 0.01

    def test_recurrence_detection(self, seeded_db):
        db, comp, events, _, _ = seeded_db
        from app.services.intelligence.analytics_service import (
            detect_recurrence_signals,
        )
        signals = detect_recurrence_signals(db, comp.id, lookback_days=120)
        assert len(signals) >= 1
        signal_types = {s.signal_type for s in signals}
        assert "repeat_action" in signal_types or "chronic_issue" in signal_types

    def test_recent_event_counts(self, seeded_db):
        db, comp, events, _, _ = seeded_db
        from app.services.intelligence.analytics_service import (
            get_recent_event_counts,
        )
        c30, c90 = get_recent_event_counts(db, comp.id)
        assert c30 >= 1
        assert c90 >= c30

    def test_avg_interval(self, seeded_db):
        db, comp, events, _, _ = seeded_db
        from app.services.intelligence.analytics_service import (
            compute_avg_days_between_events,
        )
        avg = compute_avg_days_between_events(db, comp.id)
        assert avg is not None
        assert avg > 0


class TestEndToEndRecommendation:
    def test_generate_recommendation(self, seeded_db):
        db, comp, events, cat_deton, _ = seeded_db
        from app.services.recommendation_service import generate_recommendation

        rec = generate_recommendation(events[4], db)

        assert rec.id is not None
        assert rec.compressor_id == comp.id
        assert rec.confidence_score > 0
        assert rec.confidence_label in ("high", "medium", "low")
        assert rec.reasoning is not None
        assert len(rec.reasoning) > 50
        assert rec.evidence_summary is not None
        assert rec.similar_case_count >= 1

    def test_recommendation_has_workflow(self, seeded_db):
        db, comp, events, _, _ = seeded_db
        from app.services.recommendation_service import generate_recommendation

        rec = generate_recommendation(events[4], db)
        db.refresh(rec)

        steps = rec.workflow_steps
        assert len(steps) >= 3
        assert all(s.instruction for s in steps)
        assert all(s.rationale for s in steps)

        numbers = [s.step_number for s in steps]
        assert numbers == sorted(numbers)

    def test_recommendation_has_similar_cases(self, seeded_db):
        db, comp, events, _, _ = seeded_db
        from app.services.recommendation_service import generate_recommendation

        rec = generate_recommendation(events[4], db)

        cases = rec.similar_cases
        assert len(cases) >= 1
        assert all(c.similarity_score > 0 for c in cases)

    def test_no_history_fallback(self, seeded_db):
        db, comp, events, _, _ = seeded_db

        new_comp = Compressor(unit_id="MC9999", compressor_type="reciprocating")
        db.add(new_comp)
        db.flush()

        from app.services.recommendation_service import (
            generate_recommendation_for_machine,
        )
        rec = generate_recommendation_for_machine(new_comp.id, db)

        assert rec.confidence_label == "low"
        assert rec.fallback_note is not None
        assert rec.similar_case_count == 0
        assert len(rec.workflow_steps) >= 3

    def test_recommendation_with_extra_notes(self, seeded_db):
        db, comp, events, _, _ = seeded_db
        from app.services.recommendation_service import generate_recommendation

        rec = generate_recommendation(
            events[4], db,
            current_notes="also noticed oil leak near compressor seal",
        )
        assert rec.id is not None
        assert rec.reasoning is not None
