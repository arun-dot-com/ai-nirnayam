import os
import logging
from typing import List, Dict, Any
from langchain_community.document_loaders import PyPDFLoader, PDFPlumberLoader

logger = logging.getLogger(__name__)

class DocumentParser:
    """
    Handles the extraction of text from parseable PDF documents.
    Uses PDFPlumber for better table and layout preservation compared to standard PyPDF.
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir

    def load_pdf(self, file_path: str) -> List[Any]:
        """
        Loads a single PDF and returns a list of LangChain Document objects.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF not found at: {file_path}")
        
        logger.info(f"Parsing PDF: {file_path}")
        
        try:
            # PDFPlumber is superior for extracting tables and maintaining layout structure
            loader = PDFPlumberLoader(file_path)
            documents = loader.load()
            
            # Add metadata to track the source file
            for doc in documents:
                doc.metadata["source_file"] = os.path.basename(file_path)
                
            logger.info(f"Successfully extracted {len(documents)} pages from {os.path.basename(file_path)}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {str(e)}")
            raise

    def load_all_policies(self) -> List[Any]:
        """
        Loads all PDFs from the raw_imt_tariffs and policy_wordings directories.
        """
        all_documents = []
        
        directories = [
            os.path.join(self.data_dir, "raw_imt_tariffs"),
            os.path.join(self.data_dir, "policy_wordings")
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                logger.warning(f"Directory not found: {directory}")
                continue
                
            for filename in os.listdir(directory):
                if filename.lower().endswith(".pdf"):
                    file_path = os.path.join(directory, filename)
                    docs = self.load_pdf(file_path)
                    all_documents.extend(docs)
                    
        logger.info(f"Total documents loaded: {len(all_documents)}")
        return all_documents