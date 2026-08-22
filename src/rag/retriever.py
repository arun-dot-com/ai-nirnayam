import logging
from typing import List, Dict, Any
from langchain_community.vectorstores import FAISS

logger = logging.getLogger(__name__)

class PolicyRetriever:
    """
    Handles semantic retrieval of policy clauses and IMT rules from the FAISS store.
    """
    
    def __init__(self, vectorstore: FAISS, k: int = 3):
        self.vectorstore = vectorstore
        self.k = k
        
        # Use standard similarity search to reliably return top-k results.
        # Score thresholds (e.g., 0.6) are often too strict for initial RAG setups 
        # and can filter out valid semantic matches that score around 0.4-0.5.
        self.retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": self.k}
        )

    def retrieve_clauses(self, query: str) -> List[Dict[str, Any]]:
        """
        Retrieves the top-k most relevant document chunks for a given query.
        Returns a list of dictionaries containing the text and metadata.
        """
        logger.info(f"Retrieving clauses for query: '{query}'")
        
        docs = self.retriever.invoke(query)
        
        results = []
        for doc in docs:
            results.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source_file", "Unknown"),
                "chunk_index": doc.metadata.get("chunk_index", 0)
            })
            
        logger.info(f"Retrieved {len(results)} relevant chunks.")
        return results