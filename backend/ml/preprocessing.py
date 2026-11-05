"""
Text preprocessing for the academic issue classifier.

Documented preprocessing decisions (see training_report.md for the
measured impact of the stopword decision specifically):

1. Course-code normalization runs FIRST, before lowercasing. Students write
   course codes both spaced ("CSC 311") and unspaced ("CSC311"). Left alone,
   TF-IDF's default tokenizer would split "CSC 311" into two tokens ("csc",
   "311"), diluting a genuinely useful signal and splitting it from the
   unspaced form entirely. Collapsing "CSC 311" -> "CSC311" first means both
   spellings always produce the identical token.

2. Lowercasing everything. Case carries no classification signal in this
   domain, and it keeps the vocabulary compact (e.g. "Please" and "please"
   collapse to one feature).

3. Whitespace normalization: repeated spaces/newlines collapse to one space,
   and leading/trailing whitespace is stripped.

4. No stemming or lemmatization. Abbreviations and course codes (GST, NYSC,
   JAMB, CGPA, CSC311, ...) are exactly the signal this classifier should
   preserve, and aggressive stemming risks mangling them or collapsing
   meaningfully distinct words (e.g. "results" -> "result", "cleared" ->
   "clear"). No evaluation showed a benefit from stemming here, so per the
   task's own guidance ("avoid aggressive stemming unless justified") it is
   skipped entirely.

5. Stopword removal is NOT hardcoded here. train_classifier.py explicitly
   compares stop_words=None against stop_words='english' (as part of its
   TF-IDF configuration search) via cross-validated macro-F1 on the training
   set only, and keeps whichever wins. See training_report.md for the result.
"""

from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"\s+")
# Matches a 2-4 letter subject prefix followed by whitespace then a 3-digit
# course number, e.g. "CSC 311", "gst 111" -- but not "CSC311" (already
# unspaced, left untouched) or four-digit numbers.
_COURSE_CODE_RE = re.compile(r"\b([A-Za-z]{2,4})\s+(\d{3})\b")


def normalize_course_codes(text: str) -> str:
    """Collapses spaced course codes like "CSC 311" into "CSC311" so both
    spellings tokenize identically downstream."""
    return _COURSE_CODE_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}", text)


def clean_text(text: str) -> str:
    """Full preprocessing pipeline applied to a single string. Idempotent --
    safe to call more than once on the same text."""
    text = normalize_course_codes(str(text))
    text = text.lower()
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def clean_series(texts) -> list[str]:
    """Vectorized convenience wrapper for a pandas Series / list of strings."""
    return [clean_text(t) for t in texts]
