from collections.abc import Callable
from importlib.util import find_spec
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    silhouette_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from app.models import Dataset, Experiment
from app.services.explainability import (
    explain_supervised_model,
    unsupported_clustering_explanation,
)

XGBOOST_AVAILABLE = find_spec("xgboost") is not None

MODEL_NAMES = {
    "classification": {
        "logistic_regression": "Logistic Regression",
        "decision_tree": "Decision Tree",
        "random_forest": "Random Forest",
        "gradient_boosting": "Gradient Boosting",
        "xgboost": "XGBoost",
    },
    "regression": {
        "linear_regression": "Linear Regression",
        "ridge": "Ridge",
        "random_forest_regressor": "Random Forest Regressor",
        "gradient_boosting_regressor": "Gradient Boosting Regressor",
        "xgboost_regressor": "XGBoost Regressor",
    },
    "clustering": {"kmeans": "K-Means", "dbscan": "DBSCAN"},
}


def model_catalog() -> dict[str, list[dict[str, Any]]]:
    return {
        task: [
            {
                "id": model_id,
                "name": name,
                "available": XGBOOST_AVAILABLE or not model_id.startswith("xgboost"),
                "unavailable_reason": None if XGBOOST_AVAILABLE or not model_id.startswith("xgboost") else "Install the optional xgboost package on the API and worker images",
            }
            for model_id, name in models.items()
        ]
        for task, models in MODEL_NAMES.items()
    }


def validate_experiment_configuration(dataset: Dataset, task_type: str, target: str | None, features: list[str], models: list[str]) -> None:
    columns = {column.name: column.data_type for column in dataset.columns}
    unknown = [column for column in features + ([target] if target else []) if column not in columns]
    if unknown:
        raise ValueError(f"Unknown dataset column: {unknown[0]}")
    allowed = MODEL_NAMES[task_type]
    for model in models:
        if model not in allowed:
            raise ValueError(f"Model '{model}' is not valid for {task_type}")
        if model.startswith("xgboost") and not XGBOOST_AVAILABLE:
            raise ValueError(f"Model '{model}' is not available in this environment")
    if task_type == "regression" and columns.get(target or "") != "numeric":
        raise ValueError("Regression target must be numeric")


def _preprocessor(dataset: Dataset, features: list[str], config: dict[str, Any]) -> ColumnTransformer:
    types = {column.name: column.data_type for column in dataset.columns}
    numeric = [column for column in features if types[column] == "numeric"]
    categorical = [column for column in features if types[column] != "numeric"]
    scaler = {"standard": StandardScaler(), "minmax": MinMaxScaler(), "none": "passthrough"}[config["scaler"]]
    transformers = []
    if numeric:
        transformers.append(("numeric", Pipeline([("imputer", SimpleImputer(strategy=config["numeric_imputer"])), ("scaler", scaler)]), numeric))
    if categorical:
        transformers.append(("categorical", Pipeline([("imputer", SimpleImputer(strategy=config["categorical_imputer"])), ("encoder", OneHotEncoder(handle_unknown="ignore", max_categories=100, sparse_output=False))]), categorical))
    return ColumnTransformer(transformers=transformers, remainder="drop")


def _parameters(model_id: str, supplied: dict[str, Any]) -> dict[str, Any]:
    allowed: dict[str, tuple[type, float | None, float | None]] = {
        "C": (float, 0.0001, 10000), "max_iter": (int, 100, 5000), "max_depth": (int, 1, 100),
        "min_samples_split": (int, 2, 1000), "n_estimators": (int, 10, 500), "learning_rate": (float, 0.001, 1),
        "alpha": (float, 0, 10000), "n_clusters": (int, 2, 20), "eps": (float, 0.01, 100), "min_samples": (int, 2, 100),
    }
    permitted_by_model = {
        "logistic_regression": {"C", "max_iter"}, "decision_tree": {"max_depth", "min_samples_split"},
        "random_forest": {"n_estimators", "max_depth", "min_samples_split"}, "gradient_boosting": {"n_estimators", "learning_rate", "max_depth"},
        "ridge": {"alpha"}, "random_forest_regressor": {"n_estimators", "max_depth", "min_samples_split"},
        "gradient_boosting_regressor": {"n_estimators", "learning_rate", "max_depth"}, "kmeans": {"n_clusters"}, "dbscan": {"eps", "min_samples"},
        "xgboost": {"n_estimators", "learning_rate", "max_depth"}, "xgboost_regressor": {"n_estimators", "learning_rate", "max_depth"},
        "linear_regression": set(),
    }[model_id]
    result: dict[str, Any] = {}
    for key, value in supplied.items():
        if key not in permitted_by_model:
            raise ValueError(f"Unsupported parameter '{key}' for model '{model_id}'")
        cast, minimum, maximum = allowed[key]
        converted = cast(value)
        if (minimum is not None and converted < minimum) or (maximum is not None and converted > maximum):
            raise ValueError(f"Parameter '{key}' is outside the supported range")
        result[key] = converted
    return result


def build_estimator(task_type: str, model_id: str, supplied: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    params = _parameters(model_id, supplied)
    random_defaults = {"random_state": 42}
    if model_id == "logistic_regression": estimator = LogisticRegression(**{"max_iter": 1000, "random_state": 42, **params})
    elif model_id == "decision_tree": estimator = DecisionTreeClassifier(**random_defaults, **params)
    elif model_id == "random_forest": estimator = RandomForestClassifier(**{"n_estimators": 100, "n_jobs": 1, **random_defaults, **params})
    elif model_id == "gradient_boosting": estimator = GradientBoostingClassifier(**random_defaults, **params)
    elif model_id == "linear_regression": estimator = LinearRegression(**params)
    elif model_id == "ridge": estimator = Ridge(**{"alpha": 1.0, **params})
    elif model_id == "random_forest_regressor": estimator = RandomForestRegressor(**{"n_estimators": 100, "n_jobs": 1, **random_defaults, **params})
    elif model_id == "gradient_boosting_regressor": estimator = GradientBoostingRegressor(**random_defaults, **params)
    elif model_id == "kmeans": estimator = KMeans(**{"n_clusters": 3, "n_init": 10, **random_defaults, **params})
    elif model_id == "dbscan": estimator = DBSCAN(**{"eps": 0.5, "min_samples": 5, **params})
    elif model_id in {"xgboost", "xgboost_regressor"}:
        if not XGBOOST_AVAILABLE:
            raise ValueError("XGBoost is not available")
        from xgboost import XGBClassifier, XGBRegressor
        estimator = (XGBClassifier if model_id == "xgboost" else XGBRegressor)(**{"n_estimators": 100, "random_state": 42, **params})
    else:
        raise ValueError(f"Unsupported model: {model_id}")
    effective = {key: value for key, value in estimator.get_params(deep=False).items() if isinstance(value, (str, int, float, bool)) or value is None}
    return estimator, effective


def _classification_metrics(pipeline: Pipeline, x_test: pd.DataFrame, y_test: pd.Series) -> dict[str, Any]:
    predictions = pipeline.predict(x_test)
    result: dict[str, Any] = {
        "accuracy": round(float(accuracy_score(y_test, predictions)), 6),
        "precision": round(float(precision_score(y_test, predictions, average="weighted", zero_division=0)), 6),
        "recall": round(float(recall_score(y_test, predictions, average="weighted", zero_division=0)), 6),
        "f1": round(float(f1_score(y_test, predictions, average="weighted", zero_division=0)), 6),
        "confusion_matrix": confusion_matrix(y_test, predictions).astype(int).tolist(),
    }
    if hasattr(pipeline, "predict_proba"):
        try:
            probabilities = pipeline.predict_proba(x_test)
            result["roc_auc"] = round(float(roc_auc_score(y_test, probabilities[:, 1] if probabilities.shape[1] == 2 else probabilities, multi_class="ovr", average="weighted")), 6)
        except ValueError:
            result["roc_auc"] = None
    return result


def run_supervised_experiment(experiment: Experiment, dataset: Dataset, progress_callback: Callable[[int, int], None] | None = None) -> list[dict[str, Any]]:
    selected = experiment.features + [experiment.target_column]
    frame = pd.read_csv(dataset.storage_path, usecols=selected, low_memory=False).dropna(subset=[experiment.target_column])
    if len(frame) < 10:
        raise ValueError("Supervised training requires at least 10 rows with a non-missing target")
    x, y = frame[experiment.features], frame[experiment.target_column]
    if experiment.task_type == "classification" and y.nunique() < 2:
        raise ValueError("Classification target must contain at least two classes")
    stratify = y if experiment.task_type == "classification" and y.value_counts().min() >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=experiment.preprocessing["test_size"], random_state=42, stratify=stratify)
    results = []
    for index, model_id in enumerate(experiment.selected_models, start=1):
        estimator, parameters = build_estimator(experiment.task_type, model_id, experiment.model_parameters.get(model_id, {}))
        pipeline = Pipeline([("preprocessing", _preprocessor(dataset, experiment.features, experiment.preprocessing)), ("model", estimator)])
        pipeline.fit(x_train, y_train)
        if experiment.task_type == "classification": metrics = _classification_metrics(pipeline, x_test, y_test)
        else:
            predictions = pipeline.predict(x_test)
            mse = float(mean_squared_error(y_test, predictions))
            metrics = {"mae": round(float(mean_absolute_error(y_test, predictions)), 6), "mse": round(mse, 6), "rmse": round(float(np.sqrt(mse)), 6), "r2": round(float(r2_score(y_test, predictions)), 6)}
        metrics.update({"train_rows": len(x_train), "test_rows": len(x_test)})
        explanation = explain_supervised_model(pipeline, model_id, x_train, x_test, y_test)
        results.append({"model_name": model_id, "metrics": metrics, "hyperparameters": parameters, "explainability": explanation})
        if progress_callback:
            progress_callback(index, len(experiment.selected_models))
    return results


def run_clustering_experiment(experiment: Experiment, dataset: Dataset, progress_callback: Callable[[int, int], None] | None = None) -> list[dict[str, Any]]:
    frame = pd.read_csv(dataset.storage_path, usecols=experiment.features, low_memory=False)
    if len(frame) < 3:
        raise ValueError("Clustering requires at least three rows")
    results = []
    for index, model_id in enumerate(experiment.selected_models, start=1):
        estimator, parameters = build_estimator("clustering", model_id, experiment.model_parameters.get(model_id, {}))
        pipeline = Pipeline([("preprocessing", _preprocessor(dataset, experiment.features, experiment.preprocessing)), ("model", estimator)])
        labels = pipeline.fit_predict(frame)
        unique, counts = np.unique(labels, return_counts=True)
        cluster_sizes = {str(int(label)): int(count) for label, count in zip(unique, counts)}
        non_noise = labels != -1
        valid_labels = set(labels[non_noise])
        score = None
        if len(valid_labels) >= 2 and non_noise.sum() > len(valid_labels):
            transformed = pipeline.named_steps["preprocessing"].transform(frame)
            score = round(float(silhouette_score(transformed[non_noise], labels[non_noise])), 6)
        results.append({"model_name": model_id, "metrics": {"silhouette_score": score, "cluster_sizes": cluster_sizes, "rows": len(frame)}, "hyperparameters": parameters, "explainability": unsupported_clustering_explanation()})
        if progress_callback:
            progress_callback(index, len(experiment.selected_models))
    return results


def train_models(experiment: Experiment, dataset: Dataset, progress_callback: Callable[[int, int], None] | None = None) -> list[dict[str, Any]]:
    validate_experiment_configuration(dataset, experiment.task_type, experiment.target_column, experiment.features, experiment.selected_models)
    return run_clustering_experiment(experiment, dataset, progress_callback) if experiment.task_type == "clustering" else run_supervised_experiment(experiment, dataset, progress_callback)
