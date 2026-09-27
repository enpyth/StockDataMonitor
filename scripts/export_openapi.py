import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.main import app  # noqa: E402

output = ROOT / "apps" / "web" / "openapi.json"
output.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
print(f"Wrote {output}")
