import os
import pytest
from dotenv import load_dotenv
from src.pii_masking.anonymizer import PIIMaskingManager

# CRITICAL: Load environment variables so it picks up your custom REDIS_URL from .env
load_dotenv()

@pytest.fixture(scope="module")
def masking_manager():
    """Provides a PIIMaskingManager instance connected to the configured Redis instance."""
    # We rely on the REDIS_URL from the .env file. No hardcoded localhost overrides.
    manager = PIIMaskingManager(config_path="configs/presidio_recognizers.yaml")
    yield manager
    
    # Note: We do NOT flushdb() here. The anonymizer already sets a 24-hour TTL 
    # on all keys for privacy compliance, so test data will clean itself up automatically.

def test_mask_and_unmask_with_redis(masking_manager):
    """Test that PII is masked, stored in Redis, and successfully unmasked."""
    text = "The driver DL-1420110012345 was driving vehicle MH 02 AB 1234 when the accident occurred."
    claim_id = "TEST-CLAIM-001"
    
    # 1. Mask PII
    masked_text, returned_claim_id = masking_manager.mask_pii(text, claim_id=claim_id)
    assert returned_claim_id == claim_id
    
    # 2. Assert PII is removed from text
    assert "DL-1420110012345" not in masked_text
    assert "MH 02 AB 1234" not in masked_text
    
    # 3. Assert placeholders exist
    assert "<ANON_IN_DRIVING_LICENCE_" in masked_text
    assert "<ANON_IN_VEHICLE_RC_" in masked_text
    
    # 4. Assert data is actually in Redis
    redis_key = f"pii_mapping:{claim_id}"
    redis_data = masking_manager.redis_client.hgetall(redis_key)
    assert len(redis_data) > 0
    
    # 5. Assert unmasking works perfectly
    unmasked_text = masking_manager.unmask_pii(masked_text, claim_id=claim_id)
    assert "DL-1420110012345" in unmasked_text
    assert "MH 02 AB 1234" in unmasked_text
    assert unmasked_text == text

def test_clear_mapping(masking_manager):
    """Test that explicit clearing removes the mapping from Redis."""
    text = "Contact owner at +91-9876543210."
    claim_id = "TEST-CLAIM-002"
    
    masked_text, _ = masking_manager.mask_pii(text, claim_id=claim_id)
    assert "<ANON_IN_PHONE_NUMBER_" in masked_text or "<ANON_PHONE_NUMBER_" in masked_text
    
    # Clear the mapping
    success = masking_manager.clear_mapping(claim_id)
    assert success is True
    
    # Attempt to unmask should return the masked text unchanged
    unmasked_text = masking_manager.unmask_pii(masked_text, claim_id=claim_id)
    assert unmasked_text == masked_text

def test_no_pii_text(masking_manager):
    """Test that text without PII is returned unchanged and no Redis key is created."""
    text = "The front bumper was damaged in a minor collision."
    claim_id = "TEST-CLAIM-003"
    
    masked_text, returned_claim_id = masking_manager.mask_pii(text, claim_id=claim_id)
    
    assert masked_text == text
    # Verify no key was created in Redis for this claim
    redis_key = f"pii_mapping:{claim_id}"
    assert masking_manager.redis_client.exists(redis_key) == 0