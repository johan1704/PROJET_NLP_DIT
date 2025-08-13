import streamlit as st
import sys
import os
from pathlib import Path
import time

# Configuration de la page
st.set_page_config(
    page_title="ArXiv Search Engine",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé simple
st.markdown("""
<style>
.result-card {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 15px;
    margin: 10px 0;
    background-color: #fafafa;
}
.score-badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 12px;
    font-size: 0.8em;
    font-weight: bold;
    margin: 2px;
    background-color: #4CAF50;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# ----------------------------
# Initialisation avec cache
# ----------------------------

@st.cache_resource
def get_database():
    from database import VectorDatabase
    return VectorDatabase()

@st.cache_resource
def get_search_engine():
    from search_engine import HybridSearchEngine
    return HybridSearchEngine()

@st.cache_resource
def get_analytics():
    from analytics import AnalyticsEngine
    return AnalyticsEngine()

# ----------------------------
# Pages
# ----------------------------

def main():
    st.title("🔬 ArXiv Advanced Search Engine")
    
    # Sidebar simple
    with st.sidebar:
        st.header("Navigation")
        page = st.selectbox("Choisir une page", [
            "🏠 Accueil",
            "🔍 Recherche",
            "📊 Analytics", 
            "📥 Ingestion"
        ])
    
    # Navigation des pages
    if page == "🏠 Accueil":
        show_home_page()
    elif page == "🔍 Recherche":
        show_search_page()
    elif page == "📊 Analytics":
        show_analytics_page()
    elif page == "📥 Ingestion":
        show_ingestion_page()

def show_home_page():
    """Page d'accueil simple"""
    st.header("🏠 Bienvenue dans ArXiv Search Engine")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔍 Recherche Hybride")
        st.write("Combinaison de recherche sémantique et lexicale")
        
        st.subheader("📊 Analytics")
        st.write("Visualisation des tendances")
    
    with col2:
        st.subheader("📥 Ingestion")
        st.write("Import automatique d'articles arXiv")
        
        st.subheader("🤖 IA Intégrée")
        st.write("Expansion de requête avec Ollama")
    
    st.header("🚀 Démarrage rapide")
    st.markdown("""
    1. **Ingestion** : Commencez par indexer quelques articles
    2. **Recherche** : Testez des requêtes en anglais
    3. **Analytics** : Visualisez les tendances
    """)
    
    # Test de connectivité
    with st.expander("🔧 Test des composants"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Test Database"):
                with st.spinner("Test..."):
                    try:
                        db = get_database()
                        count = db.count_documents()
                        st.success(f"✅ DB OK ({count} docs)")
                    except:
                        st.error("❌ DB KO")
        
        with col2:
            if st.button("Test Search"):
                with st.spinner("Test..."):
                    try:
                        _ = get_search_engine()
                        st.success("✅ Search OK")
                    except:
                        st.error("❌ Search KO")
        
        with col3:
            if st.button("Test Analytics"):
                with st.spinner("Test..."):
                    try:
                        _ = get_analytics()
                        st.success("✅ Analytics OK")
                    except:
                        st.error("❌ Analytics KO")

def show_search_page():
    """Page de recherche"""
    st.header("🔍 Recherche d'Articles")
    
    query = st.text_input("Votre recherche", placeholder="Ex: machine learning computer vision")
    
    col1, col2 = st.columns(2)
    with col1:
        top_k = st.slider("Nombre de résultats", 5, 20, 10)
    with col2:
        expand_query = st.checkbox("Expansion de requête", value=True)
    
    if st.button("🔍 Rechercher", type="primary") and query:
        try:
            db = get_database()
            doc_count = db.count_documents()
            if doc_count == 0:
                st.warning("⚠️ Aucun document indexé. Allez d'abord dans 'Ingestion'.")
                return
            st.info(f"📊 {doc_count} documents dans la base")
        except Exception as e:
            st.error(f"Erreur DB: {e}")
            return
        
        try:
            search_engine = get_search_engine()
            results = search_engine.hybrid_search(
                query=query, 
                top_k=top_k, 
                expand_query=expand_query
            )
        except Exception as e:
            st.error(f"Erreur Search: {e}")
            return
        
        if results:
            st.success(f"✅ {len(results)} résultats trouvés")
            for i, result in enumerate(results, 1):
                with st.container():
                    st.markdown(f"""
                    <div class="result-card">
                        <h4>{i}. {result['metadata'].get('title', 'Sans titre')}</h4>
                        <span class="score-badge">Score: {result.get('hybrid_score', 0):.3f}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        import json
                        authors = result['metadata'].get('authors', '[]')
                        try:
                            authors_list = json.loads(authors)
                            if authors_list:
                                st.write(f"**Auteurs:** {', '.join(authors_list[:2])}")
                        except:
                            pass
                        
                        published = result['metadata'].get('published', '')
                        if published:
                            st.write(f"**Publié:** {published}")
                        
                        doc = result.get('document', '')
                        if len(doc) > 300:
                            doc = doc[:300] + "..."
                        st.write(f"**Résumé:** {doc}")
                    with col2:
                        arxiv_url = result['metadata'].get('url', '')
                        if arxiv_url:
                            st.link_button("📄 arXiv", arxiv_url)
                    
                    st.divider()
        else:
            st.warning("❌ Aucun résultat trouvé")

def show_analytics_page():
    """Page analytics"""
    st.header("📊 Analytics")
    
    tab1, tab2 = st.tabs(["📈 Tendances temporelles", "📊 Catégories"])
    
    with tab1:
        if st.button("Générer graphique temporel"):
            try:
                analytics = get_analytics()
                fig = analytics.create_temporal_chart()
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("📊 Pas assez de données pour générer le graphique")
            except Exception as e:
                st.error(f"Erreur: {e}")
    
    with tab2:
        if st.button("Générer distribution"):
            try:
                analytics = get_analytics()
                fig = analytics.create_category_chart(15)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("📊 Pas assez de données pour générer le graphique")
            except Exception as e:
                st.error(f"Erreur: {e}")

def show_ingestion_page():
    """Page ingestion"""
    st.header("📥 Ingestion d'Articles")
    
    if st.button("🚀 Ingérer des articles populaires (IA/ML)", type="primary"):
        try:
            from ingestion import ArxivIngestion
            ingestion = ArxivIngestion()
            added = ingestion.quick_ingest(
                topics=["machine learning", "deep learning"], 
                max_per_topic=15
            )
            st.success(f"✅ {added} documents ajoutés")
            total = get_database().count_documents()
            st.info(f"📊 Total: {total} documents")
        except Exception as e:
            st.error(f"Erreur ingestion: {e}")
    
    with st.expander("🔧 Ingestion personnalisée"):
        query = st.text_input("Requête de recherche", "computer vision")
        max_results = st.slider("Nombre max", 10, 100, 30)
        if st.button("Lancer l'ingestion personnalisée"):
            try:
                from ingestion import ArxivIngestion
                ingestion = ArxivIngestion()
                docs = ingestion.search_arxiv(query, max_results)
                added = ingestion.ingest_documents(docs)
                st.success(f"✅ {added} documents ajoutés sur {len(docs)}")
            except Exception as e:
                st.error(f"Erreur ingestion: {e}")

if __name__ == "__main__":
    main()
