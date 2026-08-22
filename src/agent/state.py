from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    # Policy Verification
    policy_number: str     
    policy_status: str  # "ACTIVE", "EXPIRED", "NOT_FOUND"
    policy_message: str
    verified_add_ons: Dict[str, bool]
    # Input & Privacy
    claim_id: str
    raw_input_text: str
    masked_input_text: str
    
    # LLM Extraction Results
    vehicle_age_years: float
    has_zero_depreciation: bool
    has_engine_protect: bool
    extracted_parts: List[Dict[str, Any]] # e.g., [{"name": "Front Bumper", "claimed_cost": 5000}]
    
    # Context Retrieval
    rag_clauses: List[Dict[str, Any]]
    memory_history: List[Dict[str, Any]]
    extracted_vehicle_rc: Optional[str] # The anonymized RC to query memory
    
    # Deterministic Tool Results
    tool_calculations: List[Dict[str, Any]]
    
    # Final Output
    final_assessment: Dict[str, Any]
    errors: List[str]