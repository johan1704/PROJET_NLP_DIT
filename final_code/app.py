import streamlit as st
import json
from database import VectorDatabase
from search_engine import HybridSearchEngine
from analytics import AnalyticsEngine
from ingestion import run_ingestion_interface

# Configuration de la page
st.set_page_config(
    page_title="ArXiv Search Engine",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
.metric-container {
    background-color: #f0f2f6;
    padding: 10px;
    border-radius: 5px;
    margin: 5px 0;
}
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
}
.score-high { background-color: #4CAF50; color: white; }
.score-medium { background-color: #FF9800; color: white; }
.score-low { background-color: #9E9E9E; color: white; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_components():
    return VectorDatabase(), HybridSearchEngine(), AnalyticsEngine()

def main():
    st.title("🔬 ArXiv Advanced Search Engine")
    
    # Initialisation des composants
    db, search_engine, analytics = init_components()
    
    # Sidebar pour la navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.selectbox("Choisir une page", [
            "🔍 Recherche",
            "📊 Analytics", 
            "📥 Ingestion"
        ])
        
        # Statistiques générales
        st.header("📈 Statistiques")
        total_docs = db.count_documents()
        st.metric("Documents indexés", total_docs)
    
    # Page de recherche
    if page == "🔍 Recherche":
        show_search_page(db, search_engine)
    
    # Page d'analytics
    elif page == "📊 Analytics":
        show_analytics_page(analytics)
    
    # Page d'ingestion
    elif page == "📥 Ingestion":
        run_ingestion_interface()

def show_search_page(db, search_engine):
    st.header("🔍 Recherche Hybride")
    
    # Interface de recherche
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_input(
            "Votre recherche", 
            placeholder="Ex: deep learning for computer vision",
            key="main_search"
        )
    
    with col2:
        search_button = st.button("🔍 Rechercher", type="primary", use_container_width=True)
    
    # Options avancées
    with st.expander("⚙️ Options avancées"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            expand_query = st.checkbox("Expansion de requête", value=True)
            semantic_weight = st.slider("Poids sémantique", 0.0, 1.0, 0.6, 0.1)
        
        with col2:
            top_k = st.slider("Nombre de résultats", 5, 50, 10)
            generate_summary = st.checkbox("Générer un résumé", value=True)
        
        with col3:
            # Filtres
            metadata = db.get_all_metadata()
            
            selected_categories = st.multiselect(
                "Catégories", 
                ["Toutes"] + metadata.get('categories', []),
                default=["Toutes"]
            )
            
            selected_years = st.multiselect(
                "Années",
                ["Toutes"] + metadata.get('years', []),
                default=["Toutes"]
            )
    
    # Exécution de la recherche
    if search_button and query:
        with st.spinner("Recherche en cours..."):
            # Préparer les filtres
            filters = {}
            if selected_categories and "Toutes" not in selected_categories:
                filters['categories'] = selected_categories[0] if selected_categories else None
            
            # Lancer la recherche
            results = search_engine.hybrid_search(
                query=query,
                top_k=top_k,
                expand_query=expand_query,
                semantic_weight=semantic_weight,
                filters=filters
            )
            
            # Afficher les résultats
            if results:
                st.success(f"✅ {len(results)} résultats trouvés")
                
                # Résumé automatique
                if generate_summary:
                    with st.expander("📝 Résumé synthétique", expanded=True):
                        summary = search_engine.generate_summary(results, query)
                        st.write(summary)
                
                # Affichage des résultats
                st.header("📄 Résultats")
                
                for i, result in enumerate(results, 1):
                    with st.container():
                        # Score badges
                        def get_score_class(score):
                            if score > 0.7: return "score-high"
                            elif score > 0.4: return "score-medium"
                            else: return "score-low"
                        
                        hybrid_class = get_score_class(result.get('hybrid_score', 0))
                        semantic_class = get_score_class(result.get('semantic_score', 0))
                        bm25_class = get_score_class(result.get('bm25_score', 0))
                        
                        st.markdown(f"""
                        <div class="result-card">
                            <h4>{i}. {result['metadata'].get('title', 'Titre non disponible')}</h4>
                            <div>
                                <span class="score-badge {hybrid_class}">
                                    Hybride: {result.get('hybrid_score', 0):.3f}
                                </span>
                                <span class="score-badge {semantic_class}">
                                    Sémantique: {result.get('semantic_score', 0):.3f}
                                </span>
                                <span class="score-badge {bm25_class}">
                                    BM25: {result.get('bm25_score', 0):.3f}
                                </span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Métadonnées
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            authors = result['metadata'].get('authors', '[]')
                            try:
                                authors_list = json.loads(authors)
                                if authors_list:
                                    st.write("**Auteurs:**", ", ".join(authors_list[:3]) + 
                                           ("..." if len(authors_list) > 3 else ""))
                            except:
                                st.write("**Auteurs:** Non disponible")
                        
                        with col2:
                            categories = result['metadata'].get('categories', '[]')
                            try:
                                cat_list = json.loads(categories)
                                if cat_list:
                                    st.write("**Catégories:**", ", ".join(cat_list[:2]))
                            except:
                                st.write("**Catégories:** Non disponible")
                        
                        with col3:
                            published = result['metadata'].get('published', 'Non disponible')
                            st.write("**Publié:**", published)
                        
                        # Abstract (tronqué)
                        abstract = result.get('document', '')
                        if len(abstract) > 300:
                            abstract = abstract[:300] + "..."
                        st.write("**Résumé:**", abstract)
                        
                        # Lien arXiv
                        arxiv_url = result['metadata'].get('url', '')
                        if arxiv_url:
                            st.markdown(f"[📄 Voir sur arXiv]({arxiv_url})")
                        
                        st.divider()
            
            else:
                st.warning("❌ Aucun résultat trouvé")

def show_analytics_page(analytics):
    st.header("📊 Analytics & Visualisations")
    
    tab1, tab2, tab3 = st.tabs(["📈 Tendances temporelles", "🌐 Réseau d'auteurs", "📊 Distribution des catégories"])
    
    with tab1:
        st.subheader("Évolution temporelle des publications")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            analysis_type = st.radio("Type d'analyse", ["Corpus global", "Mots-clés spécifiques"])
            
            if analysis_type == "Mots-clés spécifiques":
                keywords_input = st.text_area(
                    "Mots-clés (un par ligne)",
                    value="machine learning\ndeep learning\nneural networks"
                )
                keywords = [k.strip() for k in keywords_input.split('\n') if k.strip()]
            else:
                keywords = None
        
        with col2:
            if st.button("Générer le graphique temporel"):
                with st.spinner("Génération du graphique..."):
                    fig = analytics.create_temporal_chart(keywords)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Pas assez de données pour générer le graphique")
    
    with tab2:
        st.subheader("Réseau de collaboration entre auteurs")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            min_collab = st.slider("Collaborations minimum", 1, 10, 2)
            max_nodes = st.slider("Nombre max d'auteurs", 20, 100, 50)
        
        with col2:
            if st.button("Générer le réseau"):
                with st.spinner("Génération du réseau..."):
                    fig = analytics.create_network_chart(min_collab, max_nodes)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Pas assez de données pour générer le réseau")
    
    with tab3:
        st.subheader("Distribution des catégories d'articles")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            top_n = st.slider("Top N catégories", 5, 30, 15)
        
        with col2:
            if st.button("Générer le graphique des catégories"):
                with st.spinner("Génération du graphique..."):
                    fig = analytics.create_category_chart(top_n)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Pas assez de données pour générer le graphique")

if __name__ == "__main__":
    main()