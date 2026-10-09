from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def json_value(value: Any) -> Any:
    if value is None or (isinstance(value, (float, np.floating)) and np.isnan(value)):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def profile_csv(path: str | Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    frame = pd.read_csv(path, low_memory=False)
    if len(frame.columns) == 0:
        raise ValueError("CSV must contain a header row")
    if frame.empty:
        raise ValueError("CSV must contain at least one data row")

    rows = len(frame)
    total_cells = max(frame.size, 1)
    missing_cells = int(frame.isna().sum().sum())
    duplicate_rows = int(frame.duplicated().sum())
    constant_columns: list[str] = []
    high_cardinality_columns: list[str] = []
    outlier_columns: list[str] = []
    column_profiles: list[dict[str, Any]] = []

    for position, name in enumerate(frame.columns):
        series = frame[name]
        clean = series.dropna()
        unique_count = int(series.nunique(dropna=True))
        missing_count = int(series.isna().sum())
        missing_percentage = round(float(series.isna().mean() * 100), 2)
        statistics: dict[str, Any] = {}

        if unique_count <= 1:
            constant_columns.append(str(name))

        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
            data_type = "numeric"
            q1 = clean.quantile(0.25) if len(clean) else None
            q3 = clean.quantile(0.75) if len(clean) else None
            iqr = (q3 - q1) if q1 is not None and q3 is not None else 0
            outliers = int(((clean < q1 - 1.5 * iqr) | (clean > q3 + 1.5 * iqr)).sum()) if iqr else 0
            if outliers:
                outlier_columns.append(str(name))
            statistics = {
                "count": int(clean.count()),
                "mean": json_value(clean.mean()) if len(clean) else None,
                "median": json_value(clean.median()) if len(clean) else None,
                "standard_deviation": json_value(clean.std()) if len(clean) > 1 else None,
                "minimum": json_value(clean.min()) if len(clean) else None,
                "q1": json_value(q1),
                "q3": json_value(q3),
                "maximum": json_value(clean.max()) if len(clean) else None,
                "outlier_count": outliers,
            }
        else:
            sample = clean.astype(str).head(200)
            date_pattern = r"(?:\d{4}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}:\d{2})"
            looks_like_dates = bool(len(sample)) and float(sample.str.contains(date_pattern, regex=True).mean()) >= 0.9
            parsed = pd.to_datetime(sample, errors="coerce", format="mixed") if looks_like_dates else pd.Series(dtype="datetime64[ns]")
            if looks_like_dates and float(parsed.notna().mean()) >= 0.9:
                data_type = "datetime"
                all_dates = pd.to_datetime(series, errors="coerce")
                statistics = {"minimum": json_value(all_dates.min()), "maximum": json_value(all_dates.max())}
            else:
                data_type = "categorical"
                counts = series.fillna("(missing)").astype(str).value_counts().head(10)
                statistics = {"top_values": [{"value": str(value), "count": int(count)} for value, count in counts.items()]}
                if rows > 0 and unique_count > 20 and unique_count / rows > 0.8:
                    high_cardinality_columns.append(str(name))

        column_profiles.append({
            "name": str(name),
            "position": position,
            "data_type": data_type,
            "pandas_dtype": str(series.dtype),
            "missing_count": missing_count,
            "missing_percentage": missing_percentage,
            "unique_count": unique_count,
            "statistics": statistics,
        })

    missing_penalty = min(40.0, missing_cells / total_cells * 40.0)
    duplicate_penalty = min(25.0, duplicate_rows / max(rows, 1) * 25.0)
    constant_penalty = min(15.0, len(constant_columns) * 5.0)
    cardinality_penalty = min(10.0, len(high_cardinality_columns) * 2.0)
    outlier_penalty = min(10.0, len(outlier_columns) * 2.5)
    score = round(max(0.0, 100.0 - missing_penalty - duplicate_penalty - constant_penalty - cardinality_penalty - outlier_penalty), 1)

    issues: list[str] = []
    missing_columns = int((frame.isna().sum() > 0).sum())
    if missing_columns:
        issues.append(f"{missing_columns} column(s) contain missing values ({missing_cells} cells)")
    if duplicate_rows:
        issues.append(f"{duplicate_rows} duplicate row(s) detected")
    if constant_columns:
        issues.append(f"Constant columns: {', '.join(constant_columns)}")
    if high_cardinality_columns:
        issues.append(f"High-cardinality columns: {', '.join(high_cardinality_columns)}")
    if outlier_columns:
        issues.append(f"Potential IQR outliers in: {', '.join(outlier_columns)}")
    if not issues:
        issues.append("No material data-quality issues detected")

    return {
        "row_count": rows,
        "column_count": len(frame.columns),
        "memory_bytes": int(frame.memory_usage(deep=True).sum()),
        "missing_cells": missing_cells,
        "duplicate_rows": duplicate_rows,
        "quality_score": score,
        "quality_issues": issues,
    }, column_profiles
