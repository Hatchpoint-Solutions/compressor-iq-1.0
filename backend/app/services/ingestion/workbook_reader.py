"""Stage 2: Workbook / CSV reader.

Opens each file, enumerates sheets, reads column headers and raw rows.
Returns dataclass representations for downstream processing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class SheetData:
    sheet_name: str
    sheet_index: int
    column_names: list[str]
    rows: list[dict[str, Any]]

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def column_count(self) -> int:
        return len(self.column_names)


@dataclass
class WorkbookData:
    file_path: str
    file_type: str
    sheets: list[SheetData] = field(default_factory=list)


def read_workbook(file_path: str, file_type: str) -> WorkbookData:
    """Read all sheets from a workbook or a single CSV into ``WorkbookData``."""
    wb = WorkbookData(file_path=file_path, file_type=file_type)

    if file_type in ("csv", "tsv"):
        sep = "\t" if file_type == "tsv" else ","
        df = pd.read_csv(file_path, sep=sep, dtype=str, keep_default_na=False)
        wb.sheets.append(_df_to_sheet(df, sheet_name="csv", sheet_index=0))
    else:
        xls = pd.ExcelFile(file_path)
        for idx, name in enumerate(xls.sheet_names):
            df = pd.read_excel(xls, sheet_name=name, dtype=str, keep_default_na=False)
            wb.sheets.append(_df_to_sheet(df, sheet_name=name, sheet_index=idx))

    return wb


def _df_to_sheet(df: pd.DataFrame, sheet_name: str, sheet_index: int) -> SheetData:
    columns = [str(c).strip() for c in df.columns.tolist()]
    rows: list[dict[str, Any]] = []

    for row_idx, (_, row) in enumerate(df.iterrows(), start=1):
        row_dict: dict[str, Any] = {}
        for col in columns:
            val = row.get(col)
            if pd.isna(val) or str(val).strip() in ("", "nan", "NaN", "None", "NaT"):
                row_dict[col] = None
            else:
                row_dict[col] = str(val).strip()
        rows.append(row_dict)

    return SheetData(
        sheet_name=sheet_name,
        sheet_index=sheet_index,
        column_names=columns,
        rows=rows,
    )
