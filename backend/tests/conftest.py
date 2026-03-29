"""Shared test fixtures."""

import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base


@pytest.fixture(scope="session")
def engine():
    """Create an in-memory SQLite engine for tests."""
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture
def db(engine):
    """Yield a transactional session that rolls back after each test."""
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def sample_xlsx(tmp_path):
    """Create a minimal Excel file mimicking the MC6068 data structure."""
    import pandas as pd

    data = {
        "Plant": ["1031", "1032", "1031"],
        "Order & Description": [
            "4113904 - MC6068 - JANUARY 2020 CALLOUTS",
            "4117446 - MC6068 - CORRECTIVE - 02/09/2020",
            "4119330 - MC6068 - Maintenance - Annual/Semi",
        ],
        "Customer Name": ["EOG Resources Inc", "ConocoPhillips Co", "EOG Resources Inc"],
        "Equipment": [500021946, 500021946, 500021946],
        "Type": ["ZNS1", "ZNS1", "ZNS6"],
        "Order Review Comments": [
            "* 01/03/2020 09:20:09 MST Meagan Burnett (MBURNETT)\n* 1/2/2020 @ 18,671 hrs - Micah - BLEW OUT AIR FILTERS",
            "* 02/11/2020 15:08:14 MST Gail Carter (GCARTER)\n* 2/9/2020 - Ji - 19,558 hrs - unit down on #5 cylinder detonation. I pulled the #5 hole spark plug and gapped and installed a new plug",
            "* 04/23/2020 14:41:25 MST Meagan Burnett (MBURNETT)\n* Matt and Mark completed 4/23/2020 @ 21,288 hrs along with PM1",
        ],
        "Order Status": ["TECO", "TECO", "TECO"],
        "User Status": ["SMOK", "SMOK", "SMOK"],
        "Maintenance Activity Type": [
            "ZUR - Unscheduled Repair -Mechanical",
            "ZUR - Unscheduled Repair -Mechanical",
            "ZPM - Preventative Maintenance",
        ],
        "Order Cost": [None, 1500.50, 2200.00],
        "Order Revenue": [None, 0, 0],
        "Currency": ["USD", "USD", "USD"],
        "GM %": [None, None, None],
        "Days to Inv.": [None, None, None],
        "Category": ["No Group", "No Group", "No Group"],
        "Sub-Orders": [None, None, None],
        "Lead Order": [None, None, None],
        "Run Hours": [None, 19558, 21288],
        "Reading Date": [None, "2020-02-09", "2020-04-23"],
    }

    filepath = str(tmp_path / "test_maintenance.xlsx")
    pd.DataFrame(data).to_excel(filepath, index=False, sheet_name="Export")
    return filepath
