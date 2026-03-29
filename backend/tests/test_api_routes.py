"""API route integration tests using FastAPI TestClient.

Tests the full request/response cycle through the routes using an
in-memory SQLite database. Covers health, compressors, service events,
dashboard, recommendations, feedback, and analytics endpoints.
"""

import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.models.event_models import ServiceEvent, ServiceEventAction
from app.models.master_models import Compressor, IssueCategory, Site


@pytest.fixture(scope="module")
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="module")
def test_session_factory(test_engine):
    return sessionmaker(bind=test_engine)


@pytest.fixture
def db_session(test_session_factory):
    session = test_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session):
    """TestClient that overrides the DB dependency with the test session."""

    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_data(db_session):
    """Seed realistic data and return references for test assertions."""
    tag = uuid.uuid4().hex[:6]

    site = Site(plant_code=f"P{tag[:4]}", customer_name=f"TestCo-{tag}")
    db_session.add(site)
    db_session.flush()

    comp = Compressor(
        unit_id=f"MC{tag}",
        equipment_number="500099",
        compressor_type="reciprocating",
        site_id=site.id,
        status="active",
    )
    db_session.add(comp)
    db_session.flush()

    cat = IssueCategory(name=f"detonation_{tag}", severity_default="high")
    db_session.add(cat)
    db_session.flush()

    today = date.today()
    events = []
    for i, (desc, cat_val, notes, status) in enumerate([
        ("CORRECTIVE - detonation", "corrective",
         "unit down on detonation, replaced spark plug", "TECO"),
        ("CORRECTIVE - oil leak", "corrective",
         "found oil leak near compressor seal, tightened fittings", "TECO"),
        ("PM-1 Maintenance", "preventive_maintenance",
         "completed PM1, checked filters, oil level good", "TECO"),
    ]):
        event = ServiceEvent(
            compressor_id=comp.id,
            order_number=f"ORD{i:03d}-{tag}",
            order_description=desc,
            event_date=today - timedelta(days=30 * (3 - i)),
            event_category=cat_val,
            maintenance_activity_type="unscheduled_repair" if cat_val == "corrective" else "preventive_maintenance",
            technician_notes_raw=notes,
            order_status=status,
            order_cost=1500.0 + i * 500,
            issue_category_id=cat.id if i == 0 else None,
        )
        db_session.add(event)
        db_session.flush()
        events.append(event)

    db_session.add(ServiceEventAction(
        service_event_id=events[0].id,
        action_type_raw="replaced",
        component="spark_plug",
        description="replaced spark plug on cylinder 5",
    ))
    db_session.flush()

    return {"comp": comp, "events": events, "site": site, "tag": tag, "cat": cat}


# ═══════════════════════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════════════════════

class TestHealth:
    def test_health_endpoint(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data


# ═══════════════════════════════════════════════════════════════════════════
# Compressors
# ═══════════════════════════════════════════════════════════════════════════

class TestCompressorRoutes:
    def test_list_compressors(self, client, seeded_data):
        r = client.get("/api/compressors/")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_compressor_detail(self, client, seeded_data):
        comp_id = seeded_data["comp"].id
        r = client.get(f"/api/compressors/{comp_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == comp_id
        assert "total_events" in data

    def test_get_compressor_not_found(self, client):
        r = client.get("/api/compressors/nonexistent-id")
        assert r.status_code == 404

    def test_get_timeline(self, client, seeded_data):
        comp_id = seeded_data["comp"].id
        r = client.get(f"/api/compressors/{comp_id}/timeline")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_get_issues(self, client, seeded_data):
        comp_id = seeded_data["comp"].id
        r = client.get(f"/api/compressors/{comp_id}/issues")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)


# ═══════════════════════════════════════════════════════════════════════════
# Service Events
# ═══════════════════════════════════════════════════════════════════════════

class TestServiceEventRoutes:
    def test_list_events_paginated(self, client, seeded_data):
        r = client.get("/api/service-events/", params={"page": 1, "page_size": 10})
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert data["page"] == 1

    def test_list_events_with_category_filter(self, client, seeded_data):
        r = client.get("/api/service-events/", params={"event_category": "corrective"})
        assert r.status_code == 200
        items = r.json()["items"]
        assert all(e["event_category"] == "corrective" for e in items)

    def test_list_events_with_search(self, client, seeded_data):
        r = client.get("/api/service-events/", params={"search": "detonation"})
        assert r.status_code == 200

    def test_get_event_detail(self, client, seeded_data):
        event_id = seeded_data["events"][0].id
        r = client.get(f"/api/service-events/{event_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == event_id
        assert "actions" in data
        assert "notes" in data

    def test_get_event_not_found(self, client):
        r = client.get("/api/service-events/nonexistent-id")
        assert r.status_code == 404

    def test_list_categories(self, client, seeded_data):
        r = client.get("/api/service-events/categories")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)


# ═══════════════════════════════════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════════════════════════════════

class TestDashboardRoutes:
    def test_summary(self, client, seeded_data):
        r = client.get("/api/dashboard/summary")
        assert r.status_code == 200
        data = r.json()
        assert "total_events" in data
        assert "total_compressors" in data
        assert "top_issues" in data

    def test_recent_events(self, client, seeded_data):
        r = client.get("/api/dashboard/recent-events", params={"limit": 5})
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_recurring_issues(self, client, seeded_data):
        r = client.get("/api/dashboard/recurring-issues")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)


# ═══════════════════════════════════════════════════════════════════════════
# Recommendations
# ═══════════════════════════════════════════════════════════════════════════

class TestRecommendationRoutes:
    def test_generate_for_event(self, client, seeded_data):
        event_id = seeded_data["events"][0].id
        r = client.post(f"/api/recommendations/generate/{event_id}")
        assert r.status_code == 200
        data = r.json()
        assert "confidence_score" in data
        assert "confidence_label" in data
        assert data["confidence_label"] in ("high", "medium", "low")

    def test_generate_for_nonexistent_event(self, client):
        r = client.post("/api/recommendations/generate/fake-id")
        assert r.status_code == 404

    def test_generate_for_machine(self, client, seeded_data):
        comp_id = seeded_data["comp"].id
        r = client.post(
            "/api/recommendations/generate",
            json={"machine_id": comp_id},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["compressor_id"] == comp_id

    def test_generate_requires_machine_or_event(self, client):
        r = client.post(
            "/api/recommendations/generate",
            json={"event_description": "some issue"},
        )
        assert r.status_code == 400

    def test_list_for_machine(self, client, seeded_data):
        comp_id = seeded_data["comp"].id
        r = client.get(f"/api/recommendations/machine/{comp_id}")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)


# ═══════════════════════════════════════════════════════════════════════════
# Feedback
# ═══════════════════════════════════════════════════════════════════════════

class TestFeedbackRoutes:
    def test_submit_and_retrieve_feedback(self, client, seeded_data):
        event_id = seeded_data["events"][1].id
        r = client.post("/api/feedback/", json={
            "service_event_id": event_id,
            "actual_action_taken": "Tightened fittings, replaced o-ring",
            "issue_resolved": True,
            "technician_name": "John Doe",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["service_event_id"] == event_id
        assert data["issue_resolved"] is True

        r2 = client.get(f"/api/feedback/event/{event_id}")
        assert r2.status_code == 200
        assert r2.json()["service_event_id"] == event_id

    def test_duplicate_feedback_rejected(self, client, seeded_data):
        event_id = seeded_data["events"][2].id
        client.post("/api/feedback/", json={
            "service_event_id": event_id,
            "actual_action_taken": "PM completed",
            "issue_resolved": True,
        })
        r = client.post("/api/feedback/", json={
            "service_event_id": event_id,
            "actual_action_taken": "duplicate",
        })
        assert r.status_code == 409

    def test_feedback_for_nonexistent_event(self, client):
        r = client.post("/api/feedback/", json={
            "service_event_id": "fake-id",
            "actual_action_taken": "nothing",
        })
        assert r.status_code == 404

    def test_list_feedback(self, client, seeded_data):
        r = client.get("/api/feedback/")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
