import pytest
import os
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from src.agent.surveyor_agent import SurveyorAgent
from src.agent.state import AgentState

load_dotenv()

@pytest.fixture
def compiled_agent():
    """Provides a compiled LangGraph Surveyor Agent for testing."""
    # Use a mock or existing FAISS index for the test
    embedder = OpenAIEmbeddings(model="text-embedding-3-small")
    # Point to the index we built
    vs = FAISS.load_local("data/faiss_index", embedder, allow_dangerous_deserialization=True)
    
    agent = SurveyorAgent(vectorstore=vs)
    return agent.build_graph()

def test_agent_graph_execution(compiled_agent):
    """Test the full LangGraph workflow with a sample masked claim."""
    initial_state: AgentState = {
        "claim_id": "TEST-AGENT-001",
        "policy_number": "POL-MH-9981",          # <-- ADDED
        "raw_input_text": "Irrelevant raw text",
        "masked_input_text": "Vehicle <ANON_IN_VEHICLE_RC_1> age 3 years. Damaged: Front Bumper (Rs. 4000), Painting Labour (Rs. 4000). Has Zero Depreciation cover.",
        "vehicle_age_years": 0.0,
        "has_zero_depreciation": False,
        "has_engine_protect": False,
        "extracted_parts": [],
        "extracted_vehicle_rc": None,
        "rag_clauses": [],
        "memory_history": [],
        "tool_calculations": [],
        "final_assessment": {},
        "policy_status": "UNKNOWN",              # <-- ADDED
        "policy_message": "",                    # <-- ADDED
        "verified_add_ons": {},                  # <-- ADDED
        "errors": []
    }
    
    # Invoke the graph
    result = compiled_agent.invoke(initial_state)
    
    # Assertions
    assert len(result.get("errors", [])) == 0, f"Agent encountered errors: {result.get('errors')}"
    assert result["has_zero_depreciation"] is True
    assert len(result["extracted_parts"]) == 2
    
    # Verify deterministic calculation happened
    calculations = result["tool_calculations"]
    assert len(calculations) == 2
    
    # Check Bumper (Plastic/Rubber, but 0% dep due to Zero Dep)
    bumper_calc = next((c for c in calculations if "Bumper" in c["part_name"]), None)
    assert bumper_calc is not None
    assert bumper_calc["depreciation_percentage"] == 0.0
    assert bumper_calc["approved_cost_inr"] == 4000.0
    
    # Check Painting (25% material, 75% labour, 0% dep on material due to Zero Dep)
    painting_calc = next((c for c in calculations if "Painting" in c["part_name"]), None)
    assert painting_calc is not None
    assert painting_calc["approved_cost_inr"] == 4000.0 # Full approval due to Zero Dep
    
    # Check final summary math
    assert result["final_assessment"]["summary"]["total_claimed_inr"] == 8000.0
    assert result["final_assessment"]["summary"]["total_approved_inr"] == 8000.0