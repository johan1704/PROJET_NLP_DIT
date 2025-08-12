import json
import requests
import chromadb
import pandas as pd
import re
from typing import List, Dict
import yaml
from datetime import datetime
import arxiv


class DataIngestion:
    def __init__(self, config_path: str = "../config/config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.client = chromadb.PersistentClient(path=self.config['database']['chroma_path'])
        self.collection = self._get_or_create_collection()
        self.ollama_url = self.config['ollama']['base_url']

    def _get_or_create_collection(self):
        """Créer ou récupérer la collection ChromaDB"""
        try:
            return self.client.get_collection(self.config['database']['collection_name'])
        except:
            return self.client.create_collection(
                name=self.config['database']['collection_name'],
                metadata={"description": "ArXiv papers embeddings"}
            )

    def fetch_arxiv_papers(self, query: str = "machine learning", max_results: int = 100):
        """Récupérer des articles arXiv"""
        client = arxiv.Client()  # Forcer HTTPS
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )

        papers = []
        for paper in client.results(search):
            papers.append({
                'id': paper.entry_id.split('/')[-1],
                'title': paper.title,
                'abstract': paper.summary,
                'authors': [author.name for author in paper.authors],
                'categories': paper.categories,
                'published': paper.published.isoformat(),
                'pdf_url': paper.pdf_url,
                'primary_category': paper.primary_category
            })

        # Sauvegarder les données
        with open(self.config['data']['arxiv_data_path'], 'w', encoding='utf-8') as f:
            json.dump(papers, f, indent=2)

        return papers

    def chunk_text(self, text: str) -> List[str]:
        """Segmenter le texte en chunks"""
        chunk_size = self.config['data']['chunk_size']
        chunk_overlap = self.config['data']['chunk_overlap']

        # Nettoyer le texte
        text = re.sub(r'\s+', ' ', text).strip()

        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            chunks.append(chunk)
            start += chunk_size - chunk_overlap

        return chunks

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
            resp_json = response.json()
            print("Réponse de l'API embedding:", resp_json)  # DEBUG
            return resp_json['embedding']
        except Exception as e:
            print(f"Erreur embedding: {e}")
            return [0.0] * 768  # Embedding par défaut

    def process_papers(self, papers: List[Dict] = None):
        """Traiter et indexer les articles"""
        if papers is None:
            with open(self.config['data']['arxiv_data_path'], 'r') as f:
                papers = json.load(f)

        documents = []
        embeddings = []
        metadatas = []
        ids = []

        for i, paper in enumerate(papers):
            # Créer le texte complet
            full_text = f"{paper['title']} {paper['abstract']}"

            # Chunker le texte
            chunks = self.chunk_text(full_text)

            for j, chunk in enumerate(chunks):
                doc_id = f"{paper['id']}_chunk_{j}"

                # Générer l'embedding
                embedding = self.get_embedding(chunk)

                documents.append(chunk)
                embeddings.append(embedding)
                ids.append(doc_id)
                metadatas.append({
                    'paper_id': paper['id'],
                    'title': paper['title'],
                    'authors': ', '.join(paper['authors']),
                    'categories': ', '.join(paper['categories']),
                    'published': paper['published'],
                    'primary_category': paper['primary_category'],
                    'chunk_index': j,
                    'pdf_url': paper['pdf_url']
                })

            print(f"Traité {i + 1}/{len(papers)} articles")

        # Ajouter à ChromaDB
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

        print(f"Indexé {len(documents)} chunks de {len(papers)} articles")

    def get_stats(self):
        """Obtenir les statistiques de la base"""
        count = self.collection.count()
        return {
            'total_chunks': count,
            'collection_name': self.config['database']['collection_name']
        }


if __name__ == "__main__":
    ingestion = DataIngestion()

    # Récupérer et traiter les articles
    print("Récupération des articles arXiv...")
    papers = ingestion.fetch_arxiv_papers("machine learning OR deep learning", max_results=50)

    print("Traitement et indexation...")
    ingestion.process_papers(papers)

    print("Terminé!")
    print(ingestion.get_stats())# data_ingestion.py
# Pipeline d'ingestion des données
