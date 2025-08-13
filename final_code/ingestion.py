import arxiv
import json
from typing import List, Dict, Any
from datetime import datetime, timedelta
from database import VectorDatabase
import streamlit as st

class ArxivIngestion:
    def __init__(self):
        self.db = VectorDatabase()
        self.client = arxiv.Client()
    
    def search_arxiv(self, query: str, max_results: int = 100, 
                    categories: List[str] = None, 
                    start_date: str = None, 
                    end_date: str = None) -> List[Dict[str, Any]]:
        
        search_query = query
        if categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
            search_query = f"({query}) AND ({cat_query})"
        
        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )
        
        documents = []
        for result in self.client.results(search):
            # Filtrage par date si spécifié
            if start_date and result.published.strftime('%Y-%m-%d') < start_date:
                continue
            if end_date and result.published.strftime('%Y-%m-%d') > end_date:
                continue
            
            doc = {
                'id': result.entry_id.split('/')[-1],
                'title': result.title.replace('\n', ' ').strip(),
                'abstract': result.summary.replace('\n', ' ').strip(),
                'authors': [author.name for author in result.authors],
                'categories': [cat for cat in result.categories],
                'published': result.published.strftime('%Y-%m-%d'),
                'url': result.entry_id,
                'pdf_url': result.pdf_url
            }
            documents.append(doc)
        
        return documents
    
    def ingest_documents(self, documents: List[Dict[str, Any]]):
        if documents:
            self.db.add_documents(documents)
            return len(documents)
        return 0
    
    def quick_ingest(self, topics: List[str] = None, max_per_topic: int = 50):
        if not topics:
            topics = ["machine learning", "deep learning", "neural networks", 
                     "computer vision", "natural language processing"]
        
        all_docs = []
        for topic in topics:
            docs = self.search_arxiv(topic, max_results=max_per_topic)
            all_docs.extend(docs)
        
        # Supprimer les doublons par ID
        seen_ids = set()
        unique_docs = []
        for doc in all_docs:
            if doc['id'] not in seen_ids:
                seen_ids.add(doc['id'])
                unique_docs.append(doc)
        
        return self.ingest_documents(unique_docs)

def run_ingestion_interface():
    st.title("🔍 Ingestion d'Articles arXiv")
    
    db = VectorDatabase()
    ingestion = ArxivIngestion()
    
    # Statistiques actuelles
    count = db.count_documents()
    st.metric("Documents indexés", count)
    
    # Interface d'ingestion
    with st.expander("📥 Ingestion rapide", expanded=True):
        if st.button("Ingérer des articles populaires (IA/ML)", type="primary"):
            with st.spinner("Ingestion en cours..."):
                try:
                    added = ingestion.quick_ingest()
                    st.success(f"✅ {added} documents ajoutés")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur: {str(e)}")
    
    with st.expander("🔍 Ingestion personnalisée"):
        col1, col2 = st.columns(2)
        
        with col1:
            search_query = st.text_input("Requête de recherche", "machine learning")
            max_results = st.slider("Nombre max de résultats", 10, 500, 100)
        
        with col2:
            categories = st.multiselect("Catégories (optionnel)", [
                "cs.AI", "cs.LG", "cs.CV", "cs.CL", "cs.NE", 
                "stat.ML", "math.ST", "physics.data-an"
            ])
        
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Date début (optionnel)", value=None)
        with date_col2:
            end_date = st.date_input("Date fin (optionnel)", value=None)
        
        if st.button("Lancer l'ingestion personnalisée"):
            with st.spinner("Recherche et ingestion..."):
                try:
                    start_str = start_date.strftime('%Y-%m-%d') if start_date else None
                    end_str = end_date.strftime('%Y-%m-%d') if end_date else None
                    
                    docs = ingestion.search_arxiv(
                        search_query, max_results, categories, start_str, end_str
                    )
                    added = ingestion.ingest_documents(docs)
                    st.success(f"✅ {added} documents ajoutés sur {len(docs)} trouvés")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur: {str(e)}")

if __name__ == "__main__":
    run_ingestion_interface()