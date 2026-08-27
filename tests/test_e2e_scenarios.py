import pytest
import os
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from src.agent.surveyor_agent import SurveyorAgent
from src.agent.state import AgentState
from src.pii_masking.anonymizer import PIIMaskingManager
from src.guardrails.validators import validate_final_assessment

load_dotenv()

@pytest.fixture(scope="module")
def e2e_agent():
    """Provides a fully compiled agent for end-to-end testing."""
    embedder = OpenAIEmbeddings(model="text-embedding-3-small")
    vs = FAISS.load_local("data/faiss_index", embedder, allow_dangerous_deserialization=True)
    agent = SurveyorAgent(vectorstore=vs)
    return agent.build_graph(), PIIMaskingManager()

def run_claim(graph, pii, claim_id: str, raw_text: str, policy_number: str = None):
    """Helper to run a claim through the full pipeline."""
    masked_text, active_id = pii.mask_pii(raw_text, claim_id=claim_id)
    
    initial_state: AgentState = {
        "claim_id": active_id,
        "policy_number": policy_number,
        "raw_input_text": raw_text,
        "masked_input_text": masked_text,
        "vehicle_age_years": 0.0,
        "has_zero_depreciation": False,
        "has_engine_protect": False,
        "extracted_parts": [],
        "extracted_vehicle_rc": None,
        "rag_clauses": [],
        "memory_history": [],
        "tool_calculations": [],
        "final_assessment": {},
        "policy_status": "UNKNOWN",
        "policy_message": "",
        "verified_add_ons": {},
        "errors": []
    }
    
    result = graph.invoke(initial_state)
    
    if result.get("policy_status") in ["EXPIRED", "NOT_FOUND"]:
        return {"rejected": True, "errors": result.get("errors", []), "policy_status": result["policy_status"]}
        
    assert len(result.get("errors", [])) == 0, f"Agent errors: {result.get('errors')}"
    return validate_final_assessment(result["final_assessment"])

def test_e2e_metal_depreciation(e2e_agent):
    graph, pii = e2e_agent
    # Use POL-TN-8877 which does NOT have Zero Dep, so standard 25% metal depreciation applies
    assessment = run_claim(graph, pii, "E2E-01", "Vehicle TN09ZZ8888, age 3.5 years. Damaged: Front Left Fender (Rs. 5000).", policy_number="POL-TN-8877")
    
    assert not isinstance(assessment, dict), "Claim was rejected unexpectedly"
    item = assessment.line_items[0]
    assert item.category == "METAL"
    assert item.depreciation_percentage == 25.0
    assert item.approved_cost_inr == 3750.0

def test_e2e_zero_dep_tyre_exception(e2e_agent):
    graph, pii = e2e_agent
    # Use POL-DL-4432 which is now active and has Zero Dep
    assessment = run_claim(graph, pii, "E2E-02", "Vehicle DL3CAB9999, age 2.0 years. Damaged: Rear Tyre (Rs. 6000).", policy_number="POL-DL-4432")
    
    assert not isinstance(assessment, dict)
    item = assessment.line_items[0]
    assert item.category == "PLASTIC_RUBBER"
    assert item.depreciation_percentage == 50.0  # PCEC-1 Exception: Tyres still get 50% even with Zero Dep
    assert item.approved_cost_inr == 3000.0

def test_e2e_painting_split(e2e_agent):
    graph, pii = e2e_agent
    # Use POL-TN-8877 which does NOT have Zero Dep, so painting material gets 50% depreciation
    assessment = run_claim(graph, pii, "E2E-03", "Vehicle TN09ZZ8888, age 1.5 years. Damaged: Denting and Painting Labour (Rs. 8000).", policy_number="POL-TN-8877")
    
    assert not isinstance(assessment, dict)
    item = assessment.line_items[0]
    assert item.category == "LABOUR_PAINTING"
    assert item.depreciation_amount_inr == 1000.0  # 50% of the 25% material cost (8000 * 0.25 * 0.50)
    assert item.approved_cost_inr == 7000.0

def test_e2e_mechanical_exclusion(e2e_agent):
    graph, pii = e2e_agent
    # Use POL-TN-8877 which does NOT have Engine Protect
    assessment = run_claim(graph, pii, "E2E-04", "Vehicle TN09ZZ8888, age 3.0 years. Damaged: Engine sump cracked (Rs. 15000).", policy_number="POL-TN-8877")
    
    assert not isinstance(assessment, dict)
    item = assessment.line_items[0]
    assert item.category == "MECHANICAL_EXCLUSION"
    assert item.depreciation_percentage == 100.0
    assert item.approved_cost_inr == 0.0

def test_e2e_policy_gatekeeper_rejection(e2e_agent):
    graph, pii = e2e_agent
    result = run_claim(graph, pii, "E2E-REJECT-01", "Vehicle KA03MN1234, age 4 years. Damaged: Bumper (Rs. 5000).", policy_number="POL-KA-1102")
    
    assert isinstance(result, dict)
    assert result["rejected"] is True
    assert result["policy_status"] == "EXPIRED"
    assert any("COVERAGE REJECTED" in err for err in result["errors"])

def test_e2e_fraud_detection_warning(e2e_agent):
    graph, pii = e2e_agent
    # POL-MH-9981 has Zero Dep, but NO Engine Protect. We lie in the text.
    raw_text = "Vehicle MH02AB1234, age 3 years. Damaged: Engine sump (Rs. 15000). I have Engine Protect cover."
    
    assessment = run_claim(graph, pii, "E2E-FRAUD-01", raw_text, policy_number="POL-MH-9981")
    
    assert not isinstance(assessment, dict)
    item = assessment.line_items[0]
    assert item.category == "MECHANICAL_EXCLUSION"
    assert item.approved_cost_inr == 0.0
    
    # Improved assertion: prints the actual warnings if it fails
    assert len(assessment.system_warnings) > 0, f"Expected system warnings, but got empty list. Full assessment: {assessment}"
    
    # Join all warnings into one string for easier checking
    all_warnings = " ".join(assessment.system_warnings)
    assert "Engine Protect" in all_warnings and "NOT active" in all_warnings, \
        f"Expected 'Engine Protect' and 'NOT active' in warnings. Actual warnings: {assessment.system_warnings}"