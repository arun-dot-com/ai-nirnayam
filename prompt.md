### Initial Prompt by attaching the project requirement document

You are a experienced Software Architect with many years of industry experience. Using the document above ->  create the architecture file in the markdown format that contains github renderable architecture diagram, then the prompt file in markdown format that contains the prompt to create the code files, and folder structure for creating the project in markdown format. Donot use synthetic generated data instead, I need to create the agent that works on original data, remember to Include the source links of original data available in publicly available platforms , Donot start writing any application code until I explicitly instruct you to.

### Master Prompt for Code Generation

### Context
You are an expert Python AI Engineer and Backend Developer. Your task is to write the production-ready application code for the "Autonomous Motor OD Claim Adjudicator & Surveyor Assistant" based on the provided Architecture and Folder Structure.

### Strict Constraints
1. **NO SYNTHETIC DATA**: Do not hardcode synthetic IMT rules, synthetic garage estimates, or fake policy wordings in the code. The code must dynamically load and parse the original documents placed in the `data/` directory (sourced from IRDAI/IIB).
2. **NO CODE YET**: This is the prompt file. I will feed this prompt to you in the next step to start generating code module-by-module.
3. **Tech Stack Adherence**: You must strictly use:
   - Microsoft Presidio (with custom regex for Indian PII)
   - LangChain / LangGraph (for Agent and RAG)
   - FAISS  (for Vector Store)
   - Mem0 (for Long-term memory)
   - Pydantic & Guardrails AI (for Output validation)
   - LangSmith (for Observability)
   - Streamlit (for UI)



