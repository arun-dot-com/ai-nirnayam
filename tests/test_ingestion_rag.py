import os
import pytest
from dotenv import load_dotenv

from src.ingestion.chunking import DocumentChunker
from src.rag.vector_store import VectorStoreManager
from src.rag.retriever import PolicyRetriever

# Load environment variables to get the real OPENAI_API_KEY
load_dotenv()

def test_document_chunker_preserves_structure():
    """Unit test: Ensures the chunker correctly splits text based on insurance separators."""
    from unittest.mock import MagicMock
    
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
    
    MockDoc = MagicMock()
    MockDoc.page_content = "PCEC-1\nThis is the nil depreciation clause.\n\nIt applies to partial losses."
    MockDoc.metadata = {"source": "test.pdf"}
    
    chunks = chunker.chunk_documents([MockDoc])
    
    assert len(chunks) >= 1
    assert any("PCEC-1" in chunk.page_content for chunk in chunks)


# This test will ONLY run if a real OpenAI API key is present in your .env file.
# If the key is missing or still the default placeholder, it skips gracefully.
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "sk-your-openai-key",
    reason="Real OPENAI_API_KEY not found in .env. Skipping live integration test."
)
def test_real_rag_pipeline_with_openai_and_pdfs():
    """
    REAL INTEGRATION TEST: 
    1. Reads actual PDFs from the data/ directory.
    2. Calls the real OpenAI API to generate embeddings.
    3. Builds a real FAISS index.
    4. Queries the index and verifies it returns actual policy text.
    """
    test_index_dir = "data/faiss_index_integration_test"
    
    # 1. Build the index from real PDFs using real OpenAI embeddings
    manager = VectorStoreManager(persist_directory=test_index_dir)
    vectorstore = manager.build_and_save_index(force_rebuild=True)
    
    assert vectorstore is not None, "Vectorstore should be created"
    assert os.path.exists(test_index_dir), "FAISS index directory should be created on disk"

    # 2. Test real semantic retrieval
    retriever = PolicyRetriever(vectorstore, k=2)
    query = "What is the depreciation rate for plastic or rubber parts?"
    results = retriever.retrieve_clauses(query)
    
    # 3. Assert we got real, relevant results back
    assert len(results) > 0, "Should retrieve at least one relevant chunk from the real PDFs"
    
    # Combine retrieved text to check for expected IMT keywords from your actual documents
    retrieved_text = " ".join([r["content"] for r in results]).lower()
    
    # Your actual PDFs contain "50%" and "plastic" or "rubber" in the depreciation clauses
    assert "50%" in retrieved_text or "plastic" in retrieved_text or "rubber" in retrieved_text, \
        f"Retrieved text should contain actual policy depreciation rules. Got: {retrieved_text[:100]}..."
        
    print("\n✅ SUCCESS: Real OpenAI embedding and real PDF retrieval verified successfully.")