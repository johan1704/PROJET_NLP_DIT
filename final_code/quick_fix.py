import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="ArXiv Search Engine",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS simple
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

# === Fonctions d'initialisation avec debug et cache ===
@st.cache_resource
def init_database():
    st.write("📡 Import de VectorDatabase...")
    from database import VectorDatabase
    st.write("✅ Import OK, instanciation...")
    return VectorDatabase()

@st.cache_resource
def init_search_engine():
    st.write("📡 Import de HybridSearchEngine...")
    from search_engine import HybridSearchEngine
    st.write("✅ Import OK, instanciation...")
    return HybridSearchEngine()

@st.cache_resource
def init_analytics():
    st.write("📡 Import de AnalyticsEngine...")
    from analytics import AnalyticsEngine
    st.write("✅ Import OK, instanciation...")
    return AnalyticsEngine()

# === Navigation ===
def main():
    st.title("🔬 ArXiv Advanced Search Engine")

    with st.sidebar:
        st.header("Navigation")
        page = st.selectbox("Choisir une page", [
            "🏠 Accueil",
            "🔍 Recherche",
            "📊 Analytics",
            "📥 Ingestion"
        ])

    if page == "🏠 Accueil":
        show_home_page()
    elif page == "🔍 Recherche":
        show_search_page()
    elif page == "📊 Analytics":
        show_analytics_page()
    elif page == "📥 Ingestion":
        show_ingestion_page()

# === Pages ===
def show_home_page():
    st.header("🏠 Bienvenue dans ArXiv Search Engine")
    st.info("💡 Utilisez les boutons ci-dessous pour tester la connexion aux composants.")

    with st.expander("🔧 Test des composants"):
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Test Database"):
                with st.spinner("Test DB..."):
                    try:
                        db = init_database()
                        count = db.count_documents()
                        st.success(f"✅ DB OK ({count} docs)")
                    except Exception as e:
                        st.error(f"❌ DB KO: {e}")

        with col2:
            if st.button("Test Search"):
                with st.spinner("Test Search..."):
                    try:
                        search = init_search_engine()
                        st.success("✅ Search OK")
                    except Exception as e:
                        st.error(f"❌ Search KO: {e}")

        with col3:
            if st.button("Test Analytics"):
                with st.spinner("Test Analytics..."):
                    try:
                        analytics = init_analytics()
                        st.success("✅ Analytics OK")
                    except Exception as e:
                        st.error(f"❌ Analytics KO: {e}")

def show_search_page():
    st.header("🔍 Recherche d'Articles")
    query = st.text_input("Votre recherche", placeholder="Ex: machine learning computer vision")
    top_k = st.slider("Nombre de résultats", 5, 20, 10)
    expand_query = st.checkbox("Expansion de requête", value=True)

    if st.button("🔍 Rechercher") and query:
        try:
            db = init_database()
            if db.count_documents() == 0:
                st.warning("⚠️ Aucun document indexé.")
                return
            search_engine = init_search_engine()
            results = search_engine.hybrid_search(query=query, top_k=top_k, expand_query=expand_query)
            if results:
                st.success(f"{len(results)} résultats trouvés")
            else:
                st.warning("Aucun résultat trouvé.")
        except Exception as e:
            st.error(f"Erreur de recherche: {e}")

def show_analytics_page():
    st.header("📊 Analytics")
    if st.button("📈 Générer tendances"):
        try:
            analytics = init_analytics()
            fig = analytics.create_temporal_chart()
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Erreur Analytics: {e}")

def show_ingestion_page():
    st.header("📥 Ingestion d'Articles")
    if st.button("🚀 Ingestion rapide"):
        try:
            st.write("📡 Import de ArxivIngestion...")
            from ingestion import ArxivIngestion
            ingestion = ArxivIngestion()
            st.info("⏳ Ingestion en cours...")
            added = ingestion.quick_ingest(["machine learning"], max_per_topic=5)
            st.success(f"{added} documents ajoutés")
        except Exception as e:
            st.error(f"Erreur ingestion: {e}")

if __name__ == "__main__":
    main()
