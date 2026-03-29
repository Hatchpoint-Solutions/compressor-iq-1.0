"""Tests for the validation module."""

import pytest

from app.services.ingestion.validator import validate_row


def _base_row(**overrides):
    """Return a valid base row dict, with optional overrides."""
    row = {
        "order_and_description": "4113904 - MC6068 - JANUARY 2020 CALLOUTS",
        "plant_code": "1031",
        "customer_name": "EOG Resources Inc",
        "equipment_number": "500021946",
        "order_type": "ZNS1",
        "technician_notes": "Some notes here",
        "order_status": "TECO",
        "user_status": "SMOK",
        "maintenance_activity_type_raw": "ZUR - Unscheduled Repair -Mechanical",
        "order_cost": "1500",
        "run_hours": "18671",
        "reading_date": "2020-01-03",
    }
    row.update(overrides)
    return row


class TestValidateRow:
    def test_valid_row(self):
        result = validate_row(_base_row(), 1)
        assert result.is_valid
        assert not result.has_errors

    def test_missing_order_description(self):
        result = validate_row(_base_row(order_and_description=""), 1)
        assert not result.is_valid
        assert any(i.issue_type == "missing_order_description" for i in result.issues)

    def test_missing_machine_id(self):
        result = validate_row(_base_row(order_and_description="4113904"), 1)
        assert any(i.issue_type == "missing_machine_id" for i in result.issues)

    def test_missing_date_is_warning(self):
        result = validate_row(_base_row(reading_date=None), 1)
        assert result.is_valid  # warnings don't block
        assert any(i.issue_type == "missing_reading_date" for i in result.issues)

    def test_empty_notes_is_info(self):
        result = validate_row(_base_row(technician_notes=""), 1)
        assert result.is_valid
        assert any(i.issue_type == "empty_technician_notes" for i in result.issues)

    def test_negative_cost_warning(self):
        result = validate_row(_base_row(order_cost="-100"), 1)
        assert result.is_valid
        assert any(i.issue_type == "negative_order_cost" for i in result.issues)

    def test_negative_run_hours_error(self):
        result = validate_row(_base_row(run_hours="-500"), 1)
        assert not result.is_valid
        assert any(i.issue_type == "negative_run_hours" for i in result.issues)

    def test_metadata_plant_code_error(self):
        result = validate_row(
            _base_row(plant_code="Applied filters:\nSome very long metadata text that is not a plant code"),
            1,
        )
        assert not result.is_valid
        assert any(i.issue_type == "invalid_plant_code" for i in result.issues)
