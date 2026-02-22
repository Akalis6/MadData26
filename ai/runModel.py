"""Offline UW-Madison advising inference using Llama-3.2-1B-Instruct."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from threading import Lock
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_ID = "meta-llama/Llama-3.2-1B-Instruct"
MAX_NEW_TOKENS = 170

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
    "Do not include markdown, code fences, prose, or any text outside JSON. "
    "Use backend-provided feasibility_score, completion_pct, estimated_semesters_needed, and estimated_graduation_delay as authoritative inputs. "
    "Do NOT compute or invent feasibility metrics and do NOT override provided feasibility_score values. "
    "recommended_programs MUST include at least 1 item if candidate_programs were provided. "
    "next_steps MUST include at least 3 concrete action items."
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

        cpu_count = os.cpu_count() or 4
        if torch.get_num_threads() < 4:
            torch.set_num_threads(max(4, cpu_count))
        if hasattr(torch, "set_num_interop_threads"):
            torch.set_num_interop_threads(min(8, max(2, cpu_count // 2)))

        local_only = os.getenv("HF_HUB_OFFLINE", "0") == "1"

        _TOKENIZER = AutoTokenizer.from_pretrained(
            MODEL_ID,
            local_files_only=local_only,
        )

        _MODEL = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
            local_files_only=local_only,
        )
        _MODEL.to("cpu")
        _MODEL.eval()

        if _TOKENIZER.pad_token_id is None:
            _TOKENIZER.pad_token = _TOKENIZER.eos_token

    return _TOKENIZER, _MODEL


def _clean_json_like_text(text: str) -> str:
    """Remove common wrapper formatting around model JSON output."""
    cleaned = text.strip()

    fenced_match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if fenced_match:
        cleaned = fenced_match.group(1).strip()

    # Remove trailing commas before a close brace/bracket (common JSON5-ish artifact).
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return cleaned


def _debug_raw_output(raw_text: str) -> None:
    """Optionally print and persist raw model output for parser debugging."""
    if os.getenv("ADVISOR_DEBUG", "0") != "1":
        return

    print("[advisor-debug] Failed to parse model JSON. Raw output follows:", file=sys.stderr)
    print(raw_text, file=sys.stderr)

    debug_path = Path(tempfile.gettempdir()) / "advisor_model_raw.txt"
    try:
        debug_path.write_text(raw_text, encoding="utf-8")
        print(f"[advisor-debug] Raw output saved to {debug_path}", file=sys.stderr)
    except OSError as exc:
        print(f"[advisor-debug] Could not save raw output: {exc}", file=sys.stderr)


def extract_json(text: str) -> dict[str, Any] | None:
    """Extract the best valid JSON object from model text or return None."""
    cleaned = _clean_json_like_text(text)

    candidates: list[dict[str, Any]] = []

    # 1) Try direct parse.
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            candidates.append(obj)
    except json.JSONDecodeError:
        pass

    # 2) Scan for balanced {...} blocks and collect valid objects.
    start_idx = None
    depth = 0
    in_string = False
    escape = False

    for idx, ch in enumerate(cleaned):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue

        if ch == "{":
            if depth == 0:
                start_idx = idx
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start_idx is not None:
                    candidate = cleaned[start_idx : idx + 1]
                    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
                    try:
                        obj = json.loads(candidate)
                        if isinstance(obj, dict):
                            candidates.append(obj)
                    except json.JSONDecodeError:
                        start_idx = None
                        continue

    if not candidates:
        return None

    required = {"recommended_programs", "next_steps"}
    for candidate in candidates:
        if required.issubset(candidate.keys()):
            return candidate

    return candidates[0]


def _timeline_context(candidate: dict[str, Any], advising_payload: dict[str, Any]) -> tuple[str, float, float]:
    """Build timeline text and numeric timeline context from backend-provided fields."""
    sem_raw = candidate.get("estimated_semesters_needed", advising_payload.get("estimated_semesters_needed"))
    delay_raw = candidate.get("estimated_graduation_delay", advising_payload.get("estimated_graduation_delay", 0))
    year = candidate.get("current_year", advising_payload.get("current_year"))
    expected_grad = candidate.get("expected_graduation", advising_payload.get("expected_graduation"))

    try:
        sem = float(sem_raw) if sem_raw is not None else 0.0
    except (TypeError, ValueError):
        sem = 0.0
    try:
        delay = float(delay_raw) if delay_raw is not None else 0.0
    except (TypeError, ValueError):
        delay = 0.0

    timeline_bits = []
    if sem > 0:
        timeline_bits.append(f"estimated to finish in {sem:g} semester(s)")
    if delay > 0:
        timeline_bits.append(f"with an estimated graduation delay of {delay:g} semester(s)")
    else:
        timeline_bits.append("with no estimated graduation delay")
    if expected_grad:
        timeline_bits.append(f"targeting {expected_grad}")
    if year:
        timeline_bits.append(f"from your current {year} standing")

    return " and ".join(timeline_bits), sem, delay


def _fallback_programs_from_payload(advising_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Build deterministic fallback recommendations from candidate_programs."""
    fallback: list[dict[str, Any]] = []

    for candidate in advising_payload.get("candidate_programs", []):
        if not isinstance(candidate, dict):
            continue

        name = str(candidate.get("name", "")).strip()
        if not name:
            continue

        feasibility_raw = candidate.get("feasibility_score")
        completion_raw = candidate.get("completion_pct", 0)
        try:
            completion_pct = float(completion_raw)
        except (TypeError, ValueError):
            completion_pct = 0.0
        completion_pct = max(0.0, min(100.0, completion_pct))

        if feasibility_raw is not None:
            try:
                score = float(feasibility_raw)
            except (TypeError, ValueError):
                score = completion_pct
        else:
            score = completion_pct
        score = max(0.0, min(100.0, score))

        remaining = candidate.get("remaining_courses", [])
        remaining_list = [str(course).strip() for course in remaining if str(course).strip()] if isinstance(remaining, list) else []
        remaining_count = len(remaining_list)

        timeline_text, _, _ = _timeline_context(candidate, advising_payload)
        why = f"{completion_pct:.0f}% complete"
        if remaining_list:
            why += f" with {remaining_count} course(s) remaining"
        if timeline_text:
            why += f" and {timeline_text}"
        if remaining_list:
            why += f": {', '.join(remaining_list[:4])}"

        fallback.append(
            {
                "name": name,
                "feasibility_score_0_100": score,
                "why": why,
                "_sort_feasibility": score,
                "_sort_completion": completion_pct,
                "_sort_remaining": remaining_count,
            }
        )

    fallback.sort(
        key=lambda item: (item["_sort_feasibility"], item["_sort_completion"], -item["_sort_remaining"]),
        reverse=True,
    )

    cleaned = []
    for item in fallback[:3]:
        cleaned.append(
            {
                "name": item["name"],
                "feasibility_score_0_100": item["feasibility_score_0_100"],
                "why": item["why"],
            }
        )
    return cleaned


def _fallback_next_steps(advising_payload: dict[str, Any], programs: list[dict[str, Any]]) -> list[str]:
    """Build deterministic next steps when model omits them."""
    steps: list[str] = []

    candidate_by_name = {
        str(c.get("name", "")).strip(): c
        for c in advising_payload.get("candidate_programs", [])
        if isinstance(c, dict)
    }

    if programs:
        top_program = programs[0]
        top_candidate = candidate_by_name.get(top_program.get("name", ""), {})
        timeline_text, sem, delay = _timeline_context(top_candidate if isinstance(top_candidate, dict) else {}, advising_payload)
        step = f"Prioritize {top_program['name']} this semester and map remaining requirements into your graduation plan"
        if timeline_text:
            step += f" ({timeline_text})"
        steps.append(step + ".")
        if sem > 0:
            steps.append(f"Plan a term-by-term schedule for the next {sem:g} semester(s) to stay on track.")
        if delay > 0:
            steps.append("Meet with an L&S advisor this month to reduce projected graduation delay risks.")

    all_remaining: list[str] = []
    for candidate in advising_payload.get("candidate_programs", []):
        if isinstance(candidate, dict):
            remaining = candidate.get("remaining_courses", [])
            if isinstance(remaining, list):
                for course in remaining:
                    course_str = str(course).strip()
                    if course_str:
                        all_remaining.append(course_str)

    unique_remaining = sorted(set(all_remaining))
    if unique_remaining:
        steps.append(
            "Meet with an L&S advisor to confirm sequencing for: " + ", ".join(unique_remaining[:5]) + "."
        )

    steps.append("Use your next registration window to enroll in at least one remaining certificate/major-support course.")
    steps.append("Update your resume and LinkedIn with project work aligned to your top recommended program.")

    seen = set()
    deduped_steps = []
    for step in steps:
        if step not in seen:
            seen.add(step)
            deduped_steps.append(step)

    return deduped_steps[:6]


def _fallback_career_paths(advising_payload: dict[str, Any], programs: list[dict[str, Any]]) -> list[str]:
    """Build deterministic career path suggestions from interests/programs."""
    mapped: list[str] = []
    interests = [str(i).strip().lower() for i in advising_payload.get("interests", []) if str(i).strip()]

    if any("data" in i for i in interests) or any("data" in p["name"].lower() for p in programs):
        mapped.extend(["Data Scientist", "Data Analyst", "Business Intelligence Developer"])
    if any("machine" in i or "ai" in i for i in interests):
        mapped.extend(["Machine Learning Engineer", "Applied AI Engineer"])
    if any("software" in i for i in interests) or any("computer" in p["name"].lower() for p in programs):
        mapped.extend(["Software Engineer", "Backend Engineer"])

    if not mapped:
        mapped = ["Software Engineer", "Data Analyst", "Technical Consultant"]

    deduped = []
    seen = set()
    for item in mapped:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped[:5]


def _fallback_pros(advising_payload: dict[str, Any], programs: list[dict[str, Any]]) -> list[str]:
    """Build deterministic pros when model omits them."""
    top = programs[0]["name"] if programs else "the recommended plan"
    candidate_by_name = {
        str(c.get("name", "")).strip(): c
        for c in advising_payload.get("candidate_programs", [])
        if isinstance(c, dict)
    }
    top_candidate = candidate_by_name.get(top, {})
    timeline_text, _, delay = _timeline_context(top_candidate if isinstance(top_candidate, dict) else {}, advising_payload)

    pros = [
        f"{top} is aligned with your completed coursework and current trajectory.",
        "Completing a targeted program can strengthen internship and entry-level job competitiveness.",
    ]
    if timeline_text:
        pros.append(f"Backend timeline estimates indicate this path is {timeline_text}.")
    if delay <= 0:
        pros.append("Current feasibility inputs suggest graduation timing can likely be preserved.")
    return pros[:4]


def _fallback_cons(advising_payload: dict[str, Any], programs: list[dict[str, Any]]) -> list[str]:
    """Build deterministic cons when model omits them."""
    remaining_counts = []
    delays = []
    semesters = []
    for candidate in advising_payload.get("candidate_programs", []):
        if isinstance(candidate, dict):
            remaining = candidate.get("remaining_courses")
            if isinstance(remaining, list):
                remaining_counts.append(len(remaining))
            _, sem, delay = _timeline_context(candidate, advising_payload)
            if sem > 0:
                semesters.append(sem)
            delays.append(delay)

    avg_remaining = (sum(remaining_counts) / len(remaining_counts)) if remaining_counts else 0
    max_delay = max(delays) if delays else 0
    max_sem = max(semesters) if semesters else 0

    cons = [
        "Additional required courses may increase workload in upcoming terms.",
        "Balancing depth in one area may reduce flexibility for unrelated electives.",
    ]
    if max_sem >= 2:
        cons.append(f"Some options may require multi-semester follow-through (up to {max_sem:g} semester(s)).")
    if max_delay > 0:
        cons.append(f"Backend estimates indicate potential graduation delay risk (up to {max_delay:g} semester(s)).")
    elif avg_remaining >= 3:
        cons.append("Several remaining requirements may require careful sequencing to graduate on time.")
    else:
        cons.append("Even with high feasibility, completing requirements still needs consistent term-by-term planning.")
    return cons[:4]


def _enforce_schema(data: dict[str, Any], advising_payload: dict[str, Any]) -> dict[str, Any]:
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

    if not programs:
        programs = _fallback_programs_from_payload(advising_payload)

    career_paths = ensure_list_of_strings(data.get("career_paths"))
    if not career_paths:
        career_paths = _fallback_career_paths(advising_payload, programs)

    pros = ensure_list_of_strings(data.get("pros"))
    if not pros:
        pros = _fallback_pros(advising_payload, programs)

    cons = ensure_list_of_strings(data.get("cons"))
    if not cons:
        cons = _fallback_cons(advising_payload, programs)

    next_steps = ensure_list_of_strings(data.get("next_steps"))
    if not next_steps:
        next_steps = _fallback_next_steps(advising_payload, programs)

    return {
        "recommended_programs": programs,
        "career_paths": career_paths,
        "pros": pros,
        "cons": cons,
        "next_steps": next_steps,
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
            eos_token_id=tokenizer.eos_token_id,
            temperature=0.0,
            top_p=1.0,
        )

    output_tokens = generated[0][input_ids.shape[1] :]
    raw_text = tokenizer.decode(output_tokens, skip_special_tokens=True)
    parsed = extract_json(raw_text)
    if parsed is None:
        _debug_raw_output(raw_text)
        return _enforce_schema({}, advising_payload)

    return _enforce_schema(parsed, advising_payload)


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