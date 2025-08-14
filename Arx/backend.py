from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import arxiv
import chromadb
import requests
import json
from typing import List, Optional
import uvicorn
from datetime import datetime
from rank_bm25 import BM25Okapi
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import re
import os
import shutil

app = FastAPI(title="ArXiv Search Engine")

# Configuration Ollama
OLLAMA_BASE_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "gemma:2b"

# Modèles
class SearchQuery(BaseModel):
    query: str
    max_results: int = 10
    category: Optional[str] = None

class Paper(BaseModel):
    id: str
    title: str
    authors: List[str]
    summary: str
    published: str
    categories: List[str]
    score: float = 0.0
    bm25_score: float = 0.0
    semantic_score: float = 0.0

# Base de données
DB_PATH = "./chroma_db"
papers_cache = []  # Cache pour BM25
bm25 = None
collection = None

def initialize_database():
    """Initialize ChromaDB with correct embedding dimensions"""
    global collection
    
    # Si la base existe avec de mauvaises dimensions, la supprimer
    if os.path.exists(DB_PATH):
        try:
            temp_client = chromadb.PersistentClient(path=DB_PATH)
            try:
                temp_collection = temp_client.get_collection("arxiv_papers")
                # Tester avec un embedding de test
                test_embedding = get_ollama_embedding("test")
                if test_embedding:
                    temp_collection.query(
                        query_embeddings=[test_embedding],
                        n_results=1
                    )
                collection = temp_collection
                print("✅ Base de données existante compatible")
                return
            except Exception as e:
                if "dimension" in str(e).lower():
                    print("❌ Dimensions incompatibles, suppression de l'ancienne base...")
                    temp_client.delete_collection("arxiv_papers")
                    del temp_client
                    shutil.rmtree(DB_PATH)
                else:
                    print(f"Autre erreur: {e}")
        except Exception as e:
            print(f"Erreur lors de la vérification: {e}")
    
    # Créer une nouvelle base avec métrique cosinus
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.create_collection(
        name="arxiv_papers",
        metadata={"hnsw:space": "cosine"}  # Utiliser la métrique cosinus
    )
    print("✅ Nouvelle base de données créée avec métrique cosinus")

def get_ollama_embedding(text: str):
    """Génère un embedding avec Ollama/nomic-embed-text"""
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=30
        )
        if response.status_code == 200:
            embedding = response.json()["embedding"]
            print(f"📏 Dimension de l'embedding: {len(embedding)}")
            return embedding
        else:
            print(f"Erreur Ollama embedding: {response.status_code}")
            return None
    except Exception as e:
        print(f"Erreur connexion Ollama: {e}")
        return None

def expand_query_with_gemma(query: str):
    """Expansion de requête avec Gemma via Ollama"""
    prompt = f"""Reformule cette requête de recherche scientifique en ajoutant des termes similaires et synonymes pertinents. Donne SEULEMENT la requête étendue, sans formatage ni explication.

Requête: {query}

Requête étendue:"""
    
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 50}
            },
            timeout=30
        )
        if response.status_code == 200:
            expanded = response.json()["response"].strip()
            # Nettoyer la réponse de tout formatage markdown ou préfixe
            expanded = re.sub(r'\*\*.*?\*\*:?\s*', '', expanded)
            expanded = re.sub(r'^["\']|["\']$', '', expanded)
            expanded = expanded.split('\n')[0].strip()  # Prendre seulement la première ligne
            
            return expanded if len(expanded) > len(query) and len(expanded) < 100 else query
        else:
            return query
    except Exception as e:
        print(f"Erreur expansion de requête: {e}")
        return query

def preprocess_text(text: str):
    """Préprocessing pour BM25"""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return text.split()

def fetch_arxiv_papers(query: str, max_results: int = 50):
    """Récupère les papiers d'ArXiv"""
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )
    
    papers = []
    for result in search.results():
        paper = {
            'id': result.entry_id.split('/')[-1],
            'title': result.title,
            'authors': [str(author) for author in result.authors],
            'summary': result.summary,
            'published': result.published.isoformat(),
            'categories': result.categories
        }
        papers.append(paper)
    
    return papers

def store_papers(papers):
    """Stocke les papiers dans ChromaDB et met à jour BM25"""
    global papers_cache, bm25, collection
    
    if not collection:
        initialize_database()
    
    documents = []
    metadatas = []
    ids = []
    
    # Filtrer les papiers déjà existants
    existing_ids = {paper['id'] for paper in papers_cache}
    new_papers = [paper for paper in papers if paper['id'] not in existing_ids]
    
    if not new_papers:
        print("Aucun nouveau papier à indexer")
        return
    
    for paper in new_papers:
        # Texte combiné pour l'embedding
        text = f"{paper['title']} {paper['summary']}"
        documents.append(text)
        
        metadatas.append({
            'title': paper['title'],
            'authors': json.dumps(paper['authors']),
            'published': paper['published'],
            'categories': json.dumps(paper['categories'])
        })
        
        ids.append(paper['id'])
        
        # Ajouter au cache pour BM25
        papers_cache.append({
            'id': paper['id'],
            'text': text,
            'metadata': metadatas[-1]
        })
    
    print(f"🔄 Génération des embeddings pour {len(documents)} documents...")
    
    # Génération des embeddings avec Ollama
    embeddings = []
    for i, doc in enumerate(documents):
        print(f"📄 Processing document {i+1}/{len(documents)}")
        embedding = get_ollama_embedding(doc)
        if embedding:
            embeddings.append(embedding)
        else:
            print(f"❌ Erreur embedding pour le document {i+1}")
            return False
    
    try:
        collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"✅ {len(embeddings)} documents stockés avec succès")
    except Exception as e:
        print(f"❌ Erreur lors du stockage: {e}")
        return False
    
    # Reconstruire BM25
    corpus = [preprocess_text(paper['text']) for paper in papers_cache]
    if corpus:
        bm25 = BM25Okapi(corpus)
        print("✅ Index BM25 reconstruit")
    
    return True

def hybrid_search(query: str, max_results: int = 10, category: str = None):
    """Recherche hybride BM25 + sémantique"""
    global bm25, papers_cache, collection
    
    if not papers_cache:
        return []
    
    if not collection:
        initialize_database()
    
    # 1. Expansion de requête
    expanded_query = expand_query_with_gemma(query)
    print(f"🔍 Requête originale: {query}")
    print(f"🔍 Requête étendue: {expanded_query}")
    
    # 2. Recherche sémantique avec Ollama
    query_embedding = get_ollama_embedding(expanded_query)
    semantic_results = []
    
    if query_embedding:
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(max_results * 2, len(papers_cache))
            )
            semantic_results = results
            print(f"✅ Recherche sémantique: {len(results['ids'][0])} résultats")
            
            # Debug: afficher quelques distances pour diagnostic
            if results['distances'][0]:
                distances = results['distances'][0][:5]  # Les 5 premières
                print(f"🔍 Distances sémantiques (échantillon): {[f'{d:.4f}' for d in distances]}")
                
        except Exception as e:
            print(f"❌ Erreur recherche sémantique: {e}")
    
    # 3. Recherche BM25
    bm25_scores = []
    if bm25:
        query_tokens = preprocess_text(expanded_query)
        bm25_scores = bm25.get_scores(query_tokens)
        print(f"✅ Recherche BM25: {len(bm25_scores)} scores calculés")
    
    # 4. Fusion des scores
    papers = []
    semantic_ids = semantic_results.get('ids', [[]])[0] if semantic_results else []
    
    # Normalisation BM25 sécurisée - CORRECTION DE L'ERREUR ICI
    if len(bm25_scores) > 0:
        # Convertir en numpy array et calculer le max
        bm25_array = np.array(bm25_scores)
        max_bm25 = float(np.max(bm25_array)) if bm25_array.size > 0 else 0.0
    else:
        max_bm25 = 0.0
    
    print(f"📊 Max BM25 score: {max_bm25}")
    
    for i, paper in enumerate(papers_cache):
        # Score BM25 (normalisé)
        bm25_score = float(bm25_scores[i]) if i < len(bm25_scores) else 0.0
        bm25_normalized = bm25_score / (max_bm25 + 1e-6) if max_bm25 > 0 else 0.0
        
        # Score sémantique - Correction pour ChromaDB
        semantic_score = 0.0
        if paper['id'] in semantic_ids:
            idx = semantic_ids.index(paper['id'])
            distance = float(semantic_results['distances'][0][idx])
            
            # ChromaDB retourne une distance cosinus (0 = identique, 1 = opposé)
            # On convertit en score de similarité (1 = identique, 0 = opposé)
            semantic_score = max(0.0, 1.0 - distance)
            
            # Debug: afficher quelques scores pour vérification
            if i < 3:  # Afficher les 3 premiers
                print(f"🔍 Paper {i+1}: distance={distance:.4f}, score={semantic_score:.4f}")
        
        # Score hybride (pondération 50/50)
        hybrid_score = 0.5 * bm25_normalized + 0.5 * semantic_score
        
        # Filtrage par catégorie
        if category:
            categories = json.loads(paper['metadata']['categories'])
            if category not in categories:
                continue
        
        # Récupérer le résumé original
        summary = paper['text']
        if paper['metadata']['title'] in summary:
            summary = summary.split(paper['metadata']['title'], 1)[1].strip()
        
        paper_obj = Paper(
            id=paper['id'],
            title=paper['metadata']['title'],
            authors=json.loads(paper['metadata']['authors']),
            summary=summary[:500] + "..." if len(summary) > 500 else summary,
            published=paper['metadata']['published'],
            categories=json.loads(paper['metadata']['categories']),
            score=float(hybrid_score),
            bm25_score=float(bm25_normalized),
            semantic_score=float(semantic_score)
        )
        papers.append(paper_obj)
    
    # Tri par score hybride
    papers.sort(key=lambda x: x.score, reverse=True)
    return papers[:max_results]

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    initialize_database()

@app.get("/")
async def root():
    return {"message": "ArXiv Search Engine API avec Ollama"}

@app.post("/reset")
async def reset_database():
    """Remet à zéro la base de données"""
    global papers_cache, bm25, collection
    
    try:
        if os.path.exists(DB_PATH):
            shutil.rmtree(DB_PATH)
        
        papers_cache = []
        bm25 = None
        collection = None
        
        initialize_database()
        
        return {"message": "Base de données réinitialisée avec succès"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/index")
async def index_papers(query: str = "machine learning", max_results: int = 20):
    """Indexe de nouveaux papiers d'ArXiv"""
    try:
        print(f"🔍 Recherche ArXiv: '{query}' (max: {max_results})")
        papers = fetch_arxiv_papers(query, max_results)
        print(f"📚 {len(papers)} papiers récupérés d'ArXiv")
        
        success = store_papers(papers)
        if success:
            return {"message": f"Indexé {len(papers)} papiers avec Ollama embeddings"}
        else:
            raise HTTPException(status_code=500, detail="Erreur lors de l'indexation")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search", response_model=List[Paper])
async def search_papers(query: SearchQuery):
    """Recherche hybride BM25 + sémantique"""
    try:
        papers = hybrid_search(
            query.query, 
            query.max_results, 
            query.category
        )
        print(f"📊 Résultats: {len(papers)} papiers trouvés")
        return papers
    except Exception as e:
        print(f"❌ Erreur recherche: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Statistiques de la base de données"""
    try:
        count = len(papers_cache)
        
        # Test de connexion Ollama
        ollama_status = "disconnected"
        try:
            test_response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            if test_response.status_code == 200:
                ollama_status = "connected"
        except:
            pass
        
        return {
            "total_papers": count,
            "bm25_ready": bm25 is not None,
            "ollama_status": ollama_status,
            "collection_initialized": collection is not None
        }
    except Exception as e:
        return {"error": str(e), "total_papers": 0}

if __name__ == "__main__":
    print("🚀 Démarrage du moteur de recherche ArXiv avec Ollama")
    print("📋 Vérifiez qu'Ollama est démarré avec les modèles:")
    print("   - ollama pull nomic-embed-text")
    print("   - ollama pull gemma:2b")
    print("")
    print("🔧 Endpoints disponibles:")
    print("   - POST /reset : Réinitialiser la base")
    print("   - POST /index : Indexer des papiers")
    print("   - POST /search : Rechercher")
    print("   - GET /stats : Statistiques")
    uvicorn.run(app, host="0.0.0.0", port=8000)