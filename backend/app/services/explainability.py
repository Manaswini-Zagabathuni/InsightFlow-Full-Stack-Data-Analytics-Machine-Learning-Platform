from typing import Any

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.pipeline import Pipeline

TREE_MODELS = {
    "decision_tree", "random_forest", "gradient_boosting", "xgboost",
    "random_forest_regressor", "gradient_boosting_regressor", "xgboost_regressor",
}
LINEAR_MODELS = {"logistic_regression", "linear_regression", "ridge"}

INTERPRETATION = {
    "importance_kind": "model-derived",
    "importance_note": "Importance describes how this fitted model used the selected features on held-out data.",
    "correlation_note": "Statistical correlation measures how variables move together. It is separate from model importance and does not establish why an outcome occurred.",
    "causal_note": "These explanations are not causal claims. Establishing causation requires an appropriate experimental or causal-inference design.",
}


def _native(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if pd.isna(value):
        return None
    return value


def _feature_map(preprocessor: Any) -> list[str]:
    names: list[str] = []
    for transformer_name, transformer, columns in preprocessor.transformers_:
        if transformer_name == "remainder" or transformer == "drop":
            continue
        column_names = [str(column) for column in columns]
        if transformer_name == "numeric":
            names.extend(column_names)
        elif transformer_name == "categorical":
            encoder = transformer.named_steps["encoder"]
            for column, categories in zip(column_names, encoder.categories_):
                names.extend([column] * len(categories))
    return names


def _aggregate(feature_map: list[str], global_values: np.ndarray, signed_values: np.ndarray, individual_values: np.ndarray | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    order = list(dict.fromkeys(feature_map))
    global_rows = []
    individual_rows = []
    total = float(np.sum(global_values)) or 1.0
    for feature in order:
        indices = [index for index, mapped in enumerate(feature_map) if mapped == feature]
        importance = float(np.sum(global_values[indices]))
        global_rows.append({
            "feature": feature,
            "importance": round(importance, 8),
            "share": round(importance / total, 6),
            "mean_signed_contribution": round(float(np.sum(signed_values[indices])), 8),
        })
        if individual_values is not None:
            contribution = float(np.sum(individual_values[indices]))
            individual_rows.append({
                "feature": feature,
                "contribution": round(contribution, 8),
                "direction": "increases model output" if contribution > 0 else "decreases model output" if contribution < 0 else "neutral",
            })
    global_rows.sort(key=lambda row: row["importance"], reverse=True)
    individual_rows.sort(key=lambda row: abs(row["contribution"]), reverse=True)
    return global_rows, individual_rows


def _shap_values(model: Any, model_id: str, train_values: np.ndarray, evaluation_values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, Any, str]:
    import shap

    if model_id in TREE_MODELS:
        explanation = shap.TreeExplainer(model)(evaluation_values)
        method = "Tree SHAP"
    elif model_id in LINEAR_MODELS:
        explanation = shap.LinearExplainer(model, train_values)(evaluation_values)
        method = "Linear SHAP"
    else:
        raise ValueError("No reliable SHAP explainer is configured for this model")

    values = np.asarray(explanation.values)
    predictions = model.predict(evaluation_values)
    output_index = 0
    if values.ndim == 3:
        classes = list(getattr(model, "classes_", []))
        if classes:
            output_index = classes.index(predictions[0])
        global_values = np.mean(np.abs(values), axis=(0, 2))
        signed_values = np.mean(values, axis=(0, 2))
        individual_values = values[0, :, output_index]
    elif values.ndim == 2:
        global_values = np.mean(np.abs(values), axis=0)
        signed_values = np.mean(values, axis=0)
        individual_values = values[0]
    else:
        raise ValueError("Unexpected SHAP output shape")

    base = np.asarray(explanation.base_values)
    if base.ndim >= 2:
        baseline = base[0, output_index]
    elif base.ndim == 1:
        baseline = base[output_index] if len(base) > 1 else base[0]
    else:
        baseline = base.item()
    return global_values, signed_values, individual_values, _native(baseline), method


def _fallback_permutation(pipeline: Pipeline, x_test: pd.DataFrame, y_test: pd.Series, error: Exception) -> dict[str, Any]:
    result = permutation_importance(pipeline, x_test, y_test, n_repeats=5, random_state=42, n_jobs=1)
    values = np.maximum(result.importances_mean, 0)
    total = float(values.sum()) or 1.0
    rows = [
        {"feature": feature, "importance": round(float(value), 8), "share": round(float(value / total), 6), "mean_signed_contribution": None}
        for feature, value in zip(x_test.columns, values)
    ]
    rows.sort(key=lambda row: row["importance"], reverse=True)
    return {
        "status": "partial",
        "method": "Permutation importance fallback",
        "method_detail": "Performance decrease after shuffling one original feature on the held-out partition.",
        "global_importance": rows,
        "individual": None,
        "individual_unavailable_reason": "Individual contributions require a compatible SHAP explainer.",
        "fallback_reason": str(error)[:300],
        "sample_rows": len(x_test),
        "interpretation": INTERPRETATION,
    }


def explain_supervised_model(pipeline: Pipeline, model_id: str, x_train: pd.DataFrame, x_test: pd.DataFrame, y_test: pd.Series) -> dict[str, Any]:
    evaluation = x_test.head(100)
    training = x_train.head(200)
    preprocessor = pipeline.named_steps["preprocessing"]
    model = pipeline.named_steps["model"]
    transformed_train = np.asarray(preprocessor.transform(training))
    transformed_evaluation = np.asarray(preprocessor.transform(evaluation))
    feature_map = _feature_map(preprocessor)
    try:
        global_values, signed_values, individual_values, baseline, method = _shap_values(model, model_id, transformed_train, transformed_evaluation)
        if len(feature_map) != len(global_values):
            raise ValueError("Transformed feature mapping did not match SHAP output")
        global_rows, contribution_rows = _aggregate(feature_map, global_values, signed_values, individual_values)
        prediction = pipeline.predict(evaluation.iloc[[0]])[0]
        actual = y_test.loc[evaluation.index[0]]
        input_values = [{"feature": feature, "value": _native(evaluation.iloc[0][feature])} for feature in evaluation.columns]
        return {
            "status": "available",
            "method": method,
            "method_detail": "SHAP attributes changes in this fitted model's output relative to its baseline.",
            "global_importance": global_rows,
            "sample_rows": len(evaluation),
            "individual": {
                "prediction": _native(prediction),
                "actual": _native(actual),
                "baseline": baseline,
                "contributions": contribution_rows,
                "input": input_values,
                "output_note": "Contribution values use the model's internal output scale and should be compared by direction and relative magnitude.",
            },
            "interpretation": INTERPRETATION,
        }
    except Exception as exc:
        return _fallback_permutation(pipeline, evaluation, y_test.loc[evaluation.index], exc)


def unsupported_clustering_explanation() -> dict[str, Any]:
    return {
        "status": "unavailable",
        "method": None,
        "reason": "SHAP explanations are not generated for unsupervised cluster assignments because there is no supervised target output to explain reliably.",
        "global_importance": [],
        "individual": None,
        "interpretation": INTERPRETATION,
    }
