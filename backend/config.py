"""
Configuration management — loads from .env
"""
import os
from dotenv import load_dotenv

load_dotenv()

# LLM
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Qdrant
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "enterprise_docs")

# Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "hackathon123")

# Base directory
_BASE_DIR = os.path.dirname(__file__)

def _resolve_db_path(env_var: str, default_relative: str) -> str:
    val = os.getenv(env_var, default_relative).strip()
    if val.startswith("sqlite:///"):
        val = val.replace("sqlite:///", "").lstrip("./")
    if not os.path.isabs(val):
        val = os.path.normpath(os.path.join(_BASE_DIR, val))
    return val

DATABASE_URL = _resolve_db_path("DATABASE_URL", "data/enterprise.db")
EXPERIENCE_DB_URL = _resolve_db_path("EXPERIENCE_DB_URL", "data/experience.db")

# Safety thresholds
CONFIDENCE_APPROVE_THRESHOLD = float(os.getenv("CONFIDENCE_APPROVE_THRESHOLD", "0.80"))
CONFIDENCE_RECHECK_MIN = float(os.getenv("CONFIDENCE_RECHECK_MIN", "0.50"))
RISK_APPROVE_MAX = float(os.getenv("RISK_APPROVE_MAX", "0.30"))
RISK_HUMAN_MIN = float(os.getenv("RISK_HUMAN_MIN", "0.70"))
MAX_RECHECK_ITERATIONS = int(os.getenv("MAX_RECHECK_ITERATIONS", "2"))

# Prompt injection patterns
INJECTION_PATTERNS = [
    "ignore all previous instructions",
    "ignore previous instructions",
    "system override",
    "reveal your system prompt",
    "developer mode",
    "jailbreak",
    "disregard your instructions",
    "forget your instructions",
    "new instructions:",
    "act as",
    "you are now",
]

# Docs directory
DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
