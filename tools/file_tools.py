from __future__ import annotations
from typing import Any
import pandas as pd
import json
import os

from tools.registry import ToolRegistry

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


@ToolRegistry.register("csv_reader", "Reads a CSV file and returns rows as a list of dictionaries")
def csv_reader(file_name: str, columns: list[str] | None = None) -> dict[str, Any]:
    file_path = _resolve_path(file_name)
    df = pd.read_csv(file_path)
    if columns:
        cols = [c for c in columns if c in df.columns]
        df = df[cols]
    return {"rows": df.to_dict(orient="records"), "column_names": list(df.columns), "row_count": len(df)}


@ToolRegistry.register("excel_parser", "Reads an XLSX file, normalizes headers, and validates rows")
def excel_parser(file_name: str, required_fields: list[str] | None = None) -> dict[str, Any]:
    file_path = _resolve_path(file_name)
    df = pd.read_excel(file_path, engine="openpyxl")
    normalized_cols = {}
    for col in df.columns:
        cleaned = str(col).strip().lower().replace(" ", "_").replace("#", "")
        normalized_cols[col] = cleaned
    df = df.rename(columns=normalized_cols)
    return {"rows": df.to_dict(orient="records"), "column_names": list(df.columns), "row_count": len(df)}


@ToolRegistry.register("schema_validator", "Validates data rows against required fields and schema")
def schema_validator(rows: list[dict], required_fields: list[str], row_id_field: str = "row_number") -> dict[str, Any]:
    if isinstance(rows, str):
        rows = json.loads(rows)
    issues = []
    valid_rows = []
    for i, row in enumerate(rows, 1):
        missing = [f for f in required_fields if not row.get(f) or str(row.get(f)).strip() == "" or pd.isna(row.get(f))]
        record = dict(row)
        if row_id_field == "row_number":
            record["row_number"] = i
        record["valid"] = len(missing) == 0
        if missing:
            record["issues"] = f"Missing required fields: {', '.join(missing)}"
            issues.append(record)
        else:
            valid_rows.append({k: v for k, v in record.items() if k != "valid"})
    return {"valid_rows": valid_rows, "invalid_rows": issues, "valid_count": len(valid_rows), "invalid_count": len(issues)}


@ToolRegistry.register("json_reader", "Reads a JSON file and returns parsed content")
def json_reader(file_name: str) -> dict[str, Any]:
    file_path = _resolve_path(file_name)
    with open(file_path, "r") as f:
        data = json.load(f)
    return {"data": data}


def _resolve_path(file_name: str) -> str:
    if os.path.isabs(file_name):
        return file_name
    return os.path.join(DATA_DIR, file_name)
