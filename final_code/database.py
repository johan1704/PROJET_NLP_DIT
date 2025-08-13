import chromadb
from chromadb.config import Settings
import ollama
import json
from typing import List, Dict, Any
from config import CHROMA_DIR, CHROMA_COLLECTION_NAME, EMBEDDING_MODEL, OLLAMA_BASE_URL

class VectorDatabase:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        self.ollama_client = ollama.Client(host=OLLAMA_BASE_URL)
    
    def generate_embedding(self, text: str) -> List[float]:
        try:
            response = self.ollama_client.embeddings(
                model=EMBEDDING_MODEL,
                prompt=text
            )
            return response['embedding']
        except Exception as e:
            print(f"Erreur embedding: {e}")
            return []
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        ids = []
        embeddings = []
        metadatas = []
        documents_text = []
        
        for i, doc in enumerate(documents):
            doc_id = f"doc_{i}_{doc.get('id', '')}"
            text_content = f"{doc.get('title', '')} {doc.get('abstract', '')}"
            
            embedding = self.generate_embedding(text_content)
            if embedding:
                ids.append(doc_id)
                embeddings.append(embedding)
                documents_text.append(text_content)
                
                metadata = {
                    'title': doc.get('title', ''),
                    'authors': json.dumps(doc.get('authors', [])),
                    'categories': json.dumps(doc.get('categories', [])),
                    'published': doc.get('published', ''),
                    'arxiv_id': doc.get('id', ''),
                    'url': doc.get('url', '')
                }
                metadatas.append(metadata)
        
        if ids:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents_text,
                metadatas=metadatas
            )
    
    def search(self, query: str, n_results: int = 10, filters: Dict = None) -> List[Dict]:
        embedding = self.generate_embedding(query)
        if not embedding:
            return []
        
        where_clause = {}
        if filters:
            for key, value in filters.items():
                if value and value != "Tous":
                    where_clause[key] = {"$contains": value}
        
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            where=where_clause if where_clause else None
        )
        
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                result = {
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'distance': results['distances'][0][i],
                    'score': 1 - results['distances'][0][i],
                    'metadata': results['metadatas'][0][i]
                }
                formatted_results.append(result)
        
        return formatted_results
    
    def get_all_metadata(self) -> Dict:
        all_results = self.collection.get()
        
        authors = set()
        categories = set()
        years = set()
        
        for metadata in all_results['metadatas']:
            if metadata.get('authors'):
                try:
                    author_list = json.loads(metadata['authors'])
                    authors.update(author_list)
                except:
                    pass
            
            if metadata.get('categories'):
                try:
                    cat_list = json.loads(metadata['categories'])
                    categories.update(cat_list)
                except:
                    pass
            
            if metadata.get('published'):
                try:
                    year = metadata['published'][:4]
                    if year.isdigit():
                        years.add(year)
                except:
                    pass
        
        return {
            'authors': sorted(list(authors)),
            'categories': sorted(list(categories)),
            'years': sorted(list(years), reverse=True)
        }
    
    def count_documents(self) -> int:
        return self.collection.count()