import streamlit as st
import sys
import os
from pathlib import Path

# Configuration de la page
st.set_page_config(
    page_title="ArXiv Search Engine - Debug",
    page_icon="🔬",
    layout="wide"
)

def main():
    st.title("🔬 ArXiv Search Engine - Version Debug")
    
    st.header("🔍 Test des composants individuels")
    
    # Test 1: Imports de base
    with st.expander("1. Test des imports Python", expanded=True):
        st.write("Test en cours...")
        
        try:
            import chromadb
            st.success("✅ chromadb importé")
        except Exception as e:
            st.error(f"❌ chromadb: {e}")
        
        try:
            import ollama
            st.success("✅ ollama importé")
        except Exception as e:
            st.error(f"❌ ollama: {e}")
        
        try:
            import arxiv
            st.success("✅ arxiv importé")
        except Exception as e:
            st.error(f"❌ arxiv: {e}")
        
        try:
            import plotly
            st.success("✅ plotly importé")
        except Exception as e:
            st.error(f"❌ plotly: {e}")
    
    # Test 2: Ollama connection
    with st.expander("2. Test connexion Ollama"):
        if st.button("Tester Ollama"):
            with st.spinner("Test en cours..."):
                try:
                    import ollama
                    client = ollama.Client(host="http://localhost:11434")
                    models = client.list()
                    st.success("✅ Ollama accessible")
                    st.json(models)
                except Exception as e:
                    st.error(f"❌ Erreur Ollama: {e}")
                    st.markdown("""
                    **Solutions:**
                    1. Lancez `ollama serve` dans un autre terminal
                    2. Installez les modèles: `ollama pull nomic-embed-text` et `ollama pull gemma2:2b`
                    """)
    
    # Test 3: ChromaDB
    with st.expander("3. Test ChromaDB"):
        if st.button("Tester ChromaDB"):
            with st.spinner("Test en cours..."):
                try:
                    import chromadb
                    from chromadb.config import Settings
                    
                    client = chromadb.PersistentClient(
                        path="./test_chroma",
                        settings=Settings(anonymized_telemetry=False)
                    )
                    collection = client.get_or_create_collection("test")
                    st.success("✅ ChromaDB fonctionne")
                    st.write(f"Collections: {len(client.list_collections())}")
                except Exception as e:
                    st.error(f"❌ Erreur ChromaDB: {e}")
    
    # Test 4: Import des modules locaux
    with st.expander("4. Test des modules locaux"):
        if st.button("Tester les imports locaux"):
            with st.spinner("Test en cours..."):
                try:
                    # Test config
                    import config
                    st.success("✅ config.py importé")
                    
                    # Test database (sans initialiser)
                    from database import VectorDatabase
                    st.success("✅ database.py importé")
                    
                    # Test search_engine
                    from search_engine import HybridSearchEngine
                    st.success("✅ search_engine.py importé")
                    
                    # Test analytics
                    from analytics import AnalyticsEngine
                    st.success("✅ analytics.py importé")
                    
                    # Test ingestion
                    from ingestion import ArxivIngestion
                    st.success("✅ ingestion.py importé")
                    
                except Exception as e:
                    st.error(f"❌ Erreur import: {e}")
                    st.code(str(e))
    
    # Test 5: Interface simple
    st.header("🚀 Interface de test simple")
    
    name = st.text_input("Votre nom")
    if name:
        st.write(f"Bonjour {name}!")
    
    if st.button("Test de bouton"):
        st.balloons()
        st.success("Le bouton fonctionne!")
    
    # Informations système
    with st.expander("ℹ️ Informations système"):
        st.write(f"**Python:** {sys.version}")
        st.write(f"**Streamlit:** {st.__version__}")
        st.write(f"**Répertoire courant:** {os.getcwd()}")
        st.write(f"**Path Python:** {sys.path[:3]}")

if __name__ == "__main__":
    main()