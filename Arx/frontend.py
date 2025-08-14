import streamlit as st
import requests
import json
from datetime import datetime
import plotly.express as px
import pandas as pd

# Configuration
API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="ArXiv Search Engine",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Moteur de Recherche ArXiv")
st.markdown("Recherche sémantique dans la littérature scientifique")

# Sidebar pour les contrôles
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Indexation
    st.subheader("Indexation")
    index_query = st.text_input("Requête d'indexation", "machine learning")
    index_count = st.slider("Nombre d'articles", 10, 100, 50)
    
    if st.button("📥 Indexer Articles"):
        with st.spinner("Indexation en cours..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/index",
                    params={"query": index_query, "max_results": index_count}
                )
                if response.status_code == 200:
                    st.success(response.json()["message"])
                else:
                    st.error("Erreur lors de l'indexation")
            except Exception as e:
                st.error(f"Erreur de connexion: {e}")
    
    # Statistiques
    try:
        stats_response = requests.get(f"{API_BASE_URL}/stats")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            st.metric("Articles indexés", stats["total_papers"])
    except:
        st.metric("Articles indexés", "N/A")

# Interface de recherche
col1, col2 = st.columns([3, 1])

with col1:
    search_query = st.text_input("🔍 Recherche", placeholder="Tapez votre requête...")

with col2:
    max_results = st.selectbox("Résultats", [5, 10, 20, 50], index=1)

# Filtres avancés
with st.expander("🎛️ Filtres avancés"):
    category_filter = st.text_input("Catégorie", placeholder="cs.AI, stat.ML, etc.")

# Recherche
if search_query:
    with st.spinner("Recherche en cours..."):
        try:
            search_data = {
                "query": search_query,
                "max_results": max_results,
                "category": category_filter if category_filter else None
            }
            
            response = requests.post(
                f"{API_BASE_URL}/search",
                json=search_data
            )
            
            if response.status_code == 200:
                papers = response.json()
                
                st.success(f"Trouvé {len(papers)} articles")
                
                # Affichage des résultats
                for i, paper in enumerate(papers):
                    with st.container():
                        st.markdown("---")
                        
                        st.markdown(f"### {paper['title']}")
                        
                        # Scores détaillés
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Score Hybride", f"{paper['score']:.3f}")
                        with col2:
                            st.metric("Score BM25", f"{paper['bm25_score']:.3f}")
                        with col3:
                            st.metric("Score Sémantique", f"{paper['semantic_score']:.3f}")
                        
                        # Métadonnées
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.markdown(f"**Auteurs:** {', '.join(paper['authors'][:3])}")
                            if len(paper['authors']) > 3:
                                st.markdown(f"*et {len(paper['authors'])-3} autres...*")
                        
                        with col2:
                            pub_date = datetime.fromisoformat(paper['published'].replace('Z', '+00:00'))
                            st.markdown(f"**Publié:** {pub_date.strftime('%Y-%m-%d')}")
                        
                        with col3:
                            st.markdown(f"**Catégories:** {', '.join(paper['categories'][:2])}")
                        
                        # Résumé
                        with st.expander("📖 Résumé"):
                            st.write(paper['summary'])
                        
                        # Lien ArXiv
                        st.markdown(f"[📄 Voir sur ArXiv](https://arxiv.org/abs/{paper['id']})")
                
                # Analyse des résultats
                if papers:
                    st.markdown("---")
                    st.subheader("📊 Analyse des Résultats")
                    
                    # Distribution des catégories
                    all_categories = []
                    for paper in papers:
                        all_categories.extend(paper['categories'])
                    
                    if all_categories:
                        cat_df = pd.DataFrame(all_categories, columns=['Catégorie'])
                        cat_counts = cat_df['Catégorie'].value_counts().head(10)
                        
                        fig = px.bar(
                            x=cat_counts.values,
                            y=cat_counts.index,
                            orientation='h',
                            title="Top 10 des Catégories",
                            labels={'x': 'Nombre d\'articles', 'y': 'Catégorie'}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Distribution temporelle
                    dates = [datetime.fromisoformat(p['published'].replace('Z', '+00:00')).date() 
                            for p in papers]
                    date_df = pd.DataFrame(dates, columns=['Date'])
                    
                    fig_time = px.histogram(
                        date_df,
                        x='Date',
                        title="Distribution Temporelle des Articles"
                    )
                    st.plotly_chart(fig_time, use_container_width=True)
            
            else:
                st.error(f"Erreur de recherche: {response.status_code}")
                
        except Exception as e:
            st.error(f"Erreur: {e}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>🔬 Moteur de Recherche ArXiv - Recherche Sémantique Avancée</p>
    </div>
    """,
    unsafe_allow_html=True
)