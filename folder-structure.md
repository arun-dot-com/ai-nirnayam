### `folder-structure.md` (Updated with actual project files)

```markdown
### Folder Structure

```text
autonomous-motor-od-adjudicator/
│
├── .env.example                 # Environment variables template (API keys, DB URLs)
├── .gitignore                   # Git ignore rules
├── pyproject.toml               # Project dependencies and build config (Poetry)
├── poetry.lock                  # Locked dependency versions
├── README.md                    # Project documentation
│
├── configs/                     # Configuration files
│   ├── presidio_recognizers.yaml# Custom regex patterns for Indian PII
│   ├── agent_prompts.yaml       # System prompts for the Surveyor Agent
│   └── logging_config.yaml      # Logging and LangSmith setup
│
├── data/                        # Data storage & Vector Indexes
│   ├── raw_imt_tariffs/         # Source PDFs (Base & Bundled Policies)
│   ├── policy_wordings/         # Source PDFs (Nil Dep, Enhanced Covers)
│   ├── faiss_index/             # Persisted FAISS vector store for RAG
│   ├── mem0_faiss_index/        # Persisted FAISS index for Mem0 memory
│   └── nirnayam_policies.db     # SQLite database for Policy Verification
│
├── src/                         # Source code
│   ├── __init__.py
│   │
│   ├── ingestion/               # Document parsing and chunking
│   │   ├── __init__.py
│   │   ├── pdf_parser.py        # Extracts text from IMT/Policy PDFs
│   │   └── chunking.py          # Semantic chunking for RAG
│   │
│   ├── pii_masking/             # PII Redaction Layer
│   │   ├── __init__.py
│   │   ├── custom_recognizers.py# Indian DL, RC, VIN, PAN recognizers
│   │   └── anonymizer.py        # Presidio wrapper & Redis mapping store
│   │
│   ├── policy/                  # Policy Verification Gatekeeper (NEW)
│   │   ├── __init__.py
│   │   └── policy_registry.py   # SQLite logic for active/expired checks
│   │
│   ├── rag/                     # Retrieval Augmented Generation
│   │   ├── __init__.py
│   │   ├── vector_store.py      # FAISS initialization and loading
│   │   └── retriever.py         # Hybrid retrieval logic for IMT clauses
│   │
│   ├── memory/                  # Long-term Memory
│   │   ├── __init__.py
│   │   └── mem0_manager.py      # Mem0 integration for NCB/Claim history
│   │
│   ├── tools/                   # Deterministic Tool Calling (MCP)
│   │   ├── __init__.py
│   │   ├── depreciation_calc.py # IMT depreciation logic (Age & Category)
│   │   ├── labour_rates.py      # Labour and painting 25/75 split logic
│   │   └── part_classifier.py   # Material classification (Metal, Glass, etc.)
│   │
│   ├── agent/                   # Core Agent Logic
│   │   ├── __init__.py
│   │   ├── surveyor_agent.py    # LangGraph Agent orchestrating the flow
│   │   └── state.py             # Pydantic/TypedDict state management
│   │
│   ├── guardrails/              # Output Validation & Fraud Detection
│   │   ├── __init__.py
│   │   ├── schemas.py           # Pydantic models & Math Parity validators
│   │   └── validators.py        # Wrapper for safe schema validation
│   │
│   ├── observability/           # Tracing
│   │   ├── __init__.py
│   │   └── langsmith_setup.py   # LangSmith callbacks and tracing
│   │
│   └── ui/                      # User Interface
│       ├── __init__.py
│       └── streamlit_app.py     # Streamlit UI (Gatekeeper + Tabs + Reports)
│
└── tests/                       # Comprehensive Testing suite
    ├── __init__.py
    ├── test_pii_masking.py      # Tests for Presidio & Redis integration
    ├── test_policy_registry.py  # Tests for SQLite Gatekeeper logic
    ├── test_tools.py            # Tests for deterministic calculations
    ├── test_guardrails.py       # Tests for JSON schema and math parity
    ├── test_memory.py           # Tests for Mem0 semantic retrieval
    ├── test_ingestion_rag.py    # Tests for PDF parsing and FAISS
    ├── test_agent.py            # Tests for LangGraph state flow
    └── test_e2e_scenarios.py    # End-to-End business logic tests