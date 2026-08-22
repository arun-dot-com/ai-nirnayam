import logging
from typing import List, Dict, Any, Optional
from mem0 import Memory

logger = logging.getLogger(__name__)

class Mem0Manager:
    """
    Manages long-term memory for vehicle claim history and NCB status using Mem0.
    Uses the anonymized vehicle identifier as the user_id to ensure PII compliance.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the Mem0 memory store.
        If no config is provided, it defaults to a local vector store setup.
        """
        default_config = {
            "vector_store": {
                "provider": "faiss",
                "config": {
                    "collection_name": "vehicle_claim_history",
                    "path": "./data/mem0_faiss_index"
                }
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "model": "text-embedding-3-small"
                }
            }
        }
        
        final_config = config or default_config
        
        try:
            self.memory = Memory.from_config(final_config)
            logger.info("Mem0 Memory manager initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Mem0: {str(e)}")
            raise

    def add_claim_event(self, anonymized_vehicle_id: str, event_details: str) -> str:
        """
        Adds a new claim event or NCB update to the vehicle's memory.
        """
        logger.info(f"Adding memory for vehicle {anonymized_vehicle_id}: {event_details}")
        
        # Use 'messages' as the parameter name, which is standard in mem0ai >= 0.1.x
        result = self.memory.add(
            messages=event_details,
            user_id=anonymized_vehicle_id,
            metadata={"type": "claim_history"}
        )
        
        # Handle different return types (dict with 'id' or direct string/id)
        if isinstance(result, dict):
            memory_id = result.get("id", str(result))
        else:
            memory_id = str(result)
            
        logger.info(f"Memory added successfully with ID: {memory_id}")
        return memory_id

    def get_vehicle_history(self, anonymized_vehicle_id: str, query: str = "claim history and NCB status") -> List[Dict[str, Any]]:
        """
        Retrieves historical memories for a specific vehicle based on a semantic query.
        """
        logger.info(f"Retrieving memory for vehicle {anonymized_vehicle_id} with query: '{query}'")
        
        raw_memories = self.memory.search(
            query=query,
            user_id=anonymized_vehicle_id,
            limit=5
        )
        
        formatted_memories = []
        
        # 1. Handle if mem0 returns a dict with a 'results' key (common in mem0ai >= 0.1.x)
        if isinstance(raw_memories, dict) and "results" in raw_memories:
            memories_list = raw_memories["results"]
        # 2. Handle if it returns a direct list
        elif isinstance(raw_memories, list):
            memories_list = raw_memories
        else:
            memories_list = []

        # 3. Iterate over the actual list of memories
        for mem in memories_list:
            if isinstance(mem, dict):
                formatted_memories.append({
                    "memory_id": mem.get("id", "unknown"),
                    "content": mem.get("memory", mem.get("content", "")),
                    "score": mem.get("score", 0.0),
                    "metadata": mem.get("metadata", {})
                })
            elif isinstance(mem, str):
                formatted_memories.append({
                    "memory_id": "unknown",
                    "content": mem,
                    "score": 1.0,
                    "metadata": {}
                })
            else:
                # Fallback for object with attributes (e.g., Pydantic model)
                formatted_memories.append({
                    "memory_id": getattr(mem, "id", "unknown"),
                    "content": getattr(mem, "memory", getattr(mem, "content", str(mem))),
                    "score": getattr(mem, "score", 1.0),
                    "metadata": getattr(mem, "metadata", {})
                })
                
        logger.info(f"Retrieved {len(formatted_memories)} historical records.")
        return formatted_memories

    def update_ncb_status(self, anonymized_vehicle_id: str, new_ncb_percentage: int, reason: str) -> str:
        """
        Updates or adds a specific memory regarding the vehicle's NCB status.
        """
        event_text = f"Vehicle NCB status updated to {new_ncb_percentage}%. Reason: {reason}"
        return self.add_claim_event(anonymized_vehicle_id, event_text)

    def delete_memory(self, memory_id: str) -> bool:
        """
        Deletes a specific memory entry by its ID.
        """
        try:
            self.memory.delete(memory_id)
            logger.info(f"Memory {memory_id} deleted successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {str(e)}")
            return False