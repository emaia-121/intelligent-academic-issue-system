"""
Model and feature-extraction configuration for the academic issue
classifier. Kept separate from train_classifier.py so hyperparameters are
easy to find and adjust without touching the pipeline logic.
"""

from __future__ import annotations

from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC

RANDOM_STATE = 42

# ---------------------------------------------------------------------------
# TF-IDF configuration search space. train_classifier.py cross-validates
# each of these on the TRAINING split only (never the held-out test set) and
# keeps whichever combination yields the best mean macro-F1. Kept modest in
# size (8 combinations) so the search stays fast while still covering the
# two decisions the task calls out explicitly: unigrams vs. unigrams+bigrams,
# and stopword removal on vs. off.
# ---------------------------------------------------------------------------
VECTORIZER_GRID: list[dict] = [
    {"ngram_range": ngram_range, "stop_words": stop_words, "min_df": min_df, "max_df": 0.9}
    for ngram_range in [(1, 1), (1, 2)]
    for stop_words in [None, "english"]
    for min_df in [2, 3]
]


def build_vectorizer(**overrides) -> TfidfVectorizer:
    """Builds a TfidfVectorizer with the given config (see VECTORIZER_GRID
    entries), applied on top of preprocessing.clean_text output."""
    return TfidfVectorizer(sublinear_tf=True, **overrides)


def get_models() -> dict[str, object]:
    """Returns the four classical models the task requires, each with
    sensible, documented hyperparameters. Fresh instances every call so
    repeated training runs never share fitted state.

    - MultinomialNB: alpha=0.1 (lighter Laplace smoothing than the sklearn
      default of 1.0) tends to suit short, sparse TF-IDF text better than
      the default, since the vocabulary per document is small.
    - LogisticRegression: class_weight='balanced' since some categories
      could plausibly be reported more often than others in a real deployment
      even though this synthetic set is class-balanced; C=1.0 as a
      reasonable default regularization strength; max_iter raised because
      TF-IDF features can need more iterations to converge than dense data.
    - LinearSVC: same class_weight/regularization reasoning as
      LogisticRegression; linear SVMs are a standard strong baseline for
      high-dimensional sparse text features.
    - RandomForestClassifier: n_estimators=300 for stable estimates without
      excessive training time on ~1,200 training rows; class_weight
      'balanced' for the same reason as above.
    """
    return {
        "Multinomial Naive Bayes": MultinomialNB(alpha=0.1),
        "Logistic Regression": LogisticRegression(
            C=1.0,
            max_iter=2000,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
        "Linear SVM (LinearSVC)": LinearSVC(
            C=1.0,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            max_iter=5000,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=300,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }
