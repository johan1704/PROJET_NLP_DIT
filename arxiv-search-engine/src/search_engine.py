import chromadb
import requests
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import yaml
import re

class SearchEngine:
    def __init__(self, config_path: str = "../config/config.yaml"):
        with open(config_path, 'r',encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.client = chromadb.PersistentClient(path=self.config['database']['chroma_path'])
        self.collection = self.client.get_collection(self.config['database']['collection_name'])
        self.ollama_url = self.config['ollama']['base_url']
        
        # Initialiser BM25
        self._init_bm25()
    
    def _init_bm25(self):
        """Initialiser l'index BM25"""
        try:
            # Récupérer tous les documents
            results = self.collection.get()
            self.documents = results['documents']
            self.metadatas = results['metadatas']
            self.ids = results['ids']
            
            # Tokeniser pour BM25
            tokenized_docs = [doc.lower().split() for doc in self.documents]
            self.bm25 = BM25Okapi(tokenized_docs)
            print(f"BM25 initialisé avec {len(self.documents)} documents")
        except Exception as e:
            print(f"Erreur initialisation BM25: {e}")
            self.documents = []
            self.metadatas = []
            self.ids = []
    
    def get_embedding(self, text: str) -> List[float]:
        """Générer un embedding avec Ollama"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={
                    "model": self.config['ollama']['embedding_model'],
                    "prompt": text
                }
            )
            return response.json()['embedding']
        except Exception as e:
            print(f"Erreur embedding: {e}")
            return [0.0] * 768
    
    def expand_query(self, query: str) -> str:
        """Expansion de requête avec Gemma"""
        try:
            prompt = f"""Given the search query: "{query}"
Generate 3-5 related terms or synonyms that would help find relevant scientific papers.
Return only the expanded terms separated by spaces, no explanation.

Query: {query}
Expanded terms:"""

            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.config['ollama']['generation_model'],
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            expanded = response.json()['response'].strip()
            # Nettoyer et combiner
            expanded_terms = re.findall(r'\b\w+\b', expanded.lower())
            original_terms = re.findall(r'\b\w+\b', query.lower())
            
            all_terms = list(set(original_terms + expanded_terms))
            return ' '.join(all_terms)
            
        except Exception as e:
            print(f"Erreur expansion requête: {e}")
            return query
    
    def semantic_search(self, query: str, n_results: int = 10) -> List[Dict]:
        """Recherche sémantique avec ChromaDB"""
        try:
            query_embedding = self.get_embedding(query)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            search_results = []
            for i in range(len(results['ids'][0])):
                search_results.append({
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i],
                    'semantic_score': 1 - results['distances'][0][i]  # Convertir distance en score
                })
            
            return search_results
            
        except Exception as e:
            print(f"Erreur recherche sémantique: {e}")
            return []
    
    def lexical_search(self, query: str, n_results: int = 10) -> List[Dict]:
        """Recherche lexicale avec BM25"""
        if not hasattr(self, 'bm25'):
            return []
        
        try:
            query_tokens = query.lower().split()
            bm25_scores = self.bm25.get_scores(query_tokens)
            
            # Récupérer les top résultats
            top_indices = np.argsort(bm25_scores)[-n_results:][::-1]
            
            search_results = []
            for idx in top_indices:
                if bm25_scores[idx] > 0:
                    search_results.append({
                        'id': self.ids[idx],
                        'document': self.documents[idx],
                        'metadata': self.metadatas[idx],
                        'bm25_score': bm25_scores[idx],
                        'lexical_score': bm25_scores[idx]
                    })
            
            return search_results
            
        except Exception as e:
            print(f"Erreur recherche lexicale: {e}")
            return []
    
    def hybrid_search(self, query: str, n_results: int = 10, use_expansion: bool = True) -> List[Dict]:
        """Recherche hybride combinant sémantique et lexical"""
        # Expansion de requête
        if use_expansion:
            expanded_query = self.expand_query(query)
            print(f"Requête étendue: {expanded_query}")
        else:
            expanded_query = query
        
        # Recherches parallèles
        semantic_results = self.semantic_search(expanded_query, n_results * 2)
        lexical_results = self.lexical_search(expanded_query, n_results * 2)
        
        # Fusionner les résultats
        combined_results = {}
        
        # Ajouter résultats sémantiques
        for result in semantic_results:
            doc_id = result['id']
            combined_results[doc_id] = {
                **result,
                'semantic_score': result.get('semantic_score', 0),
                'lexical_score': 0
            }
        
        # Ajouter scores lexicaux
        for result in lexical_results:
            doc_id = result['id']
            if doc_id in combined_results:
                combined_results[doc_id]['lexical_score'] = result.get('lexical_score', 0)
            else:
                combined_results[doc_id] = {
                    **result,
                    'semantic_score': 0,
                    'lexical_score': result.get('lexical_score', 0)
                }
        
        # Calculer score hybride
        semantic_weight = self.config['search']['hybrid_weights']['semantic']
        lexical_weight = self.config['search']['hybrid_weights']['lexical']
        
        for doc_id in combined_results:
            result = combined_results[doc_id]
            # Normaliser les scores
            sem_score = result['semantic_score']
            lex_score = min(result['lexical_score'] / 10.0, 1.0) if result['lexical_score'] > 0 else 0
            
            result['hybrid_score'] = (semantic_weight * sem_score) + (lexical_weight * lex_score)
        
        # Trier par score hybride
        sorted_results = sorted(
            combined_results.values(),
            key=lambda x: x['hybrid_score'],
            reverse=True
        )
        
        return sorted_results[:n_results]
    
    def faceted_search(self, query: str, filters: Dict = None, n_results: int = 10) -> List[Dict]:
        """Recherche avec filtres à facettes"""
        results = self.hybrid_search(query, n_results * 2)
        
        if not filters:
            return results[:n_results]
        
        filtered_results = []
        for result in results:
            metadata = result['metadata']
            include = True
            
            # Appliquer les filtres
            for field, value in filters.items():
                if field == 'date_range':
                    # Filtrer par date
                    pub_date = metadata.get('published', '')
                    if not self._date_in_range(pub_date, value):
                        include = False
                        break
                elif field == 'category':
                    # Filtrer par catégorie
                    categories = metadata.get('categories', '').lower()
                    if value.lower() not in categories:
                        include = False
                        break
                elif field == 'author':
                    # Filtrer par auteur
                    authors = metadata.get('authors', '').lower()
                    if value.lower() not in authors:
                        include = False
                        break
            
            if include:
                filtered_results.append(result)
        
        return filtered_results[:n_results]
    
    def _date_in_range(self, date_str: str, date_range: Tuple[str, str]) -> bool:
        """Vérifier si une date est dans la plage"""
        try:
            from datetime import datetime
            pub_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            start_date = datetime.fromisoformat(date_range[0])
            end_date = datetime.fromisoformat(date_range[1])
            return start_date <= pub_date <= end_date
        except:
            return True
    
    def generate_summary(self, results: List[Dict], query: str) -> str:
        """Générer un résumé synthétique des résultats"""
        try:
            context_texts = []
            for result in results[:5]: 
                title = result['metadata'].get('title', '')
                doc = result['document'][:300]  # Limiter la taille
                context_texts.append(f"Titre: {title}\nContenu: {doc}")
            
            context = '\n\n'.join(context_texts)
            
            prompt = f"""Based on the following research papers related to the query "{query}", 
provide a concise summary of the main findings and themes (max 200 words):

{context}

Summary:"""

            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.config['ollama']['generation_model'],
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            return response.json()['response'].strip()
            
        except Exception as e:
            print(f"Erreur génération résumé: {e}")
            return "Impossible de générer un résumé pour le moment."

if __name__ == "__main__":
    search = SearchEngine()
    
    query = "deep learning"
    results = search.hybrid_search(query, n_results=5)
    
    print(f"Résultats pour '{query}':")
    for i, result in enumerate(results):
        print(f"{i+1}. {result['metadata']['title']}")
        print(f"   Score: {result['hybrid_score']:.3f}")
        print()