"""
Manual smoke test for ml/classifier.py.

Demonstrates predict_issue() across the three confidence tiers the task
describes (high / medium / low), plus one example that hits the category
"unknown category names" error path on purpose (see the comment on that
example below -- it's a real, current condition, not a contrived failure).

This script is read-only: it only ever performs Category SELECT queries via
predict_issue() -> _resolve_category(). It never creates, updates, or
deletes any database row, and it never touches Issue/User/auth data at all.

Run from the `backend/` directory (same convention as manage.py and
ml/train_classifier.py):

    python ml/test_classifier.py

Needs Django configured to resolve categories against the real database, so
this bootstraps Django itself (same steps manage.py takes) before importing
the classifier module -- ml/classifier.py's own tests/importers don't need
to know or care about that; only this standalone script does.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "student_issue_system.settings")

import django  # noqa: E402

django.setup()

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classifier import (  # noqa: E402
    ClassifierError,
    HIGH_CONFIDENCE_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD,
    predict_issue,
)

EXAMPLES = [
    (
        "High confidence",
        "Please, I need my official transcript processed urgently for a job application.",
        "",
    ),
    (
        "Medium confidence",
        "My GST111 result has not appeared on the portal since last semester",
        "even though I sat for the exam and my coursemates already have theirs.",
    ),
    (
        "Low confidence / ambiguous",
        "My result and my transcript both seem to be affected by the same issue,",
        "not sure which one to report.",
    ),
    (
        "Ambiguous / falls back toward 'Other'",
        "I need help",
        "",
    ),
]


def main() -> None:
    print(f"HIGH_CONFIDENCE_THRESHOLD = {HIGH_CONFIDENCE_THRESHOLD}")
    print(f"LOW_CONFIDENCE_THRESHOLD  = {LOW_CONFIDENCE_THRESHOLD}\n")

    for label, title, description in EXAMPLES:
        print("=" * 78)
        print(f"{label}")
        print(f"  title:       {title!r}")
        print(f"  description: {description!r}")
        print("-" * 78)
        try:
            result = predict_issue(title, description)
            # This is exactly the dict a future Django view would receive
            # from predict_issue() and could serialize straight into an
            # API response.
            print(json.dumps(result, indent=2))
        except ClassifierError as exc:
            # The classifier's 12-label set and the Category rows in this
            # database are now kept in exact alignment (see
            # categories/migrations/0005_align_to_canonical_categories.py),
            # so this path should not trigger for any of the 12 canonical
            # labels. It's still here, uncollapsed, as a safety net:
            # predict_issue() never invents a fallback category or
            # silently drops a lookup failure -- if a category is ever
            # renamed/removed from the database again in the future
            # without updating the classifier (or vice versa), this is
            # exactly the specific, catchable exception that would surface
            # it, instead of silently misrouting an issue.
            print(f"Raised {type(exc).__name__}: {exc}")
        print()


if __name__ == "__main__":
    main()
