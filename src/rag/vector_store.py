import os
import logging
from typing import List, Any, Optional
from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from src.ingestion.pdf_parser import DocumentParser
from src.ingestion.chunking import DocumentChunker

logger = logging.getLogger(__name__)

# Load environment variables (OPENAI_API_KEY must be set)
load_dotenv()

class VectorStoreManager:
    """
    Manages the creation, saving, and loading of the FAISS vector store.
    """
    
    def __init__(self, persist_directory: str = "data/faiss_index"):
        self.persist_directory = persist_directory
        
        # Initialize embeddings (using OpenAI as per standard LangChain setup)
        # Fallback to a dummy model if no API key is present during initial testing
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        else:
            logger.warning("OPENAI_API_KEY not found. Using mock embeddings for testing.")
            from langchain_community.embeddings import FakeEmbeddings
            self.embeddings = FakeEmbeddings(size=1536)

    def build_and_save_index(self, force_rebuild: bool = False) -> FAISS:
        """
        Parses PDFs, chunks them, and builds a new FAISS index.
        """
        if os.path.exists(self.persist_directory) and not force_rebuild:
            logger.info(f"Loading existing FAISS index from {self.persist_directory}")
            return self.load_index()

        logger.info("Building new FAISS index from source PDFs...")
        
        # 1. Parse
        parser = DocumentParser()
        documents = parser.load_all_policies()
        
        if not documents:
            raise ValueError("No documents found to index. Check the 'data/' directory.")
            
        # 2. Chunk
        chunker = DocumentChunker()
        chunks = chunker.chunk_documents(documents)
        
        # 3. Create FAISS Index
        logger.info("Creating FAISS vector store...")
        vectorstore = FAISS.from_documents(chunks, self.embeddings)
        
        # 4. Save to disk
        vectorstore.save_local(self.persist_directory)
        logger.info(f"FAISS index successfully saved to {self.persist_directory}")
        
        return vectorstore

    def load_index(self) -> FAISS:
        """
        Loads an existing FAISS index from disk.
        """
        if not os.path.exists(self.persist_directory):
            raise FileNotFoundError(f"FAISS index not found at {self.persist_directory}. Run build_and_save_index first.")
            
        return FAISS.load_local(
            self.persist_directory, 
            self.embeddings, 
            allow_dangerous_deserialization=True
        )