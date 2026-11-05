"""
Evaluation helpers: TF-IDF configuration selection via cross-validation, and
per-model test-set scoring (accuracy, macro precision/recall/F1, confusion
matrix, full classification report).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score

from model_config import RANDOM_STATE, build_vectorizer


def select_best_vectorizer_config(
    X_train_text: list[str],
    y_train: list[str],
    grid: list[dict],
    cv_folds: int = 5,
) -> tuple[dict, pd.DataFrame]:
    """Cross-validates every vectorizer config in `grid` using a fixed
    Logistic Regression probe model, scored on mean macro-F1 across
    `cv_folds` stratified folds of the TRAINING split only (the held-out
    test set is never touched here, avoiding leakage into the selection
    decision). Returns the winning config dict and a results table for the
    report.
    """
    skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=RANDOM_STATE)
    probe = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE)

    results = []
    for config in grid:
        vectorizer = build_vectorizer(**config)
        X = vectorizer.fit_transform(X_train_text)
        scores = cross_val_score(probe, X, y_train, cv=skf, scoring="f1_macro")
        results.append({**config, "mean_cv_f1_macro": scores.mean(), "std_cv_f1_macro": scores.std()})

    results_df = pd.DataFrame(results).sort_values("mean_cv_f1_macro", ascending=False).reset_index(drop=True)
    best_row = results_df.iloc[0]
    # Cast back to plain Python types -- pandas promotes dict values to
    # numpy scalars (np.int64/np.float64) once collected into a DataFrame,
    # which json.dumps() can't serialize later when metadata.json is written.
    best_config = {
        "ngram_range": tuple(best_row["ngram_range"]),
        "stop_words": None if pd.isna(best_row["stop_words"]) else str(best_row["stop_words"]),
        "min_df": int(best_row["min_df"]),
        "max_df": float(best_row["max_df"]),
    }
    return best_config, results_df


def evaluate_model(model, X_test, y_test, class_names: list[str]) -> dict:
    """Scores a fitted model on the held-out test set and returns every
    metric the task requires, plus the raw prediction array for reuse."""
    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="macro", zero_division=0
    )
    report_text = classification_report(y_test, y_pred, labels=class_names, zero_division=0)
    report_dict = classification_report(
        y_test, y_pred, labels=class_names, output_dict=True, zero_division=0
    )
    matrix = confusion_matrix(y_test, y_pred, labels=class_names)

    return {
        "accuracy": accuracy,
        "precision_macro": precision,
        "recall_macro": recall,
        "f1_macro": f1,
        "classification_report_text": report_text,
        "classification_report_dict": report_dict,
        "confusion_matrix": matrix,
        "y_pred": y_pred,
    }


def confusion_matrix_to_dataframe(matrix: np.ndarray, class_names: list[str]) -> pd.DataFrame:
    """Formats a confusion matrix as a labeled DataFrame (rows = true class,
    columns = predicted class) for CSV export / markdown rendering."""
    return pd.DataFrame(matrix, index=class_names, columns=class_names)
