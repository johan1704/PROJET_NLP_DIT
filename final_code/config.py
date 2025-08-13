import os
from pathlib import Path

# Chemins
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = BASE_DIR / "chroma_db"

# Configuration Ollama
OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "gemma2:2b"

# Configuration ChromaDB
CHROMA_COLLECTION_NAME = "arxiv_papers"

# Configuration recherche
MAX_RESULTS = 100
TOP_K_RESULTS = 10

# Créer les dossiers nécessaires
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)