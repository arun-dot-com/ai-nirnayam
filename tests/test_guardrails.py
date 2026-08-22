import pytest
from src.guardrails.schemas import FinalAssessment
from src.guardrails.validators import validate_final_assessment

def test_valid_math_parity():
    raw_data = {
        "claim_id": "TEST-001",
        "vehicle_age_years": 3.5,
        "policy_status": "ACTIVE",               # <-- MOVED TO ROOT
        "policy_message": "Test policy verified.", # <-- MOVED TO ROOT
        "system_warnings": [],                   # <-- ADDED
        "add_ons_detected": {"zero_depreciation": False, "engine_protect": False},
        "ncb_history_note": "No prior claims.",
        "line_items": [
            {
                "part_name": "Front Bumper",
                "category": "PLASTIC_RUBBER",
                "claimed_cost_inr": 4000.0,
                "depreciation_percentage": 50.0,
                "depreciation_amount_inr": 2000.0,
                "approved_cost_inr": 2000.0,
                "reason": "Standard 50% depreciation for plastic."
            }
        ],
        "summary": {
            "total_claimed_inr": 4000.0,
            "total_approved_inr": 2000.0,
            "total_depreciation_inr": 2000.0
        }
    }
    assessment = validate_final_assessment(raw_data)
    assert assessment.summary.total_approved_inr == 2000.0

def test_invalid_math_parity_claimed():
    raw_data = {
        "claim_id": "TEST-002",
        "vehicle_age_years": 3.5,
        "policy_status": "ACTIVE",               # <-- MOVED TO ROOT
        "policy_message": "Test policy verified.", # <-- MOVED TO ROOT
        "system_warnings": [],                   # <-- ADDED
        "add_ons_detected": {},
        "ncb_history_note": "",
        "line_items": [
            {
                "part_name": "Front Bumper",
                "category": "PLASTIC_RUBBER",
                "claimed_cost_inr": 4000.0,
                "depreciation_percentage": 50.0,
                "depreciation_amount_inr": 2000.0,
                "approved_cost_inr": 2000.0,
                "reason": "Test"
            }
        ],
        "summary": {
            "total_claimed_inr": 5000.0, 
            "total_approved_inr": 2000.0,
            "total_depreciation_inr": 2000.0
        }
    }
    with pytest.raises(ValueError) as exc_info:
        validate_final_assessment(raw_data)
    assert "Math Parity Error: total_claimed_inr" in str(exc_info.value)

def test_invalid_math_parity_formula():
    raw_data = {
        "claim_id": "TEST-003",
        "vehicle_age_years": 3.5,
        "policy_status": "ACTIVE",               # <-- MOVED TO ROOT
        "policy_message": "Test policy verified.", # <-- MOVED TO ROOT
        "system_warnings": [],                   # <-- ADDED
        "add_ons_detected": {},
        "ncb_history_note": "",
        "line_items": [
            {
                "part_name": "Front Bumper",
                "category": "PLASTIC_RUBBER",
                "claimed_cost_inr": 4000.0,
                "depreciation_percentage": 50.0,
                "depreciation_amount_inr": 2000.0,
                "approved_cost_inr": 2000.0,
                "reason": "Test"
            }
        ],
        "summary": {
            "total_claimed_inr": 4000.0,
            "total_approved_inr": 3000.0, 
            "total_depreciation_inr": 2000.0
        }
    }
    with pytest.raises(ValueError) as exc_info:
        validate_final_assessment(raw_data)
    assert "Math Parity Error" in str(exc_info.value)