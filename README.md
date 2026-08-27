# 🚗 Nirnayam: Autonomous Motor OD Claims Adjudicator

[![CI: Pull Request Validation](https://github.com/arun-dot-com/ai-nirnayam/actions/workflows/ci.yml/badge.svg)](https://github.com/arun-dot-com/ai-nirnayam/actions/workflows/ci.yml)
[![CD: Build, Push & Deploy](https://github.com/arun-dot-com/ai-nirnayam/actions/workflows/cd.yml/badge.svg)](https://github.com/arun-dot-com/ai-nirnayam/actions/workflows/cd.yml)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)

**Nirnayam** (Sanskrit for "Decision" or "Resolution") is an enterprise-grade, autonomous AI agent designed to automate and validate Motor Insurance Own Damage (OD) claim assessments. It combines Retrieval-Augmented Generation (RAG), agentic tool-calling, and strict deterministic guardrails to deliver accurate, fraud-resistant, and PII-compliant claim adjudications in seconds.

---

## ✨ Key Features

- **🔒 Privacy-First PII Masking**: Utilizes Microsoft Presidio with custom Indian entity recognizers (PAN, Driving Licence, Vehicle RC, VIN). Maps and stores anonymized tokens in Upstash Redis with a strict 24-hour TTL.
- **🛡️ Policy Gatekeeper**: Instantly validates policy numbers, active status, and add-ons (Zero Depreciation, Engine Protect) against a local SQLite registry before processing.
- **🧠 Agentic Reasoning (LangGraph)**: A multi-node surveyor agent that dynamically retrieves IMT clauses, calculates depreciation, classifies parts (Metal, Plastic, Consumables, Mechanical Exclusions), and validates labor/painting rates.
- **⚖️ Deterministic Guardrails**: Pydantic-based schema validation and mathematical parity checks ensure the LLM cannot hallucinate approved amounts or bypass policy exclusions.
- **📊 Enterprise Observability**: Full tracing, token usage, and latency monitoring via LangSmith.
- **🚀 Production-Ready DevOps**: Multi-stage Docker builds, automated CI/CD via GitHub Actions, and seamless deployment to Streamlit Community Cloud.

---

## 🏗️ System Architecture

For detailed system design and component interactions, see the [Architecture Document](architecture.md).

## 🛠️ Tech Stack

| Category | Technologies |
| :--- | :--- |
| **Core Framework** | Python 3.12, Streamlit |
| **Agentic AI** | LangGraph, LangChain, OpenAI (GPT-4o / text-embedding-3-small) |
| **Data & Storage** | FAISS (Vector DB), Upstash Redis, SQLite, Mem0 |
| **Security & Privacy** | Microsoft Presidio, Pydantic Guardrails |
| **DevOps & CI/CD** | Docker, Docker Compose, GitHub Actions, Poetry |
| **Observability** | LangSmith |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+ and [Poetry](https://python-poetry.org/)
- Docker & Docker Compose (Recommended for production-like local setup)
- An [OpenAI API Key](https://platform.openai.com/)
- An [Upstash Redis](https://upstash.com/) URL (Free tier works perfectly)

### Option 1: Run Locally with Docker (Recommended)
This is the exact same environment used in production.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/arun-dot-com/ai-nirnayam.git
   cd ai-nirnayam
   ```
2. **Configure Environment Variables**:
   Create a `.env` file in the root directory:
   ```env
   OPENAI_API_KEY=sk-proj-your-openai-key
   REDIS_URL=rediss://default:your-password@your-region.upstash.io:6379
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=lsv2_pt-your-langsmith-key
   LANGCHAIN_PROJECT=nirnayam-local
   ```
3. **Start the application**:
   ```bash
   docker compose up -d --build
   ```
4. **Access the UI**: Open your browser and navigate to [http://localhost:8501](http://localhost:8501).

### Option 2: Run Locally with Poetry (Development)
```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Run the Streamlit app
streamlit run src/ui/streamlit_app.py
```

For detailed execution instructions, see the [Execution steps](execution-steps.md).

---

## 🌐 Deployment

### Streamlit Community Cloud
1. Fork or connect this repository to [Streamlit Cloud](https://share.streamlit.io/).
2. Set the Main file path to: `src/ui/streamlit_app.py`
3. Add your `OPENAI_API_KEY` and `REDIS_URL` in the **Advanced Settings > Secrets** (in TOML format).
4. Click **Deploy**. *(Note: If the repo is private, the deployed app will also be private).*

### Docker Hub
Production-ready images are automatically built and pushed to Docker Hub on every merge to `main`:
```bash
docker pull arundotcom/nirnayam:latest
```
---
## ⚙️ CI/CD Pipeline

This project enforces strict quality gates via GitHub Actions:

- **On Pull Request (`ci.yml`)**:
  - 📦 Dependency & Lockfile validation
  - ⚙️ YAML Configuration structure checks
  - 🔍 Python syntax & Ruff linting
  - 📐 Pydantic Schema validation
  - 🧪 Unit, Integration (Redis), and E2E Agent tests
- **On Push to `main` or Tag (`cd.yml`)**:
  - 🔒 Full pre-deployment test suite execution
  - 🐳 Multi-stage Docker image build
  - 📦 Push to Docker Hub (`arundotcom/nirnayam`)
  - ✅ Automated health-check verification
  - 🏷️ Automatic GitHub Release generation (on `v*` tags)

---
## 📂 Project Structure

For folder structure, see the [Folder Structure](folder-structure.md).
