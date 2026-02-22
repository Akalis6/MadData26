import json
from pathlib import Path

from runModel import _enforce_schema, extract_json, generate_json


payload = json.loads(Path("ai/test_payload.json").read_text(encoding="utf-8"))

print("=== Live model run ===")
print(json.dumps(generate_json(payload), indent=2, ensure_ascii=False))

print("\n=== Parser simulation: fenced JSON ===")
fenced = """```json
{\"recommended_programs\":[{\"name\":\"Data Science Certificate\",\"feasibility_score_0_100\":65,\"why\":\"Good fit\"}],\"career_paths\":[\"Data Scientist\"],\"pros\":[\"Strong match\"],\"cons\":[\"Extra stats coursework\"],\"next_steps\":[\"Take STAT 340\",\"Meet advisor\",\"Plan capstone\"]}
```"""
print(json.dumps(_enforce_schema(extract_json(fenced) or {}, payload), indent=2, ensure_ascii=False))

print("\n=== Parser simulation: prefixed text + JSON ===")
prefixed = "Model answer follows: {\"recommended_programs\":[{\"name\":\"Digital Studies Certificate\",\"feasibility_score_0_100\":45,\"why\":\"Interdisciplinary skill-building\"}],\"career_paths\":[\"BI Developer\"],\"pros\":[\"Portfolio growth\"],\"cons\":[\"Heavier writing load\"],\"next_steps\":[\"Take LIS 461\",\"Take JOURN 601\",\"Meet advisor\"]} Thanks!"
print(json.dumps(_enforce_schema(extract_json(prefixed) or {}, payload), indent=2, ensure_ascii=False))

print("\n=== Parser simulation: no JSON (fallback expected) ===")
no_json = "I cannot provide output in JSON right now."
print(json.dumps(_enforce_schema(extract_json(no_json) or {}, payload), indent=2, ensure_ascii=False))