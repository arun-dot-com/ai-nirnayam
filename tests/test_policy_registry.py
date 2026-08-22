import pytest
import os
from datetime import date, timedelta
from src.policy.policy_registry import PolicyRegistry

@pytest.fixture(scope="module")
def registry():
    """Provides a fresh PolicyRegistry instance for testing."""
    test_db = "data/test_policies.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    reg = PolicyRegistry(db_path=test_db)
    yield reg
    # Cleanup
    if os.path.exists(test_db):
        os.remove(test_db)

def test_verify_active_policy(registry):
    """Test that an active policy is correctly verified."""
    # The seeded data includes POL-MH-9981 which is active
    result = registry.verify_by_policy_number("POL-MH-9981")
    assert result["status"] == "ACTIVE"
    assert result["policy_details"]["has_zero_dep"] is True
    assert result["policy_details"]["has_engine_protect"] is False

def test_verify_expired_policy(registry):
    """Test that an expired policy is correctly rejected."""
    # The seeded data includes POL-KA-1102 which is expired
    result = registry.verify_by_policy_number("POL-KA-1102")
    assert result["status"] == "EXPIRED"
    assert "expired" in result["message"].lower()

def test_verify_invalid_policy(registry):
    """Test that a non-existent policy number returns NOT_FOUND."""
    result = registry.verify_by_policy_number("POL-FAKE-9999")
    assert result["status"] == "NOT_FOUND"
    assert "No record found" in result["message"]

def test_add_and_verify_new_policy(registry):
    """Test adding a new policy and verifying it."""
    today = date.today()
    end_date = (today + timedelta(days=30)).strftime("%Y-%m-%d")
    start_date = today.strftime("%Y-%m-%d")
    
    success, msg = registry.add_policy(
        "POL-TEST-NEW", "TS09AB1234", "Test User", 
        start_date, end_date, zero_dep=False, engine_protect=True
    )
    assert success is True
    
    result = registry.verify_by_policy_number("POL-TEST-NEW")
    assert result["status"] == "ACTIVE"
    assert result["policy_details"]["has_engine_protect"] is True