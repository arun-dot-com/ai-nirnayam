### `execution-steps.md` (Updated to reflect the completed build & how to run)

# Project Execution & Build History

## Build History (Completed Steps)
This project was built in a strict, modular sequence to ensure enterprise-grade reliability at every layer:

- ✅ **Step 1**: `configs/`, `data/` setup, and `src/pii_masking/` (Custom Presidio Recognizers for Indian DL, RC, VIN + Redis mapping).
- ✅ **Step 2**: `src/ingestion/` and `src/rag/` (PDF parsing of real IRDAI/IIB documents and FAISS Vector Store setup).
- ✅ **Step 3**: `src/memory/` (Mem0 integration for NCB and claim history tracking).
- ✅ **Step 4**: `src/tools/` (Deterministic MCP tools for Depreciation, Labour rates, and Part classification).
- ✅ **Step 5**: `src/agent/` (LangGraph Surveyor Agent orchestrating the tools, RAG, and Memory).
- ✅ **Step 6**: `src/guardrails/` (Pydantic schemas and Math Parity validators).
- ✅ **Step 7**: `src/observability/` and `src/ui/` (LangSmith setup and Streamlit dashboard).
- ✅ **Step 8**: `src/policy/` & Fraud Detection (SQLite Policy Gatekeeper, Hard Rejections, and Discrepancy Warnings).


## How to Run the Application

### Prerequisites
1. Python 3.10+ installed.
2. Poetry installed (`pip install poetry`).
3. A running local Redis instance (via Docker: `docker run -d --name redis-local -p 6379:6379 redis:latest`).
4. An `.env` file configured with your `OPENAI_API_KEY` and `REDIS_URL`.

### Installation & Setup

# 1. Clone the repository and navigate to the folder
```bash
cd autonomous-motor-od-adjudicator
```
# 2. Install dependencies via Poetry
```bash
poetry install
```
# 3. (Optional) Run the full test suite to verify all 26 tests pass
```bash
poetry run pytest tests/ -v -s
```

# 4. Running the UI
```bash
poetry run streamlit run src/ui/streamlit_app.py
```
*The application will open at `http://localhost:8501`.*

### Execution Flow in the UI
1. **Policy Gatekeeper:** Enter a Policy Number (e.g., `POL-MH-9981`) and click **Verify Policy**.
   - *If Expired/Invalid:* The system hard-rejects the claim immediately.
   - *If Active:* The system reveals the claim entry tabs and auto-populates the verified add-ons.
2. **Claim Entry:** 
   - Use **AI Auto-Extract** to paste messy garage estimates.
   - Or use **Manual Structured Entry** to input exact parts and costs.
3. **Adjudication:** Click process. The system will mask PII, retrieve RAG clauses, calculate deterministic depreciation, and check for fraud.
4. **Final Report:** View the financial summary, line-item breakdowns, and any system warnings regarding policy discrepancies.


### Why these updates matter:
1. **The Architecture Diagram** now clearly shows the **SQLite Gatekeeper** acting as a bouncer before the AI even gets to look at the claim. This is your biggest selling point for enterprise security.
2. **The Folder Structure** now accurately reflects the `src/policy/` directory and the comprehensive `tests/` suite, proving the project's maturity.
3. **The Execution Steps** transitions the document from a "to-do list" into a "deployment manual," which is exactly what a Senior Engineer would hand over to a DevOps team or a new developer joining the project.
