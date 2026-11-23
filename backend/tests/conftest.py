import os
import tempfile
from pathlib import Path

# Isolate test runs from the real storage before the app modules are imported.
_tmp = Path(tempfile.mkdtemp(prefix="taakkad-test-"))
os.environ["TAAKKAD_DB"] = str(_tmp / "test.db")
os.environ["TAAKKAD_OPT_IN_FILE"] = str(_tmp / "opt_in.jsonl")
os.environ["TAAKKAD_ADMIN_TOKEN"] = "test-only-token"
