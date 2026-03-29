"""Tests for the normalizer module."""

from datetime import date

import pytest

from app.services.ingestion.normalizer import (
    classify_event_category,
    clean_technician_notes,
    estimate_event_date,
    extract_actions_from_notes,
    infer_issue_category,
    normalize_activity_type,
    normalize_date,
    normalize_equipment_number,
    normalize_float,
    normalize_plant_code,
    normalize_unit_id,
    parse_order_and_description,
)


class TestNormalizeUnitId:
    def test_standard(self):
        r = normalize_unit_id("MC6068")
        assert r.normalized == "MC6068"

    def test_with_suffix(self):
        r = normalize_unit_id("MC6068-CORRECTIVE")
        assert r.normalized == "MC6068"

    def test_whitespace(self):
        r = normalize_unit_id("  MC6068 ")
        assert r.normalized == "MC6068"

    def test_ef_prefix(self):
        r = normalize_unit_id("EF6068")
        assert r.normalized == "MC6068"

    def test_lowercase(self):
        r = normalize_unit_id("mc6068")
        assert r.normalized == "MC6068"

    def test_empty(self):
        r = normalize_unit_id("")
        assert r.normalized == "UNKNOWN"
        assert len(r.issues) > 0

    def test_none(self):
        r = normalize_unit_id(None)
        assert r.normalized == "UNKNOWN"

    def test_non_standard(self):
        r = normalize_unit_id("COMP101")
        assert r.normalized == "COMP101"
        assert len(r.issues) > 0


class TestParseOrderAndDescription:
    def test_standard(self):
        num, unit, desc = parse_order_and_description(
            "4113904 - MC6068 - JANUARY 2020 CALLOUTS"
        )
        assert num == "4113904"
        assert unit == "MC6068"
        assert desc == "JANUARY 2020 CALLOUTS"

    def test_two_parts(self):
        num, unit, desc = parse_order_and_description("4113904 - MC6068")
        assert num == "4113904"
        assert unit == "MC6068"
        assert desc == ""

    def test_empty(self):
        assert parse_order_and_description("") == ("", "", "")
        assert parse_order_and_description(None) == ("", "", "")


class TestNormalizeDate:
    def test_datetime_object(self):
        from datetime import datetime
        r = normalize_date(datetime(2023, 5, 4))
        assert r.normalized == date(2023, 5, 4)

    def test_iso_string(self):
        r = normalize_date("2023-05-04")
        assert r.normalized == date(2023, 5, 4)

    def test_us_format(self):
        r = normalize_date("05/04/2023")
        assert r.normalized == date(2023, 5, 4)

    def test_invalid(self):
        r = normalize_date("not-a-date")
        assert r.normalized is None
        assert len(r.issues) > 0

    def test_none(self):
        r = normalize_date(None)
        assert r.normalized is None


class TestEstimateEventDate:
    def test_from_description(self):
        r = estimate_event_date("CORRECTIVE - 02/09/2020", None)
        assert r.normalized == date(2020, 2, 9)

    def test_from_notes(self):
        r = estimate_event_date(None, "* 3/10/2020 @ 20,261 hrs - Ji - called in")
        assert r.normalized == date(2020, 3, 10)

    def test_no_date(self):
        r = estimate_event_date("CALLOUTS", "no date here")
        assert r.normalized is None


class TestNormalizeFloat:
    def test_normal(self):
        r = normalize_float("1500.50")
        assert r.normalized == 1500.50

    def test_with_commas(self):
        r = normalize_float("19,558")
        assert r.normalized == 19558.0

    def test_negative_cost(self):
        r = normalize_float("-252.35", "order_cost")
        assert r.normalized == -252.35
        assert any("Negative" in i for i in r.issues)

    def test_none(self):
        r = normalize_float(None)
        assert r.normalized is None


class TestClassifyEventCategory:
    def test_corrective(self):
        assert classify_event_category("JANUARY 2020 CALLOUTS") == "corrective"

    def test_preventive(self):
        assert classify_event_category("Maintenance - Annual/Semi") == "preventive_maintenance"

    def test_emissions(self):
        assert classify_event_category("Emissions 90 Day") == "emissions_inspection"

    def test_other(self):
        assert classify_event_category("Something Unknown") == "other"


class TestNormalizeActivityType:
    def test_zur(self):
        r = normalize_activity_type("ZUR - Unscheduled Repair -Mechanical")
        assert r.normalized == "unscheduled_repair"

    def test_zpm(self):
        r = normalize_activity_type("ZPM - Preventative Maintenance")
        assert r.normalized == "preventive_maintenance"

    def test_unknown(self):
        r = normalize_activity_type("ZXX - Something New")
        assert r.normalized == "ZXX - Something New"
        assert len(r.issues) > 0


class TestInferIssueCategory:
    def test_detonation(self):
        result = infer_issue_category("unit down on #5 cylinder detonation", "")
        assert result is not None
        assert result[0] == "detonation"

    def test_leak(self):
        result = infer_issue_category("found oil leak on hose fitting", "")
        assert result is not None
        assert result[0] == "leak"

    def test_no_match(self):
        result = infer_issue_category("everything looks good", "routine check")
        assert result is None


class TestExtractActions:
    def test_extract_from_notes(self):
        notes = (
            "* 01/03/2020 09:20:09 MST Meagan Burnett (MBURNETT)\n"
            "* 1/2/2020 @ 18,671 hrs - Micah - BLEW OUT AIR FILTERS AND LOOKED OVER UNIT.\n"
            "* 1/3/2020 @ 18,694 hrs - Micah - REPLACED AIR FILTERS."
        )
        actions = extract_actions_from_notes(notes)
        assert len(actions) >= 2
        assert any(a["action_type_raw"] == "cleaned" for a in actions)
        assert any(a["action_type_raw"] == "replaced" for a in actions)

    def test_empty_notes(self):
        assert extract_actions_from_notes("") == []
        assert extract_actions_from_notes(None) == []


class TestNormalizePlantCode:
    def test_valid(self):
        r = normalize_plant_code("1031")
        assert r.normalized == "1031"

    def test_invalid_metadata(self):
        r = normalize_plant_code("Applied filters:\nSome long metadata text")
        assert r.normalized is None
        assert len(r.issues) > 0


class TestCleanTechnicianNotes:
    def test_removes_timestamps(self):
        raw = (
            "* 01/03/2020 09:20:09 MST Meagan Burnett (MBURNETT)\n"
            "* Micah took out parts on PRF 14863\n"
            "* 1/2/2020 @ 18,671 hrs - Micah - BLEW OUT AIR FILTERS"
        )
        r = clean_technician_notes(raw)
        assert r.normalized is not None
        assert "MBURNETT" not in r.normalized
        assert "BLEW OUT AIR FILTERS" in r.normalized

    def test_empty(self):
        r = clean_technician_notes("")
        assert r.normalized is None
