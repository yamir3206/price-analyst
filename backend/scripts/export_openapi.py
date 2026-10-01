"""Export the FastAPI OpenAPI contract used by repository documentation.

Run from the repository root:

    python backend/scripts/export_openapi.py

The generated file is intentionally committed so coding agents and tools can
inspect the API without importing the application themselves. It must be
regenerated after an API schema, route, or version change.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "backend" / "src"
OUTPUT = ROOT / "docs" / "openapi.json"

if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from price_analyst.main import create_app  # noqa: E402


def main() -> None:
    specification = create_app().openapi()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(specification, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
