"""
Dev launcher — runs the IXOPE app on Windows / non-Radxa machines.

Usage:
    python run_dev.py

What it does:
    • Adds the parent directory to sys.path so `from ixope...` imports work
      even though we're inside the `ixope` package folder.
    • Sets IXOPE_BASE_PATH to a `./dev_data` subfolder if not already set,
      so captured images / config / logs land alongside the source instead
      of in the user's home directory.
    • Calls ixope.app.main() exactly like `python -m ixope` would.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)

# Force UTF-8 stdout/stderr on Windows so the logger's box-drawing
# characters (═, ✓, ✗) don't trigger cp1252 UnicodeEncodeErrors.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Make `ixope` importable as a top-level package
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

# Keep dev data inside the project so it's easy to wipe / inspect
os.environ.setdefault("IXOPE_BASE_PATH", os.path.join(HERE, "dev_data"))

from ixope.app import main  # noqa: E402

if __name__ == "__main__":
    main()
