import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
import numpy as np
from typing import List, Dict
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import re
import chromadb
import yaml

class Visualization:
    def __init__(self, config_path: str ="../config/config.yaml"):
        with open(config_path, 'r' ,encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.client = chromadb.PersistentClient(path=self.config['database']['chroma_path'])
        self.collection = self.client.get_collection(self.config['database']['collection_name'])
    
    def get_all_metadata(self) -> pd.DataFrame:
        """Récupérer toutes les métadonnées sous forme de DataFrame"""
        try:
            results = self.collection.get()
            df = pd.DataFrame(results['metadatas'])
            
            # Nettoyer et convertir les types
            df['published'] = pd.to_datetime(df['published'], errors='coerce')
            df['authors_list'] = df['authors'].str.split(', ')
            df['categories_list'] = df['categories'].str.split(', ')
            
            return df
        except Exception as e:
            print(f"Erreur récupération métadonnées: {e}")
            return pd.DataFrame()
    
    def create_trends_analysis(self, keywords: List[str], time_window: str = "1Y") -> go.Figure:
        """Analyser les tendances temporelles de mots-clés"""
        df = self.get_all_metadata()
        if df.empty:
            return go.Figure()
        
        # Filtrer par fenêtre temporelle
        df = self.get_all_metadata()
        if df.empty:
            return go.Figure()
        
        df['published'] = pd.to_datetime(df['published'] , utc=True)

        end_date =pd.Timestamp.now(tz='UTC')
        if time_window == "1Y":
            start_date = end_date - pd.Timedelta(days=365)
        elif time_window == "6M":
            start_date = end_date - pd.Timedelta(days=180)
        elif time_window == "3M":
            start_date = end_date - pd.Timedelta(days=90)
        else:
            start_date = end_date - pd.Timedelta(days=365)    
        
        df_filtered = df[
        (df['published'] >= start_date) & 
        (df['published'] <= end_date)
        ].copy()
        # Grouper par mois
        #df_filtered['month'] = df_filtered['published'].dt.to_period('M')
        df_filtered['month'] = df_filtered['published'].dt.tz_localize(None).dt.to_period('M')
        
        # Récupérer tous les documents pour l'analyse textuelle
        results = self.collection.get()
        documents = results['documents']
        metadatas = results['metadatas']
        
        # Créer un mapping doc -> metadata
        doc_metadata = {}
        for i, doc in enumerate(documents):
            if i < len(metadatas):
                doc_metadata[doc] = metadatas[i]
        
        # Analyser les tendances par mot-clé
        trends_data = []
        
        for keyword in keywords:
            monthly_counts = defaultdict(int)
            
            for doc, metadata in doc_metadata.items():
                # Vérifier si le mot-clé est présent
                if keyword.lower() in doc.lower():
                    try:
                        pub_date = pd.to_datetime(metadata['published'])
                        if start_date <= pub_date <= end_date:
                            month = pub_date.to_period('M')
                            monthly_counts[month] += 1
                    except:
                        continue
            
            # Convertir en liste pour le graphique
            for month, count in monthly_counts.items():
                trends_data.append({
                    'keyword': keyword,
                    'month': month.to_timestamp(),
                    'count': count
                })
        
        if not trends_data:
            return go.Figure().add_annotation(
                text="Aucune donnée disponible pour les mots-clés sélectionnés",
                xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
            )
        
        trends_df = pd.DataFrame(trends_data)
        
        # Créer le graphique
        fig = px.line(
            trends_df,
            x='month',
            y='count',
            color='keyword',
            title="Évolution temporelle des mots-clés",
            labels={'month': 'Mois', 'count': 'Nombre d\'occurrences', 'keyword': 'Mot-clé'}
        )
        
        fig.update_layout(
            xaxis_title="Période",
            yaxis_title="Nombre d'occurrences",
            hovermode='x unified'
        )
        
        return fig
    
    def create_category_distribution(self) -> go.Figure:
        """Créer un graphique de distribution des catégories"""
        df = self.get_all_metadata()
        if df.empty:
            return go.Figure()
        
        # Compter les catégories
        all_categories = []
        for cats in df['categories_list'].dropna():
            all_categories.extend(cats)
        
        category_counts = Counter(all_categories)
        top_categories = dict(category_counts.most_common(15))
        
        fig = px.bar(
            x=list(top_categories.keys()),
            y=list(top_categories.values()),
            title="Distribution des catégories arXiv",
            labels={'x': 'Catégorie', 'y': 'Nombre d\'articles'}
        )
        
        fig.update_layout(
            xaxis_tickangle=-45,
            height=500
        )
        
        return fig
    
    def create_author_network(self, min_papers: int = 2) -> go.Figure:
      df = self.get_all_metadata()
      if df.empty:
          return go.Figure()
    
    # Construire le graphe de co-auteurs
      G = nx.Graph()
      author_papers = defaultdict(list)
    
    # Grouper par article (paper_id)
      paper_authors = df.groupby('paper_id')['authors_list'].first()
    
      for paper_id, authors_list in paper_authors.items():
          if authors_list and len(authors_list) > 1:
            # Ajouter les auteurs
              for author in authors_list:
                  author_papers[author].append(paper_id)
                  G.add_node(author)
            
            # Ajouter les arêtes entre co-auteurs
              for i in range(len(authors_list)):
                  for j in range(i + 1, len(authors_list)):
                      author1, author2 = authors_list[i], authors_list[j]
                      if G.has_edge(author1, author2):
                          G[author1][author2]['weight'] += 1
                      else:
                          G.add_edge(author1, author2, weight=1)
    
    # Filtrer les auteurs avec au moins min_papers articles
      nodes_to_remove = [
          author for author in G.nodes()
          if len(author_papers[author]) < min_papers
      ]
      G.remove_nodes_from(nodes_to_remove)
    
      # Limiter le nombre de nœuds pour la visualisation
      max_nodes = self.config['visualization']['max_network_nodes']
      if len(G.nodes()) > max_nodes:
          # Garder les auteurs les plus connectés
          degree_centrality = nx.degree_centrality(G)
          top_authors = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
          authors_to_keep = [author for author, _ in top_authors]
          G = G.subgraph(authors_to_keep).copy()
    
      if len(G.nodes()) == 0:
          return go.Figure().add_annotation(
              text="Aucun réseau de co-auteurs trouvé",
              xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
          )
    
      # Calculer les positions avec spring layout
      pos = nx.spring_layout(G, k=1, iterations=50)
    
      # Préparer les données pour Plotly
      edge_x = []
      edge_y = []
      edge_info = []
    
      for edge in G.edges():
          x0, y0 = pos[edge[0]]
          x1, y1 = pos[edge[1]]
          edge_x.extend([x0, x1, None])
          edge_y.extend([y0, y1, None])
          weight = G[edge[0]][edge[1]]['weight']
          edge_info.append(f"Collaboration: {weight} article(s)")
    
      edge_trace = go.Scatter(
          x=edge_x, y=edge_y,
          line=dict(width=0.5, color='#888'),
          hoverinfo='none',
          mode='lines'
      )
    
      node_x = []
      node_y = []
      node_text = []
      node_info = []
    
      for node in G.nodes():
          x, y = pos[node]
          node_x.append(x)
          node_y.append(y)
          node_text.append(node)
        
          # Info sur l'auteur
          num_papers = len(author_papers[node])
          num_collabs = len(list(G.neighbors(node)))
          node_info.append(f"{node}<br>Articles: {num_papers}<br>Collaborateurs: {num_collabs}")
    
      node_trace = go.Scatter(
          x=node_x, y=node_y,
          mode='markers+text',
          hoverinfo='text',
          hovertext=node_info,
          text=node_text,
          textposition="middle center",
          marker=dict(
              size=10,
              color='lightblue',
              line=dict(width=2, color='darkblue')
          )
      )
    
      fig = go.Figure(
          data=[edge_trace, node_trace],
          layout=go.Layout(
              title='Réseau de co-auteurs',
              title_font=dict(size=16),
              showlegend=False,
              hovermode='closest',
              margin=dict(b=20, l=5, r=5, t=40),
              annotations=[dict(
                  text="Visualisation des collaborations entre auteurs",
                  showarrow=False,
                  xref="paper", yref="paper",
                  x=0.005, y=-0.002,
                  xanchor='left', yanchor='bottom',
                  font=dict(color='gray', size=12)
              )],
              xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
              yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
          )
      )
    
      return fig
    
    
    def create_publication_timeline(self) -> go.Figure:
        """Créer une timeline des publications"""
        df = self.get_all_metadata()
        if df.empty:
            return go.Figure()
        
        # Grouper par mois
        df['month'] = df['published'].dt.to_period('M')
        monthly_counts = df.groupby('month').size().reset_index(name='count')
        monthly_counts['month'] = monthly_counts['month'].dt.to_timestamp()
        
        fig = px.line(
            monthly_counts,
            x='month',
            y='count',
            title="Timeline des publications",
            labels={'month': 'Mois', 'count': 'Nombre de publications'}
        )
        
        fig.update_traces(mode='lines+markers')
        fig.update_layout(
            xaxis_title="Période",
            yaxis_title="Nombre de publications",
            height=400
        )
        
        return fig
    
    def get_search_analytics(self, results: List[Dict]) -> Dict:
        """Analyser les résultats de recherche"""
        if not results:
            return {}
        
        # Extraire les métadonnées
        categories = []
        authors = []
        years = []
        scores = []
        
        for result in results:
            metadata = result['metadata']
            
            # Catégories
            cats = metadata.get('categories', '').split(', ')
            categories.extend(cats)
            
            # Auteurs
            auths = metadata.get('authors', '').split(', ')
            authors.extend(auths)
            
            # Années
            try:
                pub_date = pd.to_datetime(metadata.get('published', ''))
                years.append(pub_date.year)
            except:
                pass
            
            # Scores
            scores.append(result.get('hybrid_score', 0))
        
        analytics = {
            'total_results': len(results),
            'avg_score': np.mean(scores) if scores else 0,
            'top_categories': Counter(categories).most_common(5),
            'top_authors': Counter(authors).most_common(5),
            'year_distribution': Counter(years),
            'score_range': (min(scores), max(scores)) if scores else (0, 0)
        }
        
        return analytics
    
    def create_results_distribution(self, results: List[Dict]) -> go.Figure:
        """Créer un graphique de distribution des résultats"""
        if not results:
            return go.Figure()
        
        analytics = self.get_search_analytics(results)
        
        # Graphique des catégories principales
        if analytics['top_categories']:
            categories, counts = zip(*analytics['top_categories'])
            
            fig = px.bar(
                x=list(categories),
                y=list(counts),
                title="Distribution des catégories dans les résultats",
                labels={'x': 'Catégorie', 'y': 'Nombre d\'articles'}
            )
            
            fig.update_layout(
                xaxis_tickangle=-45,
                height=400
            )
            
            return fig
        
        return go.Figure()
    
    def create_score_distribution(self, results: List[Dict]) -> go.Figure:
        """Créer un histogramme des scores de pertinence"""
        if not results:
            return go.Figure()
        
        scores = [result.get('hybrid_score', 0) for result in results]
        
        fig = px.histogram(
            x=scores,
            nbins=20,
            title="Distribution des scores de pertinence",
            labels={'x': 'Score de pertinence', 'y': 'Nombre d\'articles'}
        )
        
        fig.update_layout(height=400)
        
        return fig

    def create_keywords_wordcloud_data(self, results: List[Dict]) -> List[Dict]:
        """Créer les données pour un nuage de mots des résultats"""
        if not results:
            return []
        
        # Extraire tous les mots des titres et abstracts
        all_text = []
        for result in results:
            title = result['metadata'].get('title', '')
            document = result.get('document', '')
            all_text.append(f"{title} {document}")
        
        # Joindre tout le texte
        full_text = ' '.join(all_text).lower()
        
        # Nettoyer et extraire les mots
        words = re.findall(r'\b[a-zA-Z]{3,}\b', full_text)
        
        # Mots vides à ignorer
        stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
                     'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 
                     'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two',
                     'who', 'boy', 'did', 'she', 'use', 'her', 'way', 'too', 'any',
                     'each', 'which', 'their', 'time', 'will', 'about', 'would',
                     'there', 'could', 'other', 'after', 'first', 'well', 'water',
                     'been', 'call', 'who', 'oil', 'sit', 'now', 'find', 'long',
                     'down', 'day', 'did', 'get', 'come', 'made', 'may', 'part'}
        
        # Filtrer les mots vides
        filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Compter les occurrences
        word_counts = Counter(filtered_words)
        
        # Retourner les données formatées
        return [{'word': word, 'count': count} for word, count in word_counts.most_common(50)]

if __name__ == "__main__":
    viz = Visualization()
    
    # Test des visualisations
    print("Test de l'analyse des tendances...")
    trends_fig = viz.create_trends_analysis(['neural', 'learning', 'deep'])
    
    print("Test du réseau d'auteurs...")
    network_fig = viz.create_author_network()
    
    print("Test de la distribution des catégories...")
    cat_fig = viz.create_category_distribution()
    
    print("Visualisations créées avec succès!")