import logging
from typing import List, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class DocumentChunker:
    """
    Splits loaded documents into semantically meaningful chunks for RAG.
    Tailored for legal/insurance documents to avoid splitting mid-clause or mid-table.
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        # Custom separators prioritized for insurance policy structures
        self.separators = [
            "\n\n\n",          # Major section breaks
            "\n\n",            # Paragraph breaks
            "\n",              # Line breaks
            "PCEC-",           # Specific New India Assurance endorsement markers
            "Section ",        # Policy section markers
            "Exclusions",      # Clause markers
            "Conditions",      
            ". ",              # Sentence breaks
            " ",               # Word breaks
            ""                 # Character fallback
        ]
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=self.separators,
            length_function=len,
            keep_separator=True
        )

    def chunk_documents(self, documents: List[Any]) -> List[Any]:
        """
        Splits a list of LangChain Documents into smaller, overlapping chunks.
        """
        logger.info(f"Chunking {len(documents)} documents...")
        chunks = self.text_splitter.split_documents(documents)
        
        # Add chunk index to metadata for better traceability
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            
        logger.info(f"Generated {len(chunks)} chunks.")
        return chunks