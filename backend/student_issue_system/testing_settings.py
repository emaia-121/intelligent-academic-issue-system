from .settings import *

# Isolated database for controlled system testing.
DATABASES["default"]["NAME"] = BASE_DIR / "testing.sqlite3"
MEDIA_ROOT = os.path.join(BASE_DIR, "testing_media")
