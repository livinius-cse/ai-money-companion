import json
import sys
from pathlib import Path

# Add apps/api to sys.path
api_root = str(Path(__file__).resolve().parent.parent)
if api_root not in sys.path:
    sys.path.insert(0, api_root)

from app.main import app

def main():
    schema = app.openapi()
    output_path = Path(__file__).resolve().parent.parent.parent / "web" / "src" / "types" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    print(f"OpenAPI schema successfully written to {output_path}")

if __name__ == "__main__":
    main()
