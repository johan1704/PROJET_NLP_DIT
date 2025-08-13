from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import arxiv
import chromadb
from sentence_transformers import SentenceTransformer
import requests
import json
from typing import List, Optional
import uvicorn
from datetime import datetime

app = FastAPI(title="ArXiv Search Engine")

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

# Initialisation
model = SentenceTransformer('all-MiniLM-L6-v2')
client = chromadb.PersistentClient(path="./chroma_db")

try:
    collection = client.get_collection("arxiv_papers")
except:
    collection = client.create_collection("arxiv_papers")

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
    """Stocke les papiers dans ChromaDB"""
    documents = []
    metadatas = []
    ids = []
    
    for paper in papers:
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
    
    # Génération des embeddings
    embeddings = model.encode(documents).tolist()
    
    try:
        collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    except Exception as e:
        print(f"Erreur lors du stockage: {e}")

@app.get("/")
async def root():
    return {"message": "ArXiv Search Engine API"}

@app.post("/index")
async def index_papers(query: str = "machine learning", max_results: int = 50):
    """Indexe de nouveaux papiers d'ArXiv"""
    try:
        papers = fetch_arxiv_papers(query, max_results)
        store_papers(papers)
        return {"message": f"Indexé {len(papers)} papiers"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search", response_model=List[Paper])
async def search_papers(query: SearchQuery):
    """Recherche sémantique dans les papiers"""
    try:
        # Embedding de la requête
        query_embedding = model.encode(query.query).tolist()
        
        # Recherche dans ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=query.max_results
        )
        
        papers = []
        for i, doc_id in enumerate(results['ids'][0]):
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]
            
            # Filtrage par catégorie si spécifié
            categories = json.loads(metadata['categories'])
            if query.category and query.category not in categories:
                continue
            
            paper = Paper(
                id=doc_id,
                title=metadata['title'],
                authors=json.loads(metadata['authors']),
                summary=results['documents'][0][i].split(metadata['title'], 1)[1].strip(),
                published=metadata['published'],
                categories=categories,
                score=1 - distance  # Convertir distance en score
            )
            papers.append(paper)
        
        return papers[:query.max_results]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Statistiques de la base de données"""
    try:
        count = collection.count()
        return {"total_papers": count}
    except Exception as e:
        return {"error": str(e), "total_papers": 0}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)