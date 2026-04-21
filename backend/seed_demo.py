"""Insert a small synthetic fleet + service history when the Excel seed file is absent.

Used by ``seed_data.py`` so a fresh install (or SQLite dev DB) still has data for
dashboards, health assessment, and recommendation generation.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Compressor, ServiceEvent, ServiceEventAction, Site


def run_demo_seed(db: Session) -> Compressor:
    """Create demo site, compressor, events, and actions. Caller must commit if desired."""
    today = date.today()

    site = Site(
        plant_code="DEMO",
        customer_name="CompressorIQ Demo Plant",
        name="Demo facility",
        region="NA",
    )
    db.add(site)
    db.flush()

    compressor = Compressor(
        unit_id="MC6068-DEMO",
        site_id=site.id,
        compressor_type="Reciprocating",
        manufacturer="Demo OEM",
        model="D-100",
        status="active",
        current_run_hours=42_500.0,
        first_seen_date=today - timedelta(days=400),
        equipment_number="EQ-DEMO-1",
    )
    db.add(compressor)
    db.flush()

    # Varied history: recurrence-friendly keywords, mix of PM and corrective, recent density.
    rows: list[dict] = [
        {
            "days_ago": 8,
            "cat": "corrective",
            "mat": "unscheduled_repair",
            "desc": "Oil leak at discharge valve — replaced packing",
            "notes": "Found oil seeping at discharge valve body. Replaced packing set. "
            "Suction pressure normal after repair. Valve clearance checked OK.",
            "rh": 41_200.0,
            "actions": [("valve service", "discharge valve", "Repacked valve")],
        },
        {
            "days_ago": 14,
            "cat": "corrective",
            "mat": "unscheduled_repair",
            "desc": "High vibration — checked mounts and coupling",
            "notes": "Operator reported vibration on skid. Coupling alignment verified; "
            "tightened anchor bolts. Monitor for recurrence.",
            "rh": 40_900.0,
            "actions": [("inspection", "skid", "Anchor bolt torque check")],
        },
        {
            "days_ago": 22,
            "cat": "preventive_maintenance",
            "mat": "preventive_maintenance",
            "desc": "Scheduled PM — filters and oil sample",
            "notes": "PM per OEM interval. Oil sample sent to lab. Filters replaced.",
            "rh": 40_600.0,
            "actions": [("filter change", "lube oil", "Spin-on filter")],
        },
        {
            "days_ago": 28,
            "cat": "corrective",
            "mat": "unscheduled_repair",
            "desc": "Low suction pressure investigation",
            "notes": "Suction pressure low vs setpoint. Found slight leak on suction line fitting; "
            "re-torqued and soap-tested OK.",
            "rh": 40_400.0,
            "actions": [("leak check", "suction line", "Fitting re-torque")],
        },
        {
            "days_ago": 35,
            "cat": "preventive_maintenance",
            "mat": "preventive_maintenance",
            "desc": "Quarterly inspection",
            "notes": "Visual inspection, belt tension, safety guards OK.",
            "rh": 40_100.0,
            "actions": [("inspection", "general", "Walkdown")],
        },
        {
            "days_ago": 55,
            "cat": "corrective",
            "mat": "unscheduled_repair",
            "desc": "Valve noise — adjusted lash",
            "notes": "Ticking noise at idle. Valve lash adjusted per spec. "
            "Re-test hot — noise reduced.",
            "rh": 39_800.0,
            "actions": [("valve adjustment", "cylinder head", "Lash set to spec")],
        },
        {
            "days_ago": 70,
            "cat": "preventive_maintenance",
            "mat": "preventive_maintenance",
            "desc": "Oil change",
            "notes": "Drain and fill with synthetic. No metal in oil.",
            "rh": 39_400.0,
            "actions": [("oil change", "lube system", "5 gal refill")],
        },
        {
            "days_ago": 95,
            "cat": "corrective",
            "mat": "unscheduled_repair",
            "desc": "Coolant temperature high",
            "notes": "Engine coolant temp high alarm. Thermostat replaced; "
            "coolant flushed. Temperature stable.",
            "rh": 39_000.0,
            "actions": [("cooling system", "thermostat", "Replaced t-stat")],
        },
        {
            "days_ago": 120,
            "cat": "preventive_maintenance",
            "mat": "preventive_maintenance",
            "desc": "Annual PM",
            "notes": "Spark plugs, belts, hoses inspection. No defects noted.",
            "rh": 38_500.0,
            "actions": [("spark plug", "ignition", "Set of 6 replaced")],
        },
        {
            "days_ago": 150,
            "cat": "corrective",
            "mat": "unscheduled_repair",
            "desc": "Fuel BTU curve check",
            "notes": "Rough running under load. Fuel quality OK; BTU curve adjusted. "
            "Detonation not observed after tune.",
            "rh": 38_000.0,
            "actions": [("fuel system", "carburetion", "BTU curve adjustment")],
        },
        {
            "days_ago": 200,
            "cat": "preventive_maintenance",
            "mat": "preventive_maintenance",
            "desc": "Preservation PM",
            "notes": "Standard preservation checklist completed.",
            "rh": 37_200.0,
            "actions": [("inspection", "general", "Preservation checklist")],
        },
        {
            "days_ago": 260,
            "cat": "corrective",
            "mat": "unscheduled_repair",
            "desc": "Discharge pressure fluctuation",
            "notes": "Discharge pressure unstable. Found leaking relief valve seat; "
            "replaced valve cartridge.",
            "rh": 36_500.0,
            "actions": [("pressure control", "relief valve", "Cartridge replaced")],
        },
    ]

    events: list[ServiceEvent] = []
    for i, r in enumerate(rows, start=1):
        ev_date = today - timedelta(days=int(r["days_ago"]))
        ev = ServiceEvent(
            compressor_id=compressor.id,
            order_number=f"DEMO-ORD-{ev_date.isoformat()}-{i:03d}",
            order_description=r["desc"],
            event_date=ev_date,
            event_category=r["cat"],
            maintenance_activity_type=r["mat"],
            maintenance_activity_type_raw=r["mat"].replace("_", " "),
            technician_notes_raw=r["notes"],
            run_hours_at_event=r["rh"],
            plant_code="DEMO",
            customer_name="CompressorIQ Demo Plant",
            order_type="WO",
            order_status="closed",
            user_status="complete",
        )
        db.add(ev)
        db.flush()
        for raw, comp, desc in r["actions"]:
            db.add(
                ServiceEventAction(
                    service_event_id=ev.id,
                    action_type_raw=raw,
                    component=comp,
                    description=desc,
                )
            )
        events.append(ev)

    db.flush()
    return compressor
