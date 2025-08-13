import streamlit as st
import json
import os
import sys
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuration de la page
st.set_page_config(
    page_title="ArXiv Search",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Titre principal
st.title("🔍 Recherche d'Articles ArXiv")
st.markdown("---")

# Configuration minimale par défaut
DEFAULT_CONFIG = {
    'database': {
        'chroma_path': './data/chroma_db',
        'collection_name': 'arxiv_papers'
    },
    'ollama': {
        'base_url': 'http://localhost:11434',
        'embedding_model': 'nomic-embed-text',
        'chat_model': 'llama3'
    }
}

# Fonctions utilitaires
@st.cache_data
def load_sample_data():
    """Charger des données d'exemple si la DB n'est pas disponible"""
    return [
        {
            'id': 'sample1',
            'title': 'Deep Learning for Computer Vision',
            'abstract': 'This paper explores deep learning techniques for computer vision applications.',
            'authors': ['John Doe', 'Jane Smith'],
            'categories': ['cs.CV', 'cs.AI'],
            'published': '2024-01-15T00:00:00Z',
            'score': 0.95
        },
        {
            'id': 'sample2',
            'title': 'Natural Language Processing with Transformers',
            'abstract': 'A comprehensive study on transformer architectures for NLP tasks.',
            'authors': ['Alice Brown', 'Bob Wilson'],
            'categories': ['cs.CL', 'cs.AI'],
            'published': '2024-02-01T00:00:00Z',
            'score': 0.87
        }
    ]

def safe_import_modules():
    """Import sécurisé des modules custom"""
    modules = {}
    
    # Essayer d'importer data_ingestion
    try:
        from data_ingestion import DataIngestion
        modules['ingestion'] = DataIngestion
        st.success("✅ Module d'ingestion chargé")
    except Exception as e:
        st.warning(f"⚠️ Module d'ingestion non disponible: {str(e)[:50]}")
        modules['ingestion'] = None
    
    # Essayer d'importer search_engine
    try:
        # Assuming search_engine exists
        # from search_engine import SearchEngine
        # modules['search'] = SearchEngine
        modules['search'] = None
        st.info("ℹ️ Module de recherche en attente")
    except Exception as e:
        st.warning(f"⚠️ Module de recherche non disponible: {str(e)[:50]}")
        modules['search'] = None
    
    # Essayer d'importer visualization
    try:
        from visualization import Visualization
        modules['viz'] = Visualization
        st.success("✅ Module de visualisation chargé")
    except Exception as e:
        st.warning(f"⚠️ Module de visualisation non disponible: {str(e)[:50]}")
        modules['viz'] = None
    
    return modules

def simple_search(query, data):
    """Recherche simple dans les données"""
    if not query:
        return data
    
    query_lower = query.lower()
    results = []
    
    for item in data:
        title_match = query_lower in item['title'].lower()
        abstract_match = query_lower in item['abstract'].lower()
        
        if title_match or abstract_match:
            # Calculer un score simple
            score = 0
            if title_match:
                score += 0.7
            if abstract_match:
                score += 0.5
            
            item['score'] = min(score, 1.0)
            results.append(item)
    
    return sorted(results, key=lambda x: x['score'], reverse=True)

def display_paper(paper):
    """Afficher un article de manière propre"""
    with st.container():
        # Score
        if 'score' in paper:
            st.markdown(f"**Score:** {paper['score']:.2f}")
        
        # Titre
        st.markdown(f"### {paper['title']}")
        
        # Métadonnées
        col1, col2 = st.columns(2)
        
        with col1:
            if 'authors' in paper:
                authors = paper['authors']
                if isinstance(authors, list):
                    st.markdown(f"**Auteurs:** {', '.join(authors[:3])}{'...' if len(authors) > 3 else ''}")
                else:
                    st.markdown(f"**Auteurs:** {authors}")
        
        with col2:
            if 'published' in paper:
                try:
                    pub_date = pd.to_datetime(paper['published']).strftime('%Y-%m-%d')
                    st.markdown(f"**Publié:** {pub_date}")
                except:
                    st.markdown(f"**Publié:** {paper['published']}")
        
        # Catégories
        if 'categories' in paper:
            categories = paper['categories']
            if isinstance(categories, list):
                cat_str = ', '.join(categories[:3])
            else:
                cat_str = categories
            st.markdown(f"**Catégories:** {cat_str}")
        
        # Résumé
        st.markdown("**Résumé:**")
        abstract = paper.get('abstract', 'Pas de résumé disponible')
        st.write(abstract[:500] + "..." if len(abstract) > 500 else abstract)
        
        # Lien PDF si disponible
        if 'pdf_url' in paper:
            st.markdown(f"[📄 Voir le PDF]({paper['pdf_url']})")
        
        st.markdown("---")

# Interface principale
def main():
    # Import des modules
    modules = safe_import_modules()
    
    # Sidebar pour la configuration
    st.sidebar.title("⚙️ Configuration")
    
    # Mode de fonctionnement
    use_real_db = st.sidebar.checkbox("Utiliser la vraie base de données", value=False)
    
    if not use_real_db:
        st.sidebar.info("Mode démo avec données d'exemple")
        data = load_sample_data()
    else:
        # Essayer de charger les vraies données
        try:
            if modules['viz']:
                viz = modules['viz']()
                df = viz.get_all_metadata()
                if not df.empty:
                    # Convertir DataFrame en liste de dictionnaires
                    data = df.to_dict('records')
                    st.sidebar.success(f"✅ {len(data)} articles chargés")
                else:
                    st.sidebar.warning("Base de données vide, utilisation des données d'exemple")
                    data = load_sample_data()
            else:
                st.sidebar.error("Module de visualisation non disponible")
                data = load_sample_data()
        except Exception as e:
            st.sidebar.error(f"Erreur DB: {str(e)[:50]}")
            data = load_sample_data()
    
    # Interface de recherche
    st.header("🔍 Recherche")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_input(
            "Rechercher des articles:",
            placeholder="Ex: deep learning, neural networks, computer vision..."
        )
    
    with col2:
        search_button = st.button("🔍 Rechercher", type="primary")
    
    # Filtres
    with st.expander("🎛️ Filtres avancés"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Filtre par nombre de résultats
            max_results = st.slider("Nombre max de résultats", 1, 50, 10)
        
        with col2:
            # Filtre par score minimum (si disponible)
            min_score = st.slider("Score minimum", 0.0, 1.0, 0.0, 0.1)
        
        with col3:
            # Tri
            sort_by = st.selectbox("Trier par", ["Score", "Date", "Titre"])
    
    # Effectuer la recherche
    if search_button or query:
        with st.spinner("Recherche en cours..."):
            try:
                results = simple_search(query, data)
                
                # Appliquer les filtres
                if min_score > 0:
                    results = [r for r in results if r.get('score', 0) >= min_score]
                
                results = results[:max_results]
                
                # Afficher les résultats
                st.header(f"📊 Résultats ({len(results)} trouvés)")
                
                if results:
                    # Statistiques rapides
                    if len(results) > 1:
                        avg_score = sum(r.get('score', 0) for r in results) / len(results)
                        st.info(f"Score moyen: {avg_score:.2f}")
                    
                    # Afficher chaque résultat
                    for i, result in enumerate(results, 1):
                        st.subheader(f"Résultat #{i}")
                        display_paper(result)
                else:
                    st.warning("Aucun résultat trouvé pour votre recherche.")
                    st.info("💡 Essayez des termes plus généraux ou vérifiez l'orthographe.")
            
            except Exception as e:
                st.error(f"Erreur lors de la recherche: {str(e)}")
                st.info("Utilisation du mode démo...")
                results = simple_search(query, load_sample_data())[:max_results]
                for result in results:
                    display_paper(result)
    
    # Onglets pour les différentes fonctionnalités
    st.header("📈 Analyses et Visualisations")
    
    tab1, tab2, tab3 = st.tabs(["📊 Statistiques", "📈 Visualisations", "⚙️ Outils"])
    
    with tab1:
        st.subheader("Statistiques de la base")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total d'articles", len(data))
        
        with col2:
            # Compter les auteurs uniques
            all_authors = set()
            for item in data:
                authors = item.get('authors', [])
                if isinstance(authors, list):
                    all_authors.update(authors)
            st.metric("Auteurs uniques", len(all_authors))
        
        with col3:
            # Compter les catégories
            all_categories = set()
            for item in data:
                cats = item.get('categories', [])
                if isinstance(cats, list):
                    all_categories.update(cats)
            st.metric("Catégories", len(all_categories))
        
        with col4:
            # Articles récents (derniers 30 jours)
            recent_count = 0
            for item in data:
                try:
                    pub_date = pd.to_datetime(item.get('published', ''))
                    if (datetime.now() - pub_date.tz_localize(None)).days <= 30:
                        recent_count += 1
                except:
                    pass
            st.metric("Articles récents", recent_count)
    
    with tab2:
        if modules['viz']:
            try:
                viz = modules['viz']()
                
                st.subheader("Distribution des catégories")
                fig1 = viz.create_category_distribution()
                if fig1:
                    st.plotly_chart(fig1, use_container_width=True)
                
                st.subheader("Timeline des publications")
                fig2 = viz.create_publication_timeline()
                if fig2:
                    st.plotly_chart(fig2, use_container_width=True)
                
            except Exception as e:
                st.warning(f"Erreur visualisation: {str(e)[:100]}")
                st.info("Visualisations basiques disponibles en mode démo")
                
                # Graphique simple des catégories
                try:
                    all_cats = []
                    for item in data:
                        cats = item.get('categories', [])
                        if isinstance(cats, list):
                            all_cats.extend(cats)
                    
                    if all_cats:
                        cat_counts = pd.Series(all_cats).value_counts().head(10)
                        fig = px.bar(
                            x=cat_counts.index,
                            y=cat_counts.values,
                            title="Top 10 des catégories"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e2:
                    st.error(f"Erreur graphique simple: {str(e2)[:50]}")
        else:
            st.info("Module de visualisation non disponible")
    
    with tab3:
        st.subheader("Outils d'administration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Actualiser les données"):
                st.cache_data.clear()
                st.success("Cache vidé! Rechargez la page.")
        
        with col2:
            if st.button("📊 Exporter les résultats"):
                if 'results' in locals() and results:
                    df_export = pd.DataFrame(results)
                    csv = df_export.to_csv(index=False)
                    st.download_button(
                        "⬇️ Télécharger CSV",
                        csv,
                        "arxiv_results.csv",
                        "text/csv"
                    )
                else:
                    st.warning("Aucun résultat à exporter")
        
        # Informations système
        st.subheader("Informations système")
        st.text(f"Python: {sys.version.split()[0]}")
        st.text(f"Streamlit: {st.__version__}")
        st.text(f"Répertoire: {os.getcwd()}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Erreur critique: {str(e)}")
        st.info("L'application fonctionne en mode dégradé")
        st.code(f"Détails de l'erreur:\n{str(e)}")