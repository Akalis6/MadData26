# MadData26

An end-to-end **UW–Madison degree planning and advising prototype** that combines:

- a React + TypeScript planner UI,
- a Node/Express requirement-evaluation backend,
- Convex data models/functions,
- Python data-ingestion/normalization scripts,
- optional local Llama-based advising endpoints.

---

## What this repository contains

This repo is currently organized as a multi-part prototype with parallel experiments:

- `degree-planner-ui/` — main front-end app for uploading DARS PDFs, planning terms, and viewing progress.
- `backend/` — API server for major-progress evaluation and AI-advice endpoint orchestration.
- `convex/` — Convex schema + query functions used by front-end features.
- `scripts/` — one-off and pipeline scripts for scraping, transforming, and normalizing requirement/course datasets.
- `ai/` — local Python model-serving experiments (Flask + custom HTTP server).

---

## Tech stack

- **Frontend:** React 19, TypeScript, Vite, Tailwind, pdfjs-dist, PapaParse
- **Backend API:** Node.js, Express, CORS
- **Data layer:** Convex schema/functions
- **AI services:** Python, Flask, Transformers, local model inference
- **Data tooling:** Python ETL scripts, CSV/JSON normalization

---

## Repository layout

```text
MadData26/
├── ai/                         # Python local LLM utilities and API servers
│   ├── app.py                  # Flask /api/ask endpoint (port 5000)
│   ├── advisor_server.py       # Lightweight /advising endpoint (default 8000)
│   ├── runModel.py             # Local text-generation pipeline wrapper
│   └── test_*.py               # Model/server experiments
│
├── backend/
│   ├── server.js               # Express API (default port 8000)
│   ├── majorProgress.js        # Requirement-group scoring engine
│   ├── aiAdvisor.js            # Llama/Ollama prompt + fallback advice logic
│   └── data/                   # UW-Madison source + normalized datasets
│
├── convex/
│   ├── schema.ts               # Convex tables (courses, majors, plans, etc.)
│   ├── tasks.ts                # Convex query endpoints
│   ├── majors.ts               # Convex mutations/queries for majors
│   ├── studentPlans.ts         # Student plan upsert/query logic
│   └── progress.ts             # Progress-related Convex functions
│
├── degree-planner-ui/
│   ├── src/
│   │   ├── DegreePlannerFrontend.tsx  # Main planner screen
│   │   ├── AILlamaPage.tsx            # AI advisor UI page
│   │   ├── App.tsx                    # Router entry
│   │   └── main.tsx                   # React bootstrapping
│   └── package.json
│
├── scripts/                    # Data extraction/cleanup/transformation scripts
├── package.json                # Root JS dependencies (Convex, shared libs)
└── README.md
```

---

## Core product flow (current state)

1. User uploads a DARS PDF in the UI.
2. Frontend parses course-like rows (PDF text extraction + CSV-style parsing helpers).
3. Student courses are grouped by terms for planner display.
4. Backend `/api/major-progress` evaluates requirement-group completion against normalized major rules.
5. Backend `/api/ai-advice` builds suggestion candidates and attempts Llama/Ollama generation.
6. If AI model is unavailable, backend returns deterministic fallback advising text.

---

## Local setup

> The project is a prototype with multiple sub-apps. Start only the parts you need.

### 1) Install Node dependencies

From repo root:

```bash
npm install
```

From UI folder:

```bash
cd degree-planner-ui
npm install
```

### 2) Run frontend

```bash
cd degree-planner-ui
npm run dev
```

Default Vite URL is typically `http://localhost:5173`.

### 3) Run backend API

```bash
cd backend
node server.js
```

Backend listens on `http://localhost:8000`.

### 4) (Optional) Run Python AI API

```bash
cd ai
python app.py
```

Flask AI endpoint listens on `http://localhost:5000/api/ask`.

---

## API quick reference

### `GET /api/majors`

Returns available majors from normalized requirements.

### `POST /api/major-progress`

Evaluates progress for a major.

**Example payload**

```json
{
  "major": "Computer Sciences",
  "degreeType": "BA",
  "studentCourses": [
    { "courseId": "COMP SCI 300", "credits": 3, "grade": "B" },
    { "courseId": "MATH 222", "credits": 4, "grade": "A" }
  ]
}
```

### `POST /api/ai-advice`

Returns major progress + AI/fallback recommendations.

---

## Data + normalization pipeline

The backend relies on normalized JSON requirement groups at:

`backend/data/normalized/MajorSpecificRequirements.JSON`

Normalization logic lives in:

- `scripts/normalize_major_requirements.py`

This script converts raw grouped requirement rows into machine-evaluable rule types such as:

- `choose_n_courses`
- `min_credits`
- `manual_review`

---

## Convex data model highlights

Key tables defined in `convex/schema.ts` include:

- `CourseTable`
- `MajorsList`
- `MajorReqs`
- `DegreeReqs`
- `StudentPlans`

Queries in `convex/tasks.ts` expose basic collection reads for majors, courses, and requirement datasets.

---

## Known prototype caveats

- Some features point to different local services/ports (`5000`, `8000`, Convex), so integration may require environment cleanup.
- The AI path has multiple implementations (`backend/aiAdvisor.js`, `ai/app.py`, `ai/advisor_server.py`) reflecting experimentation.
- Root `package.json` is minimal and does not orchestrate all sub-project scripts.
- Several data scripts are one-off research utilities and may require path/driver updates before reuse.

---

## Suggested next cleanup steps

If you want to productionize this repo quickly:

1. Add a single top-level `docker-compose.yml` (frontend, backend, model service, convex dev).
2. Centralize env vars (`.env.example`) and standardize ports.
3. Add strict TypeScript/Python linting + tests for parser/evaluator logic.
4. Consolidate AI serving to one interface and remove stale variants.
5. Add seed/import scripts for Convex tables from normalized backend datasets.

---

## License

This project is currently distributed with the repository `LICENSE` file at root.
