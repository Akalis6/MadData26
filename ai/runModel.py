"""Offline UW-Madison advising inference using Llama-3.2-1B-Instruct."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from threading import Lock
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_ID = "meta-llama/Llama-3.2-1B-Instruct"
MAX_NEW_TOKENS = 220

_SYSTEM_PROMPT = (
    "You are a UW-Madison College of Letters & Science academic and career advisor. "
    "Use the student context to produce practical recommendations. "
    "Return ONLY a valid JSON object with this exact schema: "
    "{"
    '\"recommended_programs\": ['
    '{\"name\": string, \"feasibility_score_0_100\": number, \"why\": string}'
    "], "
    '\"career_paths\": [string], '
    '\"pros\": [string], '
    '\"cons\": [string], '
    '\"next_steps\": [string]'
    "}. "
    "Do not include any markdown, code fences, or explanatory text outside JSON."
)

_MODEL = None
_TOKENIZER = None
_MODEL_LOCK = Lock()


def _load_model_once() -> tuple[AutoTokenizer, AutoModelForCausalLM]:
    """Lazily load tokenizer/model once per process and keep on CPU."""
    global _MODEL, _TOKENIZER

    if _MODEL is not None and _TOKENIZER is not None:
        return _TOKENIZER, _MODEL

    with _MODEL_LOCK:
        if _MODEL is not None and _TOKENIZER is not None:
            return _TOKENIZER, _MODEL

        # CPU inference tuning
        if torch.get_num_threads() < 4:
            torch.set_num_threads(max(4, os.cpu_count() or 4))

        local_only = os.getenv("HF_HUB_OFFLINE", "0") == "1"

        _TOKENIZER = AutoTokenizer.from_pretrained(
            MODEL_ID,
            local_files_only=local_only,
        )

        _MODEL = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
            local_files_only=local_only,
        )
        _MODEL.to("cpu")
        _MODEL.eval()

        if _TOKENIZER.pad_token_id is None:
            _TOKENIZER.pad_token = _TOKENIZER.eos_token

    return _TOKENIZER, _MODEL


def _extract_last_json_object(text: str) -> dict[str, Any]:
    """Extract the last valid JSON object from text."""
    decoder = json.JSONDecoder()
    last_obj: dict[str, Any] | None = None

    for idx, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, end = decoder.raw_decode(text[idx:])
            if isinstance(obj, dict):
                remainder = text[idx + end :].strip()
                if not remainder:
                    return obj
                last_obj = obj
        except json.JSONDecodeError:
            continue

    if last_obj is None:
        raise ValueError("No valid JSON object found in model output.")

    return last_obj


def _enforce_schema(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize model output into the required response schema."""

    def ensure_list_of_strings(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    programs = []
    for item in data.get("recommended_programs", []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        why = str(item.get("why", "")).strip()
        score_raw = item.get("feasibility_score_0_100", 0)
        try:
            score = float(score_raw)
        except (TypeError, ValueError):
            score = 0.0
        score = max(0.0, min(100.0, score))
        if name:
            programs.append(
                {
                    "name": name,
                    "feasibility_score_0_100": score,
                    "why": why,
                }
            )

    return {
        "recommended_programs": programs,
        "career_paths": ensure_list_of_strings(data.get("career_paths")),
        "pros": ensure_list_of_strings(data.get("pros")),
        "cons": ensure_list_of_strings(data.get("cons")),
        "next_steps": ensure_list_of_strings(data.get("next_steps")),
    }


def generate_json(advising_payload: dict) -> dict:
    """Generate deterministic advising JSON from structured student context."""
    tokenizer, model = _load_model_once()

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Student context JSON:\n"
                f"{json.dumps(advising_payload, ensure_ascii=False)}"
            ),
        },
    ]

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(prompt, return_tensors="pt")
    input_ids = inputs["input_ids"].to("cpu")
    attention_mask = inputs.get("attention_mask")
    if attention_mask is not None:
        attention_mask = attention_mask.to("cpu")

    with torch.inference_mode():
        generated = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            use_cache=True,
            pad_token_id=tokenizer.pad_token_id,
        )

    output_tokens = generated[0][input_ids.shape[1] :]
    raw_text = tokenizer.decode(output_tokens, skip_special_tokens=True)
    parsed = _extract_last_json_object(raw_text)
    return _enforce_schema(parsed)


def _main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python ai/runModel.py <payload.json>", file=sys.stderr)
        return 2

    payload_path = Path(sys.argv[1])
    if not payload_path.exists():
        print(f"File not found: {payload_path}", file=sys.stderr)
        return 2

    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        result = generate_json(payload)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())