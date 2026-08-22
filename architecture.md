# Architecture Document: Nirnayam (Autonomous Motor OD Claim Adjudicator)

## 1. High-Level System Overview
**Nirnayam** is an enterprise-grade, multi-agent system designed to process Indian Motor Own Damage (OD) claims. It ingests unstructured garage estimates, enforces strict policy verification via a database gatekeeper, sanitizes PII using an in-memory Redis store, calculates depreciation using deterministic Indian Motor Tariff (IMT) tools, checks historical memory for NCB anomalies, and outputs a strictly validated, mathematically sound JSON assessment with built-in fraud detection warnings.

## 2. System Architecture Diagram
*Note: This diagram uses Mermaid.js and is fully renderable on GitHub.*

```mermaid
flowchart TD
    subgraph "User Interface & Input"
        A[Surveyor Dashboard: Streamlit UI] -->|1. Policy Number| B{Policy Gatekeeper}
        A -->|2. Raw Claim Text| C[PII Masking Layer]
    end

    subgraph "Verification & Privacy Layer"
        B -->|SQLite DB Lookup| D[(Policy Registry: nirnayam_policies.db)]
        D -->|Active Policy & True Add-ons| E[Inject Verified State]
        D -->|Expired/Invalid| F[Hard Reject Claim]
        
        C -->|Microsoft Presidio| G[Anonymized Text]
        G -->|Store Mapping with 24h TTL| H[(Redis: PII Mapping Store)]
    end

    subgraph "Knowledge & Memory Layer"
        I[Original Data: IRDAI, IIB, Insurer Wordings] --> J[IMT & Policy RAG Pipeline]
        J --> K[(Vector DB: FAISS)]
        L[Historical Claims & NCB Data] --> M[Mem0 Long-Term Memory]
    end

    subgraph "Autonomous Agent & Tool Layer"
        E --> N[Surveyor Adjudicator Agent: LangGraph]
        G --> N
        K -->|Retrieves IMT Clauses| N
        M -->|Retrieves Claim History| N
        
        N <-->|Tool Calling| O[IMT Depreciation Calculator]
        N <-->|Tool Calling| P[Labor & Painting Rate Master]
        N <-->|Tool Calling| Q[Parts Category Classifier]
    end

    subgraph "Validation, Fraud & Observability Layer"
        N --> R[Guardrails: Pydantic Validators]
        R -->|Math Parity & Schema Checks| S{Discrepancy Detector}
        S -->|Flags Text vs DB mismatches| T[Final Structured JSON Output]
        
        U[LangSmith Observability] -.->|Traces & Token Costs| N
        U -.->|Monitors| R
    end

    subgraph "Final Output"
        T --> V[UI: Financial Summary & Line Items]
        H -->|De-anonymization| W[Final Survey Sign-off Report]
    end