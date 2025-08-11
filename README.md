# PROJET_NLP_DIT
Objectif Mettre en œuvre un moteur de recherche local pour un corpus d’articles scientifiques (arXiv),
doté de capacités d’interrogation sémantique, de filtrage et de synthèse.<br>
Concepts Clés

– Base de Données Vectorielle (ChromaDB) : Stockage et recherche de vecteurs générés avec Ollama
Embeddings.
– Recherche Hybride : Fusion des scores de pertinence sémantique (vecteurs) et lexicale (e.g., BM25).
– Query Expansion : Utilisation de Gemma (via Ollama) pour reformuler la requête initiale.
– Recherche à Facettes : Filtrage des résultats basé sur des métadonnées structurées.
Fonctionnalités Attendues
• Pipeline d’Ingestion et d’Indexation : Extraction, segmentation, génération d’embeddings (Ollama) et
indexation dans ChromaDB.
• Moteur d’Interrogation Avancé : Expansion de requête, calcul et fusion des scores pour un classement
hybride.
• Interface de Recherche Web : Développement d’une application Streamlit pour la recherche et le
filtrage.
• Synthèse à la Volée : Générer un résumé synthétique des N meilleurs résultats avec Gemma.
• Analyse de Tendances : Visualiser l’évolution temporelle de mots-clés dans le corpus.
• Visualisation du Réseau d’Auteurs : Construire et afficher un graphe de co-auteurs.
