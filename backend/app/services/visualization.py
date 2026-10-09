from typing import Any

import numpy as np
import pandas as pd

from app.models import Dataset

NUMERIC = "numeric"


def validate_configuration(dataset: Dataset, chart_type: str, x_axis: str | None, y_axis: str | None, group_column: str | None) -> dict[str, str]:
    columns = {column.name: column.data_type for column in dataset.columns}
    for selected in (x_axis, y_axis, group_column):
        if selected and selected not in columns:
            raise ValueError(f"Unknown dataset column: {selected}")
    if group_column and group_column in {x_axis, y_axis}:
        raise ValueError("Group/color column must differ from the selected axes")
    if chart_type in {"line", "scatter"} and x_axis == y_axis:
        raise ValueError("X-axis and Y-axis must use different columns")

    if chart_type in {"bar", "line", "scatter", "histogram", "pie"} and not x_axis:
        raise ValueError(f"{chart_type.title()} charts require an X-axis column")
    if chart_type in {"line", "scatter", "box"} and not y_axis:
        raise ValueError(f"{chart_type.title()} charts require a Y-axis column")
    if chart_type == "bar" and y_axis and columns[y_axis] != NUMERIC:
        raise ValueError("Bar chart Y-axis must be numeric")
    if chart_type in {"line", "scatter", "box"} and columns.get(y_axis or "") != NUMERIC:
        raise ValueError(f"{chart_type.title()} chart Y-axis must be numeric")
    if chart_type in {"scatter", "histogram"} and columns.get(x_axis or "") != NUMERIC:
        raise ValueError(f"{chart_type.title()} chart X-axis must be numeric")
    if chart_type == "pie" and y_axis and columns[y_axis] != NUMERIC:
        raise ValueError("Pie chart Y-axis must be numeric when supplied")
    if chart_type == "heatmap" and sum(kind == NUMERIC for kind in columns.values()) < 2:
        raise ValueError("Correlation heatmap requires at least two numeric columns")
    return columns


def _native(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def _series_table(frame: pd.DataFrame, x: str, y: str | None, group: str | None, aggregation: str) -> tuple[list[dict], list[str]]:
    dimensions = [x] + ([group] if group else [])
    if y:
        grouped = frame.dropna(subset=[x, y]).groupby(dimensions, dropna=False)[y].agg(aggregation).reset_index(name="value")
    else:
        grouped = frame.dropna(subset=[x]).groupby(dimensions, dropna=False).size().reset_index(name="value")
    if group:
        top_groups = grouped.groupby(group)["value"].sum().nlargest(10).index
        grouped = grouped[grouped[group].isin(top_groups)]
        pivoted = grouped.pivot_table(index=x, columns=group, values="value", aggfunc="first").reset_index().head(150)
        series = [str(column) for column in pivoted.columns if column != x]
        records = []
        for record in pivoted.to_dict(orient="records"):
            records.append({"label": str(record.pop(x)), **{str(key): _native(value) for key, value in record.items()}})
        return records, series
    grouped = grouped.sort_values(x, kind="mergesort").head(250)
    return [{"label": str(row[x]), "value": _native(row["value"])} for _, row in grouped.iterrows()], ["value"]


def generate_visualization_data(dataset: Dataset, chart_type: str, x_axis: str | None, y_axis: str | None, group_column: str | None) -> tuple[Any, dict[str, Any]]:
    column_types = validate_configuration(dataset, chart_type, x_axis, y_axis, group_column)
    if chart_type == "heatmap":
        numeric_columns = [name for name, kind in column_types.items() if kind == NUMERIC]
        frame = pd.read_csv(dataset.storage_path, usecols=numeric_columns, low_memory=False)
        correlation = frame.corr(numeric_only=True).round(4)
        cells = [{"x": x, "y": y, "value": round(float(correlation.loc[y, x]), 4) if pd.notna(correlation.loc[y, x]) else None} for y in correlation.index for x in correlation.columns]
        return {"columns": list(correlation.columns), "cells": cells}, {"method": "pearson", "row_limit": None}

    selected = list(dict.fromkeys(column for column in [x_axis, y_axis, group_column] if column))
    frame = pd.read_csv(dataset.storage_path, usecols=selected, low_memory=False)

    if chart_type == "bar":
        data, series = _series_table(frame, x_axis, y_axis, group_column, "mean")
        return data, {"series": series, "aggregation": "mean" if y_axis else "count", "point_limit": 250}
    if chart_type == "line":
        data, series = _series_table(frame, x_axis, y_axis, group_column, "mean")
        return data, {"series": series, "aggregation": "mean", "point_limit": 250}
    if chart_type == "scatter":
        clean = frame.dropna(subset=[x_axis, y_axis]).head(1000)
        data = [{"x": _native(row[x_axis]), "y": _native(row[y_axis]), "group": str(row[group_column]) if group_column and pd.notna(row[group_column]) else "All"} for _, row in clean.iterrows()]
        groups = list(dict.fromkeys(point["group"] for point in data))[:20]
        return data, {"groups": groups, "point_limit": 1000}
    if chart_type == "histogram":
        clean = frame.dropna(subset=[x_axis])
        values = clean[x_axis].astype(float)
        if values.empty:
            return [], {"series": ["value"], "bins": 0}
        _, edges = np.histogram(values, bins=min(20, max(5, int(np.sqrt(len(values))))))
        groups = [("value", clean)] if not group_column else [(str(name), part) for name, part in clean.groupby(group_column, dropna=False)][:10]
        records: list[dict[str, Any]] = []
        for index in range(len(edges) - 1):
            record: dict[str, Any] = {"label": f"{edges[index]:.3g}–{edges[index + 1]:.3g}"}
            for name, part in groups:
                counts, _ = np.histogram(part[x_axis].astype(float), bins=edges)
                record[name] = int(counts[index])
            records.append(record)
        return records, {"series": [name for name, _ in groups], "bins": len(edges) - 1}
    if chart_type == "box":
        grouping = group_column or x_axis
        groups = [("All values", frame)] if not grouping else list(frame.groupby(grouping, dropna=False))[:20]
        results = []
        for label, part in groups:
            values = part[y_axis].dropna().astype(float)
            if values.empty:
                continue
            q1, median, q3 = values.quantile([0.25, 0.5, 0.75])
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            whiskers = values[(values >= lower) & (values <= upper)]
            outliers = values[(values < lower) | (values > upper)].head(50).tolist()
            results.append({"label": str(label), "minimum": float(whiskers.min()), "q1": float(q1), "median": float(median), "q3": float(q3), "maximum": float(whiskers.max()), "outliers": [float(value) for value in outliers]})
        return results, {"grouped_by": grouping, "outliers_capped_at": 50}
    if chart_type == "pie":
        dimensions = [x_axis] + ([group_column] if group_column else [])
        grouped = frame.dropna(subset=[x_axis]).groupby(dimensions, dropna=False)[y_axis].sum() if y_axis else frame.dropna(subset=[x_axis]).groupby(dimensions, dropna=False).size()
        grouped = grouped.sort_values(ascending=False)
        records = []
        for key, value in grouped.head(12).items():
            parts = key if isinstance(key, tuple) else (key,)
            records.append({"name": " · ".join(str(part) for part in parts), "value": float(value)})
        remainder = grouped.iloc[12:].sum()
        if remainder:
            records.append({"name": "Other", "value": float(remainder)})
        return records, {"aggregation": "sum" if y_axis else "count", "slice_limit": 12}
    raise ValueError("Unsupported chart type")
