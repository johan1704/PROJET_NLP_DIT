import ollama
from database import VectorDatabase
from rank_bm25 import BM25Okapi
from typing import List, Dict, Any
import json
import numpy as np
from config import OLLAMA_BASE_URL, LLM_MODEL

class HybridSearchEngine:
    def __init__(self):
        self.db = VectorDatabase()
        self.ollama_client = ollama.Client(host=OLLAMA_BASE_URL)
        self.bm25 = None
        self.documents_corpus = []
        self._build_bm25_index()
    
    def _build_bm25_index(self):
        # Récupérer tous les documents pour BM25
        all_docs = self.db.collection.get()
        if all_docs['documents']:
            self.documents_corpus = all_docs['documents']
            tokenized_corpus = [doc.lower().split() for doc in self.documents_corpus]
            if tokenized_corpus:
                self.bm25 = BM25Okapi(tokenized_corpus)
    
    def expand_query(self, query: str) -> str:
        try:
            prompt = f"""Reformule cette requête de recherche scientifique pour améliorer les résultats. 
            Ajoute des synonymes et termes connexes pertinents.
            Requête originale: {query}
            
            Requête étendue (une seule ligne):"""
            
            response = self.ollama_client.generate(
                model=LLM_MODEL,
                prompt=prompt,
                options={"temperature": 0.3, "num_predict": 100}
            )
            
            expanded = response['response'].strip().replace('\n', ' ')
            return expanded if expanded else query
            
        except Exception as e:
            print(f"Erreur expansion: {e}")
            return query
    
    def bm25_search(self, query: str, top_k: int = 10) -> List[Dict]:
        if not self.bm25 or not self.documents_corpus:
            return []
        
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        
        # Obtenir les top-k résultats
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append({
                    'index': idx,
                    'bm25_score': scores[idx],
                    'document': self.documents_corpus[idx]
                })
        
        return results
    
    def hybrid_search(self, query: str, top_k: int = 10, 
                     expand_query: bool = True, 
                     semantic_weight: float = 0.6,
                     filters: Dict = None) -> List[Dict]:
        
        # Expansion de requête
        search_query = self.expand_query(query) if expand_query else query
        
        # Recherche sémantique (vectorielle)
        vector_results = self.db.search(search_query, n_results=top_k*2, filters=filters)
        
        # Recherche lexicale (BM25)
        bm25_results = self.bm25_search(search_query, top_k=top_k*2)
        
        # Fusion des scores
        combined_results = {}
        
        # Normalisation des scores vectoriels
        if vector_results:
            max_vector_score = max(r['score'] for r in vector_results)
            min_vector_score = min(r['score'] for r in vector_results)
            vector_range = max_vector_score - min_vector_score if max_vector_score != min_vector_score else 1
            
            for result in vector_results:
                doc_id = result['id']
                normalized_score = (result['score'] - min_vector_score) / vector_range
                combined_results[doc_id] = {
                    'semantic_score': normalized_score,
                    'bm25_score': 0,
                    'result': result
                }
        
        # Normalisation des scores BM25
        if bm25_results:
            max_bm25_score = max(r['bm25_score'] for r in bm25_results)
            min_bm25_score = min(r['bm25_score'] for r in bm25_results)
            bm25_range = max_bm25_score - min_bm25_score if max_bm25_score != min_bm25_score else 1
            
            all_docs = self.db.collection.get()
            for bm25_result in bm25_results:
                idx = bm25_result['index']
                if idx < len(all_docs['ids']):
                    doc_id = all_docs['ids'][idx]
                    normalized_score = (bm25_result['bm25_score'] - min_bm25_score) / bm25_range
                    
                    if doc_id in combined_results:
                        combined_results[doc_id]['bm25_score'] = normalized_score
                    else:
                        # Créer un résultat basique pour BM25 uniquement
                        combined_results[doc_id] = {
                            'semantic_score': 0,
                            'bm25_score': normalized_score,
                            'result': {
                                'id': doc_id,
                                'document': bm25_result['document'],
                                'score': 0,
                                'metadata': all_docs['metadatas'][idx] if idx < len(all_docs['metadatas']) else {}
                            }
                        }
        
        # Calcul du score hybride final
        final_results = []
        for doc_id, scores in combined_results.items():
            hybrid_score = (semantic_weight * scores['semantic_score'] + 
                          (1 - semantic_weight) * scores['bm25_score'])
            
            result = scores['result'].copy()
            result['hybrid_score'] = hybrid_score
            result['semantic_score'] = scores['semantic_score']
            result['bm25_score'] = scores['bm25_score']
            final_results.append(result)
        
        # Tri par score hybride
        final_results.sort(key=lambda x: x['hybrid_score'], reverse=True)
        
        return final_results[:top_k]
    
    def generate_summary(self, results: List[Dict], query: str) -> str:
        if not results:
            return "Aucun résultat trouvé pour générer un résumé."
        
        # Préparer le contexte des meilleurs résultats
        context = []
        for i, result in enumerate(results[:5]):  # Top 5 seulement
            title = result['metadata'].get('title', 'Titre non disponible')
            context.append(f"{i+1}. {title}")
        
        context_text = "\n".join(context)
        
        try:
            prompt = f"""Basé sur ces articles scientifiques liés à la requête "{query}":

{context_text}

Génère un résumé synthétique en français qui:
1. Identifie les thèmes principaux
2. Met en évidence les tendances communes
3. Reste factuel et concis (max 200 mots)

Résumé:"""
            
            response = self.ollama_client.generate(
                model=LLM_MODEL,
                prompt=prompt,
                options={"temperature": 0.3, "num_predict": 250}
            )
            
            return response['response'].strip()
            
        except Exception as e:
            return f"Erreur lors de la génération du résumé: {str(e)}"