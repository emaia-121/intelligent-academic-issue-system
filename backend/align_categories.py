# SUPERSEDED -- do not run.
#
# This was an earlier draft (a standalone shell script, not a tracked
# Django migration) for aligning the categories_category table to the 12
# canonical category names. It was replaced by a proper data migration,
# categories/migrations/0005_align_to_canonical_categories.py, which:
#   - is transactional (safe to interrupt/retry, unlike this script),
#   - is part of the tracked migration history (`manage.py showmigrations`
#     / `manage.py migrate` both see it), and
#   - also aligns the documents_app.Document catalogue to the exact
#     required-document wording from the specification, which this draft
#     did not fully do.
#
# That migration has already been applied to this database. This file
# couldn't be deleted from this session; it's left here emptied of logic
# as a pointer to the real migration, safe to delete by hand.
