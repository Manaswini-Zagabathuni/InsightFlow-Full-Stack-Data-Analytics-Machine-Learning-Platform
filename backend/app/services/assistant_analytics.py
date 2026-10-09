import re
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Dataset, Experiment, Visualization
from app.services.visualization import generate_visualization_data

SUPPORTED_QUESTION_MESSAGE = "I can currently help with dataset summaries, missing values, correlations, basic statistics, saved visualization interpretation, and ML experiment summaries."


class UnsupportedAssistantQuestion(ValueError):
    pass


def classify_question(question: str) -> str:
    text = question.casefold()
    if any(token in text for token in (" sql", "sql ", "select *", "drop table", "insert into", "delete from", "update set")):
        raise UnsupportedAssistantQuestion("SQL generation is not supported. " + SUPPORTED_QUESTION_MESSAGE)
    rules = [
        ("missing_values", ("missing", "null", "empty value", "incomplete")),
        ("correlations", ("correlation", "correlate", "relationship between", "associated with", "move together")),
        ("visualization", ("visualization", "visualisation", "chart", "plot", "graph", "bar", "line", "scatter", "histogram", "box plot", "pie", "donut", "heatmap")),
        ("experiment", ("experiment", "model", "accuracy", "precision", "recall", "f1", "roc", "regression", "classification", "clustering", "shap")),
        ("statistics", ("average", "mean", "median", "standard deviation", "minimum", "maximum", "range", "quartile", "distribution", "outlier", "unique", "statistics")),
        ("dataset_summary", ("summary", "summarize", "summarise", "overview", "dataset", "rows", "columns", "quality")),
    ]
    for intent, phrases in rules:
        if any(phrase in text for phrase in phrases):
            return intent
    raise UnsupportedAssistantQuestion(SUPPORTED_QUESTION_MESSAGE)


def _mentioned_columns(dataset: Dataset, question: str) -> list[str]:
    mentioned = []
    for column in dataset.columns:
        pattern = re.escape(column.name).replace(r"\ ", r"[\s_]+")
        if re.search(rf"(?<!\w){pattern}(?!\w)", question, flags=re.IGNORECASE):
            mentioned.append(column.name)
    return mentioned


def _column_summary(column: Any) -> dict[str, Any]:
    return {
        "name": column.name,
        "type": column.data_type,
        "missing_count": column.missing_count,
        "missing_percentage": column.missing_percentage,
        "unique_count": column.unique_count,
        "statistics": column.statistics,
    }


def _dataset_summary(dataset: Dataset) -> dict[str, Any]:
    types: dict[str, int] = {}
    for column in dataset.columns:
        types[column.data_type] = types.get(column.data_type, 0) + 1
    return {
        "name": dataset.name,
        "rows": dataset.row_count,
        "columns": dataset.column_count,
        "column_type_counts": types,
        "column_names": [column.name for column in dataset.columns[:50]],
        "missing_cells": dataset.missing_cells,
        "duplicate_rows": dataset.duplicate_rows,
        "quality_score": dataset.quality_score,
        "quality_issues": dataset.quality_issues,
    }


def _missing_context(dataset: Dataset, mentioned: list[str]) -> dict[str, Any]:
    columns = [column for column in dataset.columns if column.missing_count > 0]
    if mentioned:
        columns = [column for column in dataset.columns if column.name in mentioned]
    columns.sort(key=lambda column: column.missing_count, reverse=True)
    return {
        "total_missing_cells": dataset.missing_cells,
        "affected_column_count": sum(column.missing_count > 0 for column in dataset.columns),
        "columns": [{"name": column.name, "missing_count": column.missing_count, "missing_percentage": column.missing_percentage} for column in columns[:25]],
    }


def _correlation_context(dataset: Dataset, mentioned: list[str]) -> dict[str, Any]:
    numeric = [column.name for column in dataset.columns if column.data_type == "numeric"]
    selected = [name for name in mentioned if name in numeric]
    if len(selected) < 2:
        selected = numeric
    if len(selected) < 2:
        return {"method": "Pearson", "available": False, "reason": "At least two numeric columns are required."}
    frame = pd.read_csv(dataset.storage_path, usecols=selected, low_memory=False)
    matrix = frame.corr(numeric_only=True)
    pairs = []
    for left_index, left in enumerate(matrix.columns):
        for right in matrix.columns[left_index + 1:]:
            value = matrix.loc[left, right]
            if pd.notna(value):
                pairs.append({"column_a": left, "column_b": right, "correlation": round(float(value), 4), "absolute_strength": round(abs(float(value)), 4)})
    pairs.sort(key=lambda pair: pair["absolute_strength"], reverse=True)
    return {
        "method": "Pearson",
        "available": True,
        "numeric_columns_considered": selected[:50],
        "strongest_pairs": pairs[:20],
        "interpretation_note": "Correlation measures statistical association, not causation.",
    }


def _statistics_context(dataset: Dataset, mentioned: list[str]) -> dict[str, Any]:
    columns = [column for column in dataset.columns if column.name in mentioned] if mentioned else list(dataset.columns)
    return {"columns": [_column_summary(column) for column in columns[:25]], "note": "Statistics are computed by the backend from the uploaded dataset profile."}


def _visualization_digest(data: Any, meta: dict[str, Any], chart_type: str) -> dict[str, Any]:
    digest: dict[str, Any] = {"metadata": meta}
    if chart_type == "heatmap" and isinstance(data, dict):
        cells = []
        seen_pairs: set[frozenset[str]] = set()
        for cell in data.get("cells", []):
            pair = frozenset((str(cell.get("x")), str(cell.get("y"))))
            if cell.get("x") == cell.get("y") or cell.get("value") is None or pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            cells.append(cell)
        cells.sort(key=lambda cell: abs(cell["value"]), reverse=True)
        digest["strongest_cells"] = cells[:8]
        digest["column_count"] = len(data.get("columns", []))
    elif chart_type == "scatter" and isinstance(data, list):
        x_values = [point["x"] for point in data if isinstance(point.get("x"), (int, float))]
        y_values = [point["y"] for point in data if isinstance(point.get("y"), (int, float))]
        digest.update({"point_count": len(data), "x_range": [min(x_values), max(x_values)] if x_values else None, "y_range": [min(y_values), max(y_values)] if y_values else None})
        if len(x_values) == len(y_values) and len(x_values) > 1:
            digest["pearson_correlation"] = round(float(np.corrcoef(x_values, y_values)[0, 1]), 4)
    elif isinstance(data, list):
        digest["record_count"] = len(data)
        digest["leading_aggregates"] = data[:5]
    return digest


def _visualization_context(dataset: Dataset, db: Session) -> dict[str, Any]:
    visualizations = list(db.scalars(select(Visualization).where(Visualization.dataset_id == dataset.id).order_by(Visualization.created_at.desc()).limit(5)).all())
    results = []
    for visualization in visualizations:
        try:
            data, meta = generate_visualization_data(dataset, visualization.chart_type, visualization.x_axis, visualization.y_axis, visualization.group_column)
            digest = _visualization_digest(data, meta, visualization.chart_type)
        except (OSError, ValueError) as exc:
            digest = {"error": str(exc)[:200]}
        results.append({
            "name": visualization.name, "chart_type": visualization.chart_type, "x_axis": visualization.x_axis,
            "y_axis": visualization.y_axis, "group_column": visualization.group_column, "analytical_digest": digest,
        })
    return {"saved_visualization_count": len(visualizations), "visualizations": results}


def _experiment_context(dataset: Dataset, db: Session) -> dict[str, Any]:
    experiments = list(db.scalars(select(Experiment).options(selectinload(Experiment.metrics)).where(Experiment.dataset_id == dataset.id).order_by(Experiment.created_at.desc()).limit(5)).all())
    results = []
    for experiment in experiments:
        model_results = []
        for metric in experiment.metrics:
            scalar_metrics = {key: value for key, value in metric.metrics.items() if isinstance(value, (str, int, float, bool)) or value is None}
            importance = (metric.explainability or {}).get("global_importance", [])[:5]
            model_results.append({"model": metric.model_name, "status": metric.status, "metrics": scalar_metrics, "top_model_derived_features": importance})
        results.append({
            "name": experiment.name, "task": experiment.task_type, "status": experiment.status, "target": experiment.target_column,
            "features": experiment.features, "preprocessing": experiment.preprocessing, "models": model_results,
        })
    return {
        "saved_experiment_count": len(experiments),
        "experiments": results,
        "interpretation_note": "Model-derived importance describes model behavior and is not a causal effect.",
    }


def build_assistant_context(dataset: Dataset, question: str, db: Session) -> tuple[str, dict[str, Any], list[str]]:
    intent = classify_question(question)
    mentioned = _mentioned_columns(dataset, question)
    common = {"dataset": _dataset_summary(dataset)}
    if intent == "dataset_summary":
        analysis, sections = common["dataset"], ["dataset profile", "data quality"]
    elif intent == "missing_values":
        analysis, sections = _missing_context(dataset, mentioned), ["missing-value profile"]
    elif intent == "correlations":
        analysis, sections = _correlation_context(dataset, mentioned), ["Pearson correlations"]
    elif intent == "statistics":
        analysis, sections = _statistics_context(dataset, mentioned), ["column statistics"]
    elif intent == "visualization":
        analysis, sections = _visualization_context(dataset, db), ["saved visualization configurations", "aggregated chart digest"]
    else:
        analysis, sections = _experiment_context(dataset, db), ["saved ML experiments", "persisted metrics", "model-derived importance"]
    return intent, {
        **common,
        "question_intent": intent,
        "mentioned_columns": mentioned,
        "analysis": analysis,
        "guardrails": {
            "raw_rows_included": False,
            "sql_generation_allowed": False,
            "correlation_is_causation": False,
            "instruction": "Use only this structured context. If it is insufficient, say what is missing.",
        },
    }, sections
