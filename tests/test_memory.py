import os
import pytest
from dotenv import load_dotenv

# CRITICAL: Load environment variables BEFORE importing Mem0Manager 
# so the OpenAI embedder can find the API key.
load_dotenv()

from src.memory.mem0_manager import Mem0Manager

# Define skip condition and reason once to keep code clean
SKIP_REASON = "Real OPENAI_API_KEY not found in .env. Skipping live integration test."
SKIP_CONDITION = not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "sk-your-openai-key"

@pytest.fixture
def mem0_manager():
    """Provides a Mem0Manager instance for testing."""
    test_config = {
        "vector_store": {
            "provider": "faiss",
            "config": {
                "collection_name": "test_vehicle_claim_history",
                "path": "./data/test_mem0_faiss_index"
            }
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "text-embedding-3-small"
            }
        }
    }
    return Mem0Manager(config=test_config)

@pytest.mark.skipif(SKIP_CONDITION, reason=SKIP_REASON)
def test_add_and_retrieve_claim_event(mem0_manager):
    """Test adding a claim event and retrieving the distilled facts."""
    anon_vehicle_id = "<ANON_IN_VEHICLE_RC_TEST_1>"
    event_details = "Partial loss claim approved for front left fender and headlamp on 2023-08-10. NCB reset to 0%."
    
    # 1. Add memory
    memory_id = mem0_manager.add_claim_event(anon_vehicle_id, event_details)
    assert memory_id is not None
    
    # 2. Retrieve memory with a semantic query focused on the physical damage
    query = "front left fender claim details"
    results = mem0_manager.get_vehicle_history(anon_vehicle_id, query=query)
    
    # 3. Assert the retrieved memory contains the distilled core facts
    assert len(results) > 0, "Should retrieve at least one relevant memory"
    retrieved_text = results[0]["content"].lower()
    
    # Mem0 extracts atomic facts. We verify the core damage components are stored.
    assert "fender" in retrieved_text or "headlamp" in retrieved_text

@pytest.mark.skipif(SKIP_CONDITION, reason=SKIP_REASON)
def test_update_ncb_status(mem0_manager):
    """Test updating the NCB status and retrieving the distilled fact."""
    anon_vehicle_id = "<ANON_IN_VEHICLE_RC_TEST_2>"
    
    # Update NCB
    mem0_manager.update_ncb_status(
        anonymized_vehicle_id=anon_vehicle_id,
        new_ncb_percentage=35,
        reason="Claim-free year completed upon renewal."
    )
    
    # Retrieve to verify
    results = mem0_manager.get_vehicle_history(anon_vehicle_id, query="current NCB percentage")
    
    assert len(results) > 0
    retrieved_text = results[0]["content"]
    
    # Mem0 distills the core fact. We verify the critical NCB percentage is stored.
    assert "35%" in retrieved_text

@pytest.mark.skipif(SKIP_CONDITION, reason=SKIP_REASON)
def test_empty_history(mem0_manager):
    """Test retrieving history for a vehicle with no prior claims."""
    anon_vehicle_id = "<ANON_IN_VEHICLE_RC_TEST_3>"
    
    results = mem0_manager.get_vehicle_history(anon_vehicle_id, query="past claims")
    
    # Should return empty list, not throw an error
    assert len(results) == 0