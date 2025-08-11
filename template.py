import os

# Structure du projet
structure = {
    "arxiv-search-engine": {
        "data": {},
        "src": {
            "data_ingestion.py": "# data_ingestion.py\n# Pipeline d'ingestion des données\n",
            "search_engine.py": "# search_engine.py\n# Moteur de recherche\n",
            "visualization.py": "# visualization.py\n# Visualisations\n",
            "streamlit_app.py": "# streamlit_app.py\n# Interface utilisateur Streamlit\n"
        },
        "config": {
            "config.yaml": "# Configuration du projet\n"
        },
        "requirements.txt": "# Dépendances du projet\n"
    }
}

def create_structure(base_path, struct):
    for name, content in struct.items():
        path = os.path.join(base_path, name)
        if isinstance(content, dict):  # Dossier
            os.makedirs(path, exist_ok=True)
            create_structure(path, content)
        else:  # Fichier
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

if __name__ == "__main__":
    create_structure("..", structure)
    print("Structure de projet créée ✅")
