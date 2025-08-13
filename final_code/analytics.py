import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import networkx as nx
from collections import defaultdict, Counter
import json
from datetime import datetime
from database import VectorDatabase
from typing import List, Dict, Any

class AnalyticsEngine:
    def __init__(self):
        self.db = VectorDatabase()
    
    def get_temporal_trends(self, keywords: List[str] = None) -> Dict:
        all_docs = self.db.collection.get()
        
        if not all_docs['metadatas']:
            return {'dates': [], 'counts': []}
        
        # Compter par année
        year_counts = defaultdict(int)
        keyword_year_counts = defaultdict(lambda: defaultdict(int))
        
        for i, metadata in enumerate(all_docs['metadatas']):
            published = metadata.get('published', '')
            document = all_docs['documents'][i] if i < len(all_docs['documents']) else ''
            
            if published:
                year = published[:4]
                if year.isdigit():
                    year_counts[year] += 1
                    
                    # Analyser les mots-clés si fournis
                    if keywords:
                        doc_lower = document.lower()
                        for keyword in keywords:
                            if keyword.lower() in doc_lower:
                                keyword_year_counts[keyword][year] += 1
        
        # Préparer les données pour le graphique
        sorted_years = sorted(year_counts.keys())
        
        if not keywords:
            return {
                'years': sorted_years,
                'counts': [year_counts[year] for year in sorted_years],
                'total_count': sum(year_counts.values())
            }
        else:
            keyword_data = {}
            for keyword in keywords:
                keyword_data[keyword] = [keyword_year_counts[keyword][year] for year in sorted_years]
            
            return {
                'years': sorted_years,
                'keyword_data': keyword_data,
                'total_counts': [year_counts[year] for year in sorted_years]
            }
    
    def create_temporal_chart(self, keywords: List[str] = None):
        data = self.get_temporal_trends(keywords)
        
        if not data.get('years'):
            return None
        
        if keywords:
            fig = go.Figure()
            
            # Ajouter une ligne pour chaque mot-clé
            for keyword, counts in data['keyword_data'].items():
                fig.add_trace(go.Scatter(
                    x=data['years'],
                    y=counts,
                    mode='lines+markers',
                    name=keyword.title(),
                    line=dict(width=3),
                    marker=dict(size=8)
                ))
            
            fig.update_layout(
                title=f"Évolution temporelle des mots-clés",
                xaxis_title="Année",
                yaxis_title="Nombre d'articles",
                hovermode='x unified',
                height=500
            )
        else:
            fig = px.line(
                x=data['years'],
                y=data['counts'],
                title="Évolution temporelle du corpus",
                labels={'x': 'Année', 'y': 'Nombre d\'articles'},
                markers=True
            )
            fig.update_traces(line=dict(width=4), marker=dict(size=8))
            fig.update_layout(height=500)
        
        return fig
    
    def get_author_network(self, min_collaborations: int = 2) -> nx.Graph:
        all_docs = self.db.collection.get()
        
        # Compter les collaborations
        collaborations = defaultdict(int)
        author_papers = defaultdict(int)
        
        for metadata in all_docs['metadatas']:
            authors_str = metadata.get('authors', '[]')
            try:
                authors = json.loads(authors_str)
                
                # Compter les papiers par auteur
                for author in authors:
                    author_papers[author] += 1
                
                # Compter les collaborations (paires d'auteurs)
                for i in range(len(authors)):
                    for j in range(i+1, len(authors)):
                        author1, author2 = sorted([authors[i], authors[j]])
                        collaborations[(author1, author2)] += 1
                        
            except json.JSONDecodeError:
                continue
        
        # Créer le graphe
        G = nx.Graph()
        
        # Ajouter les nœuds (auteurs) avec le nombre de papiers
        for author, paper_count in author_papers.items():
            G.add_node(author, papers=paper_count)
        
        # Ajouter les arêtes (collaborations) avec poids
        for (author1, author2), collab_count in collaborations.items():
            if collab_count >= min_collaborations:
                G.add_edge(author1, author2, weight=collab_count)
        
        return G
    
    def create_network_chart(self, min_collaborations: int = 2, max_nodes: int = 50):
        G = self.get_author_network(min_collaborations)
        
        if G.number_of_nodes() == 0:
            return None
        
        # Limiter le nombre de nœuds pour la performance
        if G.number_of_nodes() > max_nodes:
            # Garder les auteurs avec le plus de papiers
            node_papers = [(node, data['papers']) for node, data in G.nodes(data=True)]
            top_nodes = sorted(node_papers, key=lambda x: x[1], reverse=True)[:max_nodes]
            nodes_to_keep = {node for node, _ in top_nodes}
            G = G.subgraph(nodes_to_keep).copy()
        
        # Layout du graphe
        pos = nx.spring_layout(G, k=1, iterations=50)
        
        # Préparer les données pour Plotly
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        node_x = []
        node_y = []
        node_text = []
        node_size = []
        
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(f"{node}<br>Papers: {G.nodes[node]['papers']}")
            node_size.append(min(G.nodes[node]['papers'] * 3, 50))  # Taille proportionnelle
        
        # Créer le graphique
        fig = go.Figure()
        
        # Ajouter les arêtes
        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=1, color='#888'),
            hoverinfo='none',
            mode='lines',
            showlegend=False
        ))
        
        # Ajouter les nœuds
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            hovertext=node_text,
            marker=dict(
                size=node_size,
                color='lightblue',
                line=dict(width=2, color='darkblue')
            ),
            showlegend=False
        ))
        
        fig.update_layout(
            title=f"Réseau de Co-auteurs (min {min_collaborations} collaborations)",
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20,l=5,r=5,t=40),
            annotations=[dict(
                text="Taille du nœud = nombre de papiers",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.005, y=-0.002,
                xanchor='left', yanchor='bottom',
                font=dict(color="grey", size=12)
            )],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=600
        )
        
        return fig
    
    def get_category_distribution(self) -> Dict:
        all_docs = self.db.collection.get()
        category_counts = Counter()
        
        for metadata in all_docs['metadatas']:
            categories_str = metadata.get('categories', '[]')
            try:
                categories = json.loads(categories_str)
                for cat in categories:
                    category_counts[cat] += 1
            except json.JSONDecodeError:
                continue
        
        return dict(category_counts)
    
    def create_category_chart(self, top_n: int = 15):
        cat_data = self.get_category_distribution()
        
        if not cat_data:
            return None
        
        # Prendre les top N catégories
        sorted_cats = sorted(cat_data.items(), key=lambda x: x[1], reverse=True)[:top_n]
        categories, counts = zip(*sorted_cats)
        
        fig = px.bar(
            x=counts,
            y=categories,
            orientation='h',
            title=f"Top {top_n} Catégories d'Articles",
            labels={'x': 'Nombre d\'articles', 'y': 'Catégories'}
        )
        
        fig.update_layout(
            height=500,
            yaxis={'categoryorder': 'total ascending'}
        )
        
        return fig