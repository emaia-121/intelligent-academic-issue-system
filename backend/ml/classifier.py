"""
Confidence-aware inference layer for the academic issue classifier.

This is the ONLY module in the project that should ever load
`ml/models/classifier.pkl` or `ml/models/vectorizer.pkl`. Nothing else in
the Django app -- views, serializers, services -- should call
`joblib.load()` directly. Everything else should call `predict_issue()`
from here.

Does NOT retrain, re-vectorize, or otherwise touch the training pipeline.
Loads the artifacts `ml/train_classifier.py` already exported, exactly as
they are.

--------------------------------------------------------------------------
How confidence is calculated
--------------------------------------------------------------------------
Step 0 of building this module was inspecting the exported classifier
(`ml/models/classifier.pkl`) to see what it actually supports:

    >>> import joblib
    >>> clf = joblib.load("ml/models/classifier.pkl")
    >>> type(clf)
    <class 'sklearn.ensemble._forest.RandomForestClassifier'>
    >>> hasattr(clf, "predict_proba")
    True

The exported model is a RandomForestClassifier, and RandomForestClassifier
supports `predict_proba()` (it averages each tree's vote fractions across
the forest), so this module uses it: confidence for the top prediction is
`max(classifier.predict_proba(X)[0])`, a float in [0.0, 1.0] -- never
converted to a percentage. The `top_predictions` list is every category's
probability from that same `predict_proba()` call, sorted descending and
truncated to the top 3.

A fallback path exists for `decision_function`-only models (e.g. LinearSVC,
which has no `predict_proba`) that converts the decision margins to
pseudo-probabilities via softmax. This is a deliberate defensive branch, not
the active path today -- the exported model has `predict_proba`, so that
fallback does not run against the current artifacts. It exists so this
module keeps working, with a clearly-labeled approximation, if the exported
model is ever swapped for one without `predict_proba` (see
`_class_probabilities()`).

--------------------------------------------------------------------------
Why confidence thresholds exist
--------------------------------------------------------------------------
A raw probability isn't itself a decision. Two configurable thresholds
(HIGH_CONFIDENCE_THRESHOLD, LOW_CONFIDENCE_THRESHOLD below) translate a
probability into one of three concrete UX/workflow states so callers (a
future API, an issue-creation flow) don't each reimplement this judgment
call:

  - confidence >= HIGH_CONFIDENCE_THRESHOLD: the model is confident enough
    to auto-assign the predicted category without bothering the user.
  - LOW_CONFIDENCE_THRESHOLD <= confidence < HIGH_CONFIDENCE_THRESHOLD: the
    model has a reasonable guess but it's worth a one-click confirmation
    from the student before committing to it.
  - confidence < LOW_CONFIDENCE_THRESHOLD: the model doesn't have a strong
    enough signal to guess responsibly; a human (or the student picking
    manually) should decide instead of the system silently routing the
    issue on a coin-flip prediction.

--------------------------------------------------------------------------
Why low confidence does NOT automatically mean "Other"
--------------------------------------------------------------------------
"Other" is a category in the training data like any other -- it has its own
examples and its own learned probability. A low top confidence means the
model is unsure which of the 12 categories fits, which could just as
plausibly mean the true answer is "Missing Result" phrased unusually as it
could mean "Other". Silently substituting "Other" whenever confidence is low
would throw away the model's actual (if uncertain) top guess and misrepresent
uncertainty as a category decision -- they are different things. That's why
low confidence is surfaced as `requires_manual_review = True` with the
model's real top prediction still attached, rather than being rewritten to
"Other".
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import TypedDict

import joblib
import numpy as np

# So `from preprocessing import clean_text` resolves regardless of whether
# this module is imported as `ml.classifier` or run as a script -- mirrors
# the same sys.path convention already used by ml/train_classifier.py.
_ML_DIR = Path(__file__).resolve().parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

from preprocessing import clean_text  # noqa: E402

MODELS_DIR = _ML_DIR / "models"
CLASSIFIER_PATH = MODELS_DIR / "classifier.pkl"
VECTORIZER_PATH = MODELS_DIR / "vectorizer.pkl"

# ---------------------------------------------------------------------------
# Confidence thresholds. Configurable, defined once, referenced everywhere
# below -- never hardcoded inline elsewhere in this module.
# ---------------------------------------------------------------------------
HIGH_CONFIDENCE_THRESHOLD = 0.80
LOW_CONFIDENCE_THRESHOLD = 0.60

TOP_N_PREDICTIONS = 3


# ---------------------------------------------------------------------------
# Exceptions. Every failure mode the task calls out (missing artifacts,
# unknown category names, DB lookup failures) raises one of these instead of
# returning None / an empty dict / a fabricated result.
# ---------------------------------------------------------------------------
class ClassifierError(Exception):
    """Base class for every error this module raises."""


class ClassifierArtifactNotFoundError(ClassifierError, FileNotFoundError):
    """classifier.pkl or vectorizer.pkl is missing from ml/models/."""


class ClassifierLoadError(ClassifierError, RuntimeError):
    """The artifact file exists but failed to load (corrupt file, an
    incompatible joblib/scikit-learn version, etc.)."""


class CategoryLookupError(ClassifierError, LookupError):
    """The predicted category name could not be resolved to a row in the
    real Category table -- either it genuinely doesn't exist there, or the
    database lookup itself failed."""


class PredictionInputError(ClassifierError, ValueError):
    """title/description were empty or otherwise unusable."""


class TypedPrediction(TypedDict):
    category: str
    confidence: float


# ---------------------------------------------------------------------------
# Lazy singletons. Loaded once per process, on first use, then reused for
# every subsequent prediction -- joblib.load() is never called per-request.
# A lock guards the first load in case multiple threads hit this
# concurrently before anything is cached yet.
# ---------------------------------------------------------------------------
_load_lock = threading.Lock()
_classifier = None
_vectorizer = None


def _load_artifact(path: Path, label: str):
    if not path.exists():
        raise ClassifierArtifactNotFoundError(
            f"{label} not found at {path}. Run `python ml/train_classifier.py` "
            f"to (re)generate the exported model artifacts before using the "
            f"inference layer."
        )
    try:
        return joblib.load(path)
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: any
        # unpickling failure (corrupt file, version mismatch, etc.) should
        # surface as one clear, catchable error rather than an opaque
        # joblib/pickle traceback.
        raise ClassifierLoadError(f"Failed to load {label} from {path}: {exc}") from exc


def get_classifier():
    """Returns the cached classifier, loading it on first call."""
    global _classifier
    if _classifier is None:
        with _load_lock:
            if _classifier is None:  # re-check inside the lock
                _classifier = _load_artifact(CLASSIFIER_PATH, "classifier")
    return _classifier


def get_vectorizer():
    """Returns the cached TF-IDF vectorizer, loading it on first call."""
    global _vectorizer
    if _vectorizer is None:
        with _load_lock:
            if _vectorizer is None:
                _vectorizer = _load_artifact(VECTORIZER_PATH, "vectorizer")
    return _vectorizer


def reset_cache() -> None:
    """Clears the cached classifier/vectorizer so the next call reloads them
    from disk. Not needed in normal operation -- exists for tests that want
    to exercise the loading path more than once in a single process."""
    global _classifier, _vectorizer
    with _load_lock:
        _classifier = None
        _vectorizer = None


def _softmax(scores: np.ndarray) -> np.ndarray:
    shifted = scores - scores.max()
    exp = np.exp(shifted)
    return exp / exp.sum()


def _class_probabilities(classifier, X) -> np.ndarray:
    """Returns a probability-like array aligned to classifier.classes_.

    Uses predict_proba() when the model supports it (true today -- the
    exported model is a RandomForestClassifier). Falls back to a
    softmax-normalized decision_function() for margin-based models that
    don't expose predict_proba (e.g. LinearSVC), clearly documented as an
    approximation rather than a calibrated probability. If neither is
    available there is no principled way to produce a confidence score, so
    that's raised as an error instead of inventing a number.
    """
    if hasattr(classifier, "predict_proba"):
        return classifier.predict_proba(X)[0]

    if hasattr(classifier, "decision_function"):
        scores = classifier.decision_function(X)[0]
        return _softmax(np.atleast_1d(scores))

    raise ClassifierLoadError(
        f"{type(classifier).__name__} exposes neither predict_proba() nor "
        f"decision_function(); this module cannot compute a confidence score "
        f"for it."
    )


def _combine_title_and_description(title: str, description: str) -> str:
    title = (title or "").strip()
    description = (description or "").strip()
    combined = f"{title}. {description}" if title and description else (title or description)
    return combined.strip()


def _resolve_category(name: str) -> dict:
    """Looks up the predicted category name in the real Category table.
    Only id/name are selected -- required documents, department, etc. are
    irrelevant to this module and would be an unnecessary extra query/join.

    Raises CategoryLookupError (never returns None / silently substitutes
    a different category) if the name doesn't exist or the lookup itself
    fails for any other reason (e.g. a database connectivity issue).
    """
    # Imported lazily so this module can be unit-tested / used for a plain
    # text -> probabilities prediction without requiring Django to be fully
    # configured unless a caller actually needs the DB-backed category.
    from categories.models import Category

    try:
        category = Category.objects.only("id", "name").filter(name__iexact=name).first()
    except Exception as exc:  # noqa: BLE001 -- any DB error (connection,
        # misconfiguration, etc.) should surface as a CategoryLookupError,
        # not an unhandled database exception bubbling out of this module.
        raise CategoryLookupError(f"Database lookup failed for category '{name}': {exc}") from exc

    if category is None:
        raise CategoryLookupError(
            f"Predicted category '{name}' has no matching row in the Category "
            f"table. The classifier's label set and the seeded Category data "
            f"are not guaranteed to be in sync -- reconcile them (or add an "
            f"explicit label-to-Category mapping) before relying on this in "
            f"an API."
        )

    return {"id": category.id, "name": category.name}


def predict_issue(title: str, description: str) -> dict:
    """Predicts the category for a student issue from its title and
    description.

    1. Combines title + description into one string.
    2. Preprocesses it with preprocessing.clean_text() (the exact function
       the training pipeline used -- see ml/preprocessing.py).
    3. Vectorizes it with the exported TF-IDF vectorizer.
    4. Predicts class probabilities with the exported classifier.
    5. Takes the highest-probability class as the prediction; its
       probability is the confidence (float in [0.0, 1.0], never a
       percentage -- see module docstring for why).
    6. Sorts all class probabilities descending and keeps the top
       TOP_N_PREDICTIONS.
    7. Resolves the top prediction's category name to the real Category
       table (id + name).
    8. Applies HIGH_CONFIDENCE_THRESHOLD / LOW_CONFIDENCE_THRESHOLD to
       decide requires_confirmation / requires_manual_review.

    Raises:
        PredictionInputError: title and description were both empty.
        ClassifierArtifactNotFoundError: classifier.pkl/vectorizer.pkl
            missing from ml/models/.
        ClassifierLoadError: an artifact exists but failed to load.
        CategoryLookupError: the predicted category name has no match in
            the Category table, or the database lookup failed.
    """
    combined_text = _combine_title_and_description(title, description)
    if not combined_text:
        raise PredictionInputError("title and description cannot both be empty.")

    cleaned_text = clean_text(combined_text)

    classifier = get_classifier()
    vectorizer = get_vectorizer()

    X = vectorizer.transform([cleaned_text])
    probabilities = _class_probabilities(classifier, X)
    class_names = list(classifier.classes_)

    ranked = sorted(zip(class_names, probabilities), key=lambda pair: pair[1], reverse=True)
    top_label, top_confidence = ranked[0]
    top_confidence = float(top_confidence)

    top_predictions: list[TypedPrediction] = [
        {"category": label, "confidence": round(float(prob), 4)}
        for label, prob in ranked[:TOP_N_PREDICTIONS]
    ]

    category = _resolve_category(top_label)

    if top_confidence >= HIGH_CONFIDENCE_THRESHOLD:
        requires_confirmation = False
        requires_manual_review = False
    elif top_confidence >= LOW_CONFIDENCE_THRESHOLD:
        requires_confirmation = True
        requires_manual_review = False
    else:
        requires_confirmation = False
        requires_manual_review = True

    return {
        "category": category,
        "confidence": round(top_confidence, 4),
        "requires_confirmation": requires_confirmation,
        "requires_manual_review": requires_manual_review,
        "top_predictions": top_predictions,
    }
