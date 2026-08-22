import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def setup_langsmith():
    """
    Initializes LangSmith tracing for observability.
    Reads configuration from the .env file.
    """
    load_dotenv()
    
    tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    api_key = os.getenv("LANGCHAIN_API_KEY")
    project = os.getenv("LANGCHAIN_PROJECT", "autonomous-motor-od-adjudicator")
    
    if tracing_enabled and api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGCHAIN_PROJECT"] = project
        os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
        logger.info(f"✅ LangSmith tracing enabled for project: {project}")
    else:
        logger.info("ℹ️ LangSmith tracing is disabled. Set LANGCHAIN_TRACING_V2=true and provide LANGCHAIN_API_KEY in .env to enable.")