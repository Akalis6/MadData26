import json
from pathlib import Path

from runModel import generate_json

payload = json.loads(Path("ai/test_payload.json").read_text(encoding="utf-8"))
print(json.dumps(generate_json(payload), indent=2, ensure_ascii=False))