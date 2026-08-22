import os
import logging
import uuid
from typing import Dict, Tuple, Optional
import redis
import spacy
import subprocess
import sys
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from src.pii_masking.custom_recognizers import CustomIndianRecognizerLoader
try:
    spacy.load("en_core_web_lg")
except OSError:
    logging.info("⬇️ spaCy model 'en_core_web_lg' not found. Downloading for cloud environment...")
    subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_lg"])
    logging.info("✅ spaCy model downloaded successfully.")

logger = logging.getLogger(__name__)

class PIIMaskingManager:
    """
    Manages PII masking and de-masking using Microsoft Presidio and Redis.
    Uses Redis to ensure mappings persist across multiple application workers 
    and concurrent user sessions, with automatic TTL for data privacy.
    """
    
    def __init__(self, config_path: str = "configs/presidio_recognizers.yaml"):
        # 1. Initialize Redis Client
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping() # Verify connection
            logger.info("Successfully connected to Redis for PII mapping storage.")
        except redis.ConnectionError:
            logger.error(f"Failed to connect to Redis at {redis_url}. Please ensure Redis is running.")
            raise

        # 2. Initialize Presidio Analyzer with Custom Recognizers
        registry = RecognizerRegistry()
        custom_loader = CustomIndianRecognizerLoader(config_path)
        custom_recognizers = custom_loader.load_recognizers()
        
        for rec in custom_recognizers:
            registry.add_recognizer(rec)
            
        self.analyzer = AnalyzerEngine(registry=registry)
        self.anonymizer = AnonymizerEngine()
        
        # 3. Local counter for generating unique anonymization keys within a session
        self._counter: int = 0

    def _generate_anon_key(self, entity_type: str) -> str:
        """Generates a unique anonymized key for a specific entity."""
        self._counter += 1
        return f"<ANON_{entity_type}_{self._counter}>"

    def mask_pii(self, text: str, claim_id: Optional[str] = None) -> Tuple[str, str]:
        """
        Analyzes text for PII, masks it, and stores the mapping in Redis.
        
        Args:
            text: The raw text to be masked.
            claim_id: A unique identifier for the claim/session. If None, a UUID is generated.
            
        Returns:
            Tuple containing the masked text and the claim_id used for storage.
        """
        if not claim_id:
            claim_id = str(uuid.uuid4())
            
        analyzer_results = self.analyzer.analyze(
            text=text, 
            language="en", 
            entities=[
                "IN_DRIVING_LICENCE", "IN_VEHICLE_RC", "IN_VIN_CHASSIS", 
                "IN_PAN", "IN_PHONE_NUMBER", "PHONE_NUMBER", "PERSON"
            ]
        )
        
        if not analyzer_results:
            return text, claim_id

        operators = {}
        redis_mapping = {}
        
        for result in analyzer_results:
            entity_type = result.entity_type
            original_text = text[result.start:result.end]
            anon_key = self._generate_anon_key(entity_type)
            
            redis_mapping[anon_key] = original_text
            operators[entity_type] = OperatorConfig("replace", {"new_value": anon_key})

        # Anonymize text
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=analyzer_results,
            operators=operators
        )
        
        # Store in Redis with a 24-hour expiration (86400 seconds) for privacy compliance
        redis_key = f"pii_mapping:{claim_id}"
        if redis_mapping:
            self.redis_client.hset(redis_key, mapping=redis_mapping)
            self.redis_client.expire(redis_key, 86400)
            logger.info(f"Masked {len(redis_mapping)} PII entities for claim {claim_id} and stored in Redis.")
            
        return anonymized_result.text, claim_id

    def unmask_pii(self, masked_text: str, claim_id: str) -> str:
        """
        Restores the original PII using the mapping stored in Redis.
        """
        redis_key = f"pii_mapping:{claim_id}"
        mapping = self.redis_client.hgetall(redis_key)
        
        if not mapping:
            logger.warning(f"No PII mapping found in Redis for claim_id: {claim_id}")
            return masked_text
            
        restored_text = masked_text
        for anon_key, original_value in mapping.items():
            restored_text = restored_text.replace(anon_key, original_value)
            
        return restored_text

    def clear_mapping(self, claim_id: str) -> bool:
        """
        Explicitly deletes the mapping from Redis (e.g., after report generation).
        """
        redis_key = f"pii_mapping:{claim_id}"
        deleted_count = self.redis_client.delete(redis_key)
        if deleted_count > 0:
            logger.info(f"Cleared PII mapping for claim {claim_id} from Redis.")
            return True
        return False