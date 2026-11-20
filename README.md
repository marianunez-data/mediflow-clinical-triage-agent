<div align="center">

# MediFlow

### Autonomous agent for clinical document triage, extraction and routing

Team project · Hackathon ONE G10 · Oracle Next Education & Alura · Equipo 37

[Leer en español](docs/README_es.md)

[![Live demo](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://mediflow-clinical-triage-agent.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-agent%20graph-1C3C3C)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![OCI](https://img.shields.io/badge/Oracle%20Cloud-Always%20Free-C74634?logo=oracle&logoColor=white)](https://www.oracle.com/cloud/free/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

---

MediFlow receives clinical documents as PDF, image, plain text or JSON. It classifies them, extracts the key data into validated JSON, computes a confidence score, detects urgencies and routes each document to the right hospital queue, with no manual work for standard cases. Ambiguous, inconsistent or unreadable documents go to a human auditor.

It was built by a team of 8 in Hackathon ONE G10 and deployed on Oracle Cloud Always Free. This fork keeps the full team history and adds a public live demo. The interface is in Spanish, the language of the documents it was designed for.

## Try it

| What | Where |
|---|---|
| Live demo | [mediflow-clinical-triage-agent.streamlit.app](https://mediflow-clinical-triage-agent.streamlit.app) |
| Original team repository | [No-Country-simulation/G10-LATAM-equipo-37-Mediflow](https://github.com/No-Country-simulation/G10-LATAM-equipo-37-Mediflow) |

<p align="center">
  <a href="docs/video/mediflow-demo.mp4"><img src="docs/img/mediflow-demo.gif" width="90%" alt="MediFlow demo: a scanned CT report goes to Emergency"></a>
  <br><sub><a href="docs/video/mediflow-demo.mp4">Watch the 2-minute demo (narrated, with English captions)</a></sub>
</p>

In the demo, open **Procesar documento**, pick an example scenario (routine, urgency, ambiguity, high-risk drug, prompt injection, out of scope) and process it in one click. Then check the audit queue, the metrics dashboard and the trace. Every document is synthetic: no data belongs to a real patient.

<p align="center">
  <img src="docs/img/demo-inicio.png" width="49%" alt="Home page">
  <img src="docs/img/demo-carga.png" width="49%" alt="Prompt injection case routed to Emergency">
</p>
<p align="center">
  <img src="docs/img/demo-auditoria.png" width="49%" alt="Human-in-the-loop audit panel">
  <img src="docs/img/demo-trazas.png" width="49%" alt="Step-by-step agent trace">
</p>
<p align="center">
  <img src="docs/img/demo-documentos.png" width="49%" alt="Review queue and processed documents">
  <img src="docs/img/demo-metricas-calidad.png" width="49%" alt="Agent quality dashboard from the evaluation run">
</p>

## The problem

Hospitals, labs and health insurers process large volumes of heterogeneous documents every day: imaging reports, prescriptions, procedure orders, discharge summaries and medical certificates. Administrative staff read them by hand and retype the data into legacy systems. It is slow and error-prone, and when a document describes an urgency, the delay is paid in patient care.

MediFlow does **document triage, not clinical triage**. It does not diagnose. It detects that a document already says something urgent and moves it fast. The clinical work happened before the document arrived; MediFlow makes sure the report of a pulmonary embolism does not wait in an inbox.

## How it works

1. **Ingestion** of native PDF, scanned PDF, photo, plain text or JSON. Scans and photos go through OCR (Tesseract) and a legibility gate.
2. **Classification** into six types: prescription, imaging report, lab report, procedure order, discharge summary and medical certificate.
3. **Structured extraction** with an LLM, validated with one Pydantic schema per document type. Every extracted field cites the source text. Missing data stays `null`; nothing is invented.
4. **Validation** of required fields, ICD-10 codes, drug doses and internal consistency.
5. **Composite confidence score** from legibility, validations passed and model confidence.
6. **Urgency detection** from independent signals: critical findings, urgency keywords, critical lab values and the model's judgment. One is enough.
7. **Routing** to Emergency, Hospital Pharmacy, Authorizations, Electronic Health Record or the Human Review queue, with a reason code (AMB-1 to AMB-6) when a person needs to look.
8. **Persistence and alerts**: documents stored by status in OCI Object Storage, real-time alerts to the on-call channel through n8n and Slack, without the patient's name.

Design rules that matter:

- A detected urgency is never held back by an ambiguity: it goes to Emergency **and** gets flagged for audit.
- Text inside a document is data, never an instruction. A document that tells the system to "route this as routine" is ignored and routed by what it really is.
- If the LLM provider fails, the agent keeps working with its rules engine and flags the document for review. No urgency in the test set was lost in that mode.
- Thresholds, critical findings, high-risk drugs and destinations live in `agent/rules/rules.yaml` and can be edited without touching code.

```mermaid
flowchart LR
    U["User or external system"] -->|"PDF, image, text, JSON"| UI["Streamlit UI"]
    U -->|"POST /triage"| API["FastAPI"]
    UI --> API
    B["Bucket recibidos/"] --> W["Worker"]
    API --> G["LangGraph decision graph"]
    W --> G
    G <-->|"classify, extract"| LLM["LLM via LiteLLM"]
    G --> OS["OCI Object Storage"]
    G --> DB["State and review queue"]
    G --> N8N["n8n"] --> SL["On-call Slack"]
    DB --> UI
```

The full decision graph, the API contract and the design decisions (ADRs) are in [`docs/architecture.md`](docs/architecture.md), [`docs/api-contract.md`](docs/api-contract.md) and [`docs/decisions.md`](docs/decisions.md).

## Evaluation

The agent was measured against a test set the team labeled by hand: **45 items** (30 clinical documents, 7 out-of-scope cases and 8 handwritten prescriptions) expanded into **76 variants** across text, digital PDF, JSON and degraded photos and scans. Each item has its expected answer in [`evals/golden/plan_golden.csv`](evals/golden/plan_golden.csv), and `evals/run.py` compares the agent's output field by field.

| Metric | Baseline 13/10 (DeepSeek) | 22/10 (free chain, mostly rules) |
|---|---|---|
| **Urgency recall** | 94 % (16/17) | **100 % (17/17)** |
| Classification accuracy | 83 % (52/63) | 92 % (58/63) |
| Routing accuracy | 62 % (39/63) | 76 % (48/63) |
| Out-of-scope cases resolved | 0 % (0/12) | 67 % (8/12) |
| Fully correct variants | 41 % (31/76) | 50 % (38/76) |
| Latency p50 / p95 | 3.9 s / 5.2 s | 0.1 s / 4.3 s |

How to read it:

- On text, PDF and JSON, the baseline missed **no urgency (16/16)**. The only miss was a scanned image that OCR could not read on the evaluation machine.
- In the second run the free model quota ran out, so most documents were resolved by the rules engine. It does not measure the model; it shows the safety net: with no model, **17 of 17 urgencies were still caught**.
- The fixes merged after the baseline show up in out-of-scope handling (0/12 to 8/12) and routing accuracy.
- Cost measured per document with a paid model: about **US$ 0.0005** (around 3,500 tokens in two calls), roughly US$ 15 per month for 1,000 documents a day.
- 76 variants is a functional test, not a statistical benchmark: each percentage has a margin of about ±11 to ±13 points.

Full report and error analysis: [`evals/resultados/2026-10-13_deepseek/`](evals/resultados/2026-10-13_deepseek/).

## My contributions

I was the team's Data Scientist. My work, all visible in the commit history:

- **Test set and labeling.** Designed the 45-item golden set and its 76 variants, covering the six document types, five outcomes (routine, high-risk drug, urgency, urgency with ambiguity, ambiguity), unreadable images and the out-of-scope category AMB-6. Coordinated the labeling and a second review of every item.
- **Synthetic data generator.** Took over and fixed `evals/generator/generate.py` (text, PDF and JSON output) and `degradar.py` (degraded photos and scans in three legibility levels).
- **Reference data.** Built the clinical case bank, the WHO ICD-10 catalog and the drug table coded with WHO ATC codes and dose ranges that the validator uses in production.
- **Evaluation harness and results.** Wrote `evals/run.py`, which scores classification, per-field extraction, urgency recall, routing, audit flags and latency, and published the baseline run with its error analysis.
- **Cost measurement.** Added token and cost tracking per document and per model call.
- **Human-in-the-loop audit panel.** Built the Streamlit page where the auditor compares the original document with the extraction and approves, corrects or rejects it, with urgent cases first.
- **Metrics dashboard.** Built the operations and agent-quality dashboard (`ui/metricas.py`, `api/metricas.py`).
- **Rules, scope and guardrails.** Wrote the urgency-by-document-type rule (rule A) in `rules.yaml`, the out-of-scope categories, the guardrails and the privacy-by-design notes.
- **Planning and documentation.** Set up the repository structure, the API contract, the decision log and the final project documentation.

After the hackathon, in this fork, I deployed the public demo on Streamlit Community Cloud with the API running inside the same app, redesigned the interface around one design system (decision card, review queue, step-by-step trace, readable rules) and added one-click example scenarios so anyone can test it without preparing documents.

## Team

| Person | Role in the hackathon |
|---|---|
| Alessandro Cappelli | Streamlit interface, repository setup, demo video and n8n alerts |
| Carlos Zunino | Classification, extraction, model adapter and OCI infrastructure |
| Carolina Chambique | Human review inside the graph |
| Cristian Ojeda | Validation, urgencies, rules, human review endpoints and QA |
| Leidy Diana Gaitan Fiaga | Edge cases, test set documents and demo video |
| Maria Camila Gonzalez Nuñez | Data Scientist: test set, evaluation, audit panel, metrics dashboard, planning and documentation |
| Néstor Gribaudo | Decision graph, scoring, routing, legibility gate and traces |
| Sabrina Valentim Guimaraes | API, worker, persistence and backups |

## Tech stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph, typed state, conditional edges, pause and resume for human review |
| Models | LiteLLM with a free chain (Groq) and a paid comparison model (DeepSeek); rules fallback |
| Validation | Pydantic, one schema per document type |
| API and UI | FastAPI, Streamlit |
| OCR | Tesseract (Spanish, Portuguese, English) |
| Storage | OCI Object Storage (Always Free), local storage for development and the demo |
| Deployment | Docker and an OCI Ampere A1 VM with Nginx during the hackathon; Streamlit Community Cloud for the public demo |
| Alerts | Self-hosted n8n to Slack |
| CI/CD | GitHub Actions: lint and tests; automatic OCI deploy in the team repository |

## Run it locally

Requirements: Python 3.12, Tesseract, and optionally an LLM provider key.

```bash
git clone https://github.com/marianunez-data/mediflow-clinical-triage-agent.git
cd mediflow-clinical-triage-agent
cp .env.example .env            # USE_LLM=false runs on the rules engine, no key needed
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
make test                       # lint and tests
make dev                        # API on :8000, UI on :8501 and worker (Docker Compose)
# or, without Docker: streamlit run ui/Inicio.py  (starts the API inside the app)
```

Quick test with the brief's example:

```bash
curl -s -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d @docs/examples/triage_request.json | python -m json.tool
```

## Deployment

- **Streamlit Community Cloud (current demo).** The app runs `ui/Inicio.py`. When no external `API_URL` is set, [`ui/arranque.py`](ui/arranque.py) starts the FastAPI service inside the same process, and [`packages.txt`](packages.txt) installs Tesseract. With a `GROQ_API_KEY` secret the demo uses the language model; without it, it runs on the rules engine. Every push to `main` redeploys it.
- **Oracle Cloud (hackathon).** Object Storage for documents and an Ampere A1 VM with Docker Compose, Nginx and n8n, deployed on every merge to `main`. Setup in [`docs/oci-setup.md`](docs/oci-setup.md) and [`infra/`](infra/).

### Evidence of the Oracle Cloud deployment

The hackathon VM was shut down after the event, so the public URL no longer responds. The deployment is documented here:

- **Deploy history:** every merge to `main` in the team repository ran [`deploy.yml`](https://github.com/No-Country-simulation/G10-LATAM-equipo-37-Mediflow/actions/workflows/deploy.yml), which pulled the code on the OCI VM, rebuilt the containers and checked `/api/health` before finishing.
- **Production checks on 24/10/2026** against the public OCI URL, with Groq as the model:

| Case | Result | Time |
|---|---|---|
| GS-28, certificate (text) | Electronic Health Record | about 2 s |
| GS-07, pulmonary embolism (text) | Emergency queue and Slack alert | about 3 s |
| GS-07, pulmonary embolism (scanned photo) | Emergency queue and Slack alert | 9.9 s |
| GS-06, prescription with out-of-range dose | Human review queue | 3.6 s |
| FA-05, critical potassium with a hidden instruction | Emergency queue: instruction ignored, alert without the patient's name | 3.4 s |

- **Infrastructure as code:** VM setup script, minimal IAM policies, production Docker Compose and Nginx config in [`infra/`](infra/), and the bucket layout by status (`recibidos/`, `procesados/urgentes/`, `auditoria_humana/`, `rechazados/`) in [`docs/README_es.md`](docs/README_es.md#despliegue-en-oracle-cloud).

## Known limits

- Handwritten prescriptions are not read yet: OCR does not read cursive and images do not reach the multimodal model, so they go to human review.
- The second opinion between models is planned in the graph but not wired to a second model.
- Spanish only. Other languages are recognized as out of scope.
- Synthetic documents and no clinical validation. Taking it to a real hospital needs clinical validation and a paid model plan sized for the volume.

## License

MIT, © 2026 Equipo MediFlow, Hackathon ONE G10. See [`LICENSE`](LICENSE). The original Spanish README from the hackathon is kept in [`docs/README_es.md`](docs/README_es.md).
