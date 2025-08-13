#!/usr/bin/env python3
"""
Script de configuration et d'initialisation pour ArXiv Search Engine
"""

import subprocess
import sys
import os
from pathlib import Path

def install_requirements():
    """Installe les dépendances Python"""
    print("📦 Installation des dépendances Python...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dépendances installées avec succès")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'installation: {e}")
        return False

def check_ollama():
    """Vérifie si Ollama est installé et accessible"""
    print("🔍 Vérification d'Ollama...")
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Ollama est accessible")
            print("Modèles installés:")
            print(result.stdout)
            return True
        else:
            print("❌ Ollama n'est pas accessible")
            return False
    except FileNotFoundError:
        print("❌ Ollama n'est pas installé")
        return False

def install_ollama_models():
    """Installe les modèles Ollama nécessaires"""
    models = ["nomic-embed-text", "gemma2:2b"]
    
    for model in models:
        print(f"📥 Installation du modèle {model}...")
        try:
            subprocess.check_call(["ollama", "pull", model])
            print(f"✅ Modèle {model} installé")
        except subprocess.CalledProcessError as e:
            print(f"❌ Erreur lors de l'installation du modèle {model}: {e}")
            return False
    
    return True

def create_directories():
    """Crée les dossiers nécessaires"""
    dirs = ["data", "chroma_db"]
    for dir_name in dirs:
        path = Path(dir_name)
        path.mkdir(exist_ok=True)
        print(f"📁 Dossier {dir_name} créé/vérifié")

def run_initial_ingestion():
    """Lance une ingestion initiale de test"""
    print("🚀 Lancement de l'ingestion initiale...")
    try:
        from ingestion import ArxivIngestion
        ingestion = ArxivIngestion()
        
        # Ingestion de quelques articles de test
        added = ingestion.quick_ingest(
            topics=["machine learning", "deep learning"], 
            max_per_topic=25
        )
        print(f"✅ {added} documents ajoutés lors de l'ingestion initiale")
        return True
    except Exception as e:
        print(f"❌ Erreur lors de l'ingestion: {e}")
        return False

def main():
    print("🔬 Configuration d'ArXiv Search Engine")
    print("="*50)
    
    # Étape 1: Créer les dossiers
    create_directories()
    
    # Étape 2: Installer les dépendances Python
    
    if not install_requirements():
        print("❌ Échec de l'installation des dépendances")
        sys.exit(1)
    
    # Étape 3: Vérifier Ollama
    if not check_ollama():
        print("\n⚠️  Ollama n'est pas installé ou accessible.")
        print("Veuillez installer Ollama depuis: https://ollama.ai")
        print("Puis relancez ce script.")
        sys.exit(1)
    
    # Étape 4: Installer les modèles Ollama
    if not install_ollama_models():
        print("❌ Échec de l'installation des modèles Ollama")
        sys.exit(1)
    
    # Étape 5: Ingestion initiale (optionnelle)
    choice = input("\n🤖 Voulez-vous lancer une ingestion initiale de test ? (y/N): ")
    if choice.lower() in ['y', 'yes', 'o', 'oui']:
        run_initial_ingestion()
    
    print("\n🎉 Configuration terminée avec succès!")
    print("\nPour lancer l'application:")
    print("streamlit run app.py")

if __name__ == "__main__":
    main()




POC ---explication des termes suivants :
data warehouse , data marts , data lake , database 


-Modèle de Tableau , Graphique , Visualization déjà realisé par la cgrae 
-Accès aux sources de données,
-