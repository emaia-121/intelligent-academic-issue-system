"""
End-to-end training pipeline for the academic issue classifier.

Run:
    python ml/train_classifier.py

No manual steps required. This script:
  1. Loads ml/dataset/academic_issue_dataset.csv
  2. Preprocesses the text (see preprocessing.py)
  3. Performs a stratified 80/20 train/test split (random_state=42)
  4. Cross-validates TF-IDF configurations on the training split and keeps
     the best one (see evaluation.py, model_config.py)
  5. Trains all four required classical models on the same features
  6. Evaluates every model on the held-out test set
  7. Automatically selects the best model by macro-F1 (no model assumed
     best in advance)
  8. Exports the winning classifier + vectorizer via joblib to ml/models/
  9. Writes ml/reports/model_comparison.csv and ml/reports/training_report.md

This script intentionally stops after export -- it does NOT wire the
classifier into any Django view, API, or the existing rule-based routing
logic. That integration is a separate, later task.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split

# Allow `python ml/train_classifier.py` to import sibling modules
# (preprocessing, model_config, evaluation, reporting) regardless of the
# working directory it's invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluation import evaluate_model, select_best_vectorizer_config  # noqa: E402
from model_config import RANDOM_STATE, VECTORIZER_GRID, build_vectorizer, get_models  # noqa: E402
from preprocessing import clean_series  # noqa: E402
from reporting import write_model_comparison_csv, write_training_report_md  # noqa: E402

ML_DIR = Path(__file__).resolve().parent
DATASET_PATH = ML_DIR / "dataset" / "academic_issue_dataset.csv"
MODELS_DIR = ML_DIR / "models"
REPORTS_DIR = ML_DIR / "reports"

TEST_SIZE = 0.2


def load_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {path}. Run `python ml/generate_dataset.py` first."
        )
    df = pd.read_csv(path)
    if not {"text", "category"}.issubset(df.columns):
        raise ValueError("Dataset must contain 'text' and 'category' columns.")
    df = df.dropna(subset=["text", "category"]).reset_index(drop=True)
    return df


def split_dataset(df: pd.DataFrame):
    """Stratified 80/20 split, grouped by `template_id` within each
    category rather than split row-by-row.

    generate_dataset.py builds every row from one of ~20-30 sentence
    skeletons per category (e.g. "My {code} result has not appeared since
    {session}.") with only slot values like course codes randomized. A plain
    row-level stratified split lets the *same skeleton* land on both sides
    of the split with just a course code swapped -- the model would then be
    "tested" on sentences that are structurally identical to ones it trained
    on, inflating scores without demonstrating real generalization (measured
    initially: this produced a suspicious ~100% test accuracy across models).

    Splitting by template group instead means every test-set sentence comes
    from a skeleton the model never saw during training, while still keeping
    each category proportionally represented in both splits (satisfying the
    "stratified" requirement at the category level). If `template_id` is
    absent (e.g. a hand-supplied dataset without that column), this falls
    back to a plain stratified row split.
    """
    if "template_id" not in df.columns:
        X = df["clean_text"].tolist()
        y = df["category"].tolist()
        return train_test_split(X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE)

    train_idx: list[int] = []
    test_idx: list[int] = []

    for _category, group in df.groupby("category"):
        template_ids = sorted(group["template_id"].unique().tolist())
        train_templates, _test_templates = train_test_split(
            template_ids, test_size=TEST_SIZE, random_state=RANDOM_STATE
        )
        train_templates = set(train_templates)
        is_train = group["template_id"].isin(train_templates)
        train_idx.extend(group.index[is_train].tolist())
        test_idx.extend(group.index[~is_train].tolist())

    train_df, test_df = df.loc[train_idx], df.loc[test_idx]
    X_train = train_df["clean_text"].tolist()
    X_test = test_df["clean_text"].tolist()
    y_train = train_df["category"].tolist()
    y_test = test_df["category"].tolist()
    return X_train, X_test, y_train, y_test


def train_all_models(X_train_vec, y_train) -> dict[str, object]:
    models = get_models()
    for name, model in models.items():
        print(f"  training {name} ...")
        model.fit(X_train_vec, y_train)
    return models


def evaluate_all_models(models: dict, X_test_vec, y_test, class_names: list[str]) -> dict[str, dict]:
    return {name: evaluate_model(model, X_test_vec, y_test, class_names) for name, model in models.items()}


def export_best_model(
    *,
    model,
    vectorizer,
    model_name: str,
    class_names: list[str],
    vectorizer_config: dict,
    dataset_size: int,
) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODELS_DIR / "classifier.pkl")
    joblib.dump(vectorizer, MODELS_DIR / "vectorizer.pkl")

    (MODELS_DIR / "label_classes.json").write_text(
        json.dumps(sorted(class_names), indent=2), encoding="utf-8"
    )

    metadata = {
        "selected_model": model_name,
        "vectorizer_config": {
            "ngram_range": list(vectorizer_config["ngram_range"]),
            "stop_words": vectorizer_config["stop_words"],
            "min_df": vectorizer_config["min_df"],
            "max_df": vectorizer_config["max_df"],
        },
        "dataset_size": dataset_size,
        "random_state": RANDOM_STATE,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "sklearn_note": "classifier.predict() expects a TF-IDF matrix produced by the "
        "co-exported vectorizer.pkl, applied to text preprocessed with ml/preprocessing.py's "
        "clean_text().",
    }
    (MODELS_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def main() -> None:
    print(f"Loading dataset from {DATASET_PATH} ...")
    df = load_dataset(DATASET_PATH)
    class_names = sorted(df["category"].unique().tolist())
    class_counts = df["category"].value_counts().reindex(class_names)
    print(f"Loaded {len(df)} examples across {len(class_names)} categories.")

    print("Preprocessing text ...")
    df["clean_text"] = clean_series(df["text"])

    print("Splitting dataset (80/20, stratified, random_state=42) ...")
    X_train_text, X_test_text, y_train, y_test = split_dataset(df)
    print(f"  train={len(X_train_text)}  test={len(X_test_text)}")

    print("Selecting TF-IDF configuration via cross-validation on the training split ...")
    best_vec_config, vectorizer_search_results = select_best_vectorizer_config(
        X_train_text, y_train, VECTORIZER_GRID
    )
    print(f"  best config: {best_vec_config}")

    print("Fitting final TF-IDF vectorizer on the training split ...")
    vectorizer = build_vectorizer(**best_vec_config)
    X_train_vec = vectorizer.fit_transform(X_train_text)
    X_test_vec = vectorizer.transform(X_test_text)
    print(f"  vocabulary size: {len(vectorizer.vocabulary_)}")

    print("Training models:")
    models = train_all_models(X_train_vec, y_train)

    print("Evaluating models on the held-out test set ...")
    all_results = evaluate_all_models(models, X_test_vec, y_test, class_names)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    comparison_df = write_model_comparison_csv(all_results, REPORTS_DIR / "model_comparison.csv")
    print("\nModel comparison (sorted by macro-F1):")
    print(comparison_df.to_string(index=False))

    best_model_name = comparison_df.iloc[0]["Model"]
    best_model = models[best_model_name]
    print(f"\nSelected best model: {best_model_name}")

    print("Exporting classifier + vectorizer ...")
    export_best_model(
        model=best_model,
        vectorizer=vectorizer,
        model_name=best_model_name,
        class_names=class_names,
        vectorizer_config=best_vec_config,
        dataset_size=len(df),
    )

    print("Writing training_report.md ...")
    write_training_report_md(
        output_path=REPORTS_DIR / "training_report.md",
        dataset_path=DATASET_PATH,
        dataset_size=len(df),
        class_counts=class_counts,
        vectorizer_search_results=vectorizer_search_results,
        chosen_vectorizer_config=best_vec_config,
        comparison_df=comparison_df,
        all_results=all_results,
        class_names=class_names,
        best_model_name=best_model_name,
        export_dir=MODELS_DIR.relative_to(ML_DIR.parent),
        train_size=len(X_train_text),
        test_size=len(X_test_text),
    )

    print("\nDone.")
    print(f"  classifier -> {MODELS_DIR / 'classifier.pkl'}")
    print(f"  vectorizer -> {MODELS_DIR / 'vectorizer.pkl'}")
    print(f"  reports    -> {REPORTS_DIR}")


if __name__ == "__main__":
    main()
