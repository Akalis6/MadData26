# ai/runModel.py
import sys, json, os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_ID = "meta-llama/Llama-3.2-1B-Instruct"

_tokenizer = None
_model = None

def get_model():
    global _tokenizer, _model
    if _model is None:
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        _model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            device_map="cpu",
            torch_dtype=torch.float32,
        )
        _model.eval()
    return _tokenizer, _model

def generate_json(advising_payload: dict) -> dict:
    tokenizer, model = get_model()

    # Force structured output (critical for hackathon reliability)
    prompt = f"""
You are an academic and career advisor for UW–Madison (L&S). 
Return ONLY valid JSON with keys:
- recommended_programs: list of objects with {{name, feasibility_score_0_100, why}}
- career_paths: list of strings
- pros: list of strings
- cons: list of strings
- next_steps: list of strings

Student context JSON:
{json.dumps(advising_payload)}
"""

    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=350,
            do_sample=False,
            temperature=0.0,
        )
    text = tokenizer.decode(out[0], skip_special_tokens=True)

    # Try to extract JSON block (simple + effective)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {"error": "Model did not return JSON", "raw": text}
    try:
        return json.loads(text[start:end+1])
    except Exception:
        return {"error": "Failed to parse JSON", "raw": text[start:end+1]}

if __name__ == "__main__":
    # Expect one argument: a JSON string
    payload = json.loads(sys.argv[1])
    result = generate_json(payload)
    print(json.dumps(result))