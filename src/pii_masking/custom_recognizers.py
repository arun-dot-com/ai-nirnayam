import re
import yaml
import logging
from typing import List, Dict, Any
from presidio_analyzer import EntityRecognizer, RecognizerResult, Pattern, PatternRecognizer

logger = logging.getLogger(__name__)

class CustomIndianRecognizerLoader:
    """Loads custom Indian PII recognizers from the YAML configuration."""
    
    def __init__(self, config_path: str = "configs/presidio_recognizers.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
    def load_recognizers(self) -> List[PatternRecognizer]:
        recognizers = []
        for rec_config in self.config.get("recognizers", []):
            patterns = [
                Pattern(
                    name=p["name"], 
                    regex=p["regex"], 
                    score=p["score"]
                ) for p in rec_config["patterns"]
            ]
            
            context = rec_config.get("context", [])
            
            recognizer = PatternRecognizer(
                supported_entity=rec_config["entity_type"],
                patterns=patterns,
                context=context,
                name=rec_config["name"]
            )
            recognizers.append(recognizer)
            logger.info(f"Loaded custom recognizer: {rec_config['name']} for {rec_config['entity_type']}")
            
        return recognizers