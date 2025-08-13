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

def init_database():
    """Initialise seulement la base de données"""
    try:
        from database import VectorDatabase
        return VectorDatabase()
    except Exception as e:
        st.error(f"Erreur DB: {e}")
        return None

def init_search_engine():
    """Initialise seulement le moteur de recherche"""
    try:
        from search_engine import HybridSearchEngine
        return HybridSearchEngine()
    except Exception as e:
        st.error(f"Erreur Search: {e}")
        return None

def init_analytics():
    """Initialise seulement les analytics"""
    try:
        from analytics import AnalyticsEngine
        return AnalyticsEngine()
    except Exception as e:
        st.error(f"Erreur Analytics: {e}")
        return None

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
                    db = init_database()
                    if db:
                        try:
                            count = db.count_documents()
                            st.success(f"✅ DB OK ({count} docs)")
                        except:
                            st.success("✅ DB OK (vide)")
                    else:
                        st.error("❌ DB KO")
        
        with col2:
            if st.button("Test Search"):
                with st.spinner("Test..."):
                    search = init_search_engine()
                    if search:
                        st.success("✅ Search OK")
                    else:
                        st.error("❌ Search KO")
        
        with col3:
            if st.button("Test Analytics"):
                with st.spinner("Test..."):
                    analytics = init_analytics()
                    if analytics:
                        st.success("✅ Analytics OK")
                    else:
                        st.error("❌ Analytics KO")

def show_search_page():
    """Page de recherche avec initialisation à la demande"""
    st.header("🔍 Recherche d'Articles")
    
    # Interface de recherche
    query = st.text_input("Votre recherche", placeholder="Ex: machine learning computer vision")
    
    col1, col2 = st.columns(2)
    with col1:
        top_k = st.slider("Nombre de résultats", 5, 20, 10)
    with col2:
        expand_query = st.checkbox("Expansion de requête", value=True)
    
    search_button = st.button("🔍 Rechercher", type="primary")
    
    if search_button and query:
        # Initialisation à la demande
        with st.spinner("Initialisation du moteur de recherche..."):
            db = init_database()
            if not db:
                st.error("❌ Impossible d'initialiser la base de données")
                return
            
            # Vérifier s'il y a des documents
            try:
                doc_count = db.count_documents()
                if doc_count == 0:
                    st.warning("⚠️ Aucun document indexé. Allez d'abord dans 'Ingestion'.")
                    return
                else:
                    st.info(f"📊 {doc_count} documents dans la base")
            except Exception as e:
                st.error(f"Erreur lors de la vérification: {e}")
                return
        
        with st.spinner("Initialisation du moteur de recherche..."):
            search_engine = init_search_engine()
            if not search_engine:
                st.error("❌ Impossible d'initialiser le moteur de recherche")
                return
        
        with st.spinner("Recherche en cours..."):
            try:
                results = search_engine.hybrid_search(
                    query=query, 
                    top_k=top_k, 
                    expand_query=expand_query
                )
                
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
                            
                            # Métadonnées
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                # Auteurs
                                authors = result['metadata'].get('authors', '[]')
                                try:
                                    import json
                                    authors_list = json.loads(authors)
                                    if authors_list:
                                        st.write(f"**Auteurs:** {', '.join(authors_list[:2])}")
                                except:
                                    pass
                                
                                # Date
                                published = result['metadata'].get('published', '')
                                if published:
                                    st.write(f"**Publié:** {published}")
                                
                                # Résumé
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
                    
            except Exception as e:
                st.error(f"❌ Erreur de recherche: {str(e)}")
                st.code(str(e))

def show_analytics_page():
    """Page analytics avec initialisation à la demande"""
    st.header("📊 Analytics")
    
    tab1, tab2 = st.tabs(["📈 Tendances temporelles", "📊 Catégories"])
    
    with tab1:
        st.subheader("Évolution des publications")
        
        if st.button("Générer graphique temporel"):
            with st.spinner("Initialisation des analytics..."):
                analytics = init_analytics()
                if not analytics:
                    st.error("❌ Impossible d'initialiser les analytics")
                    return
            
            with st.spinner("Génération du graphique..."):
                try:
                    fig = analytics.create_temporal_chart()
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("📊 Pas assez de données pour générer le graphique")
                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")
    
    with tab2:
        st.subheader("Distribution des catégories")
        
        if st.button("Générer distribution"):
            with st.spinner("Initialisation des analytics..."):
                analytics = init_analytics()
                if not analytics:
                    st.error("❌ Impossible d'initialiser les analytics")
                    return
            
            with st.spinner("Génération du graphique..."):
                try:
                    fig = analytics.create_category_chart(15)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("📊 Pas assez de données pour générer le graphique")
                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")

def show_ingestion_page():
    """Page d'ingestion avec initialisation à la demande"""
    st.header("📥 Ingestion d'Articles")
    
    # Bouton d'ingestion rapide
    if st.button("🚀 Ingérer des articles populaires (IA/ML)", type="primary"):
        with st.spinner("Initialisation de l'ingestion..."):
            try:
                from ingestion import ArxivIngestion
                ingestion = ArxivIngestion()
                
                with st.spinner("Recherche et ingestion des articles... (peut prendre 2-3 minutes)"):
                    # Ingestion réduite pour les tests
                    added = ingestion.quick_ingest(
                        topics=["machine learning", "deep learning"], 
                        max_per_topic=15
                    )
                    st.success(f"✅ {added} documents ajoutés avec succès!")
                    
                    # Afficher quelques stats
                    db = init_database()
                    if db:
                        total = db.count_documents()
                        st.info(f"📊 Total dans la base: {total} documents")
                
            except Exception as e:
                st.error(f"❌ Erreur d'ingestion: {str(e)}")
                st.code(str(e))
    
    st.markdown("""
    ### 💡 Conseils:
    - Commencez par cette ingestion rapide
    - Attendez la fin avant de faire une recherche
    - Les articles sont en anglais
    """)
    
    # Ingestion personnalisée
    with st.expander("🔧 Ingestion personnalisée"):
        query = st.text_input("Requête de recherche", "computer vision")
        max_results = st.slider("Nombre max", 10, 100, 30)
        
        if st.button("Lancer l'ingestion personnalisée"):
            with st.spinner("Ingestion personnalisée..."):
                try:
                    from ingestion import ArxivIngestion
                    ingestion = ArxivIngestion()
                    
                    docs = ingestion.search_arxiv(query, max_results)
                    added = ingestion.ingest_documents(docs)
                    st.success(f"✅ {added} documents ajoutés sur {len(docs)} trouvés")
                    
                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")

if __name__ == "__main__":
    main()