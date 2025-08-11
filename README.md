# PROJET_NLP_DIT

<h3>Objectif Mettre en œuvre un moteur de recherche local pour un corpus d’articles scientifiques (arXiv),
doté de capacités d’interrogation sémantique, de filtrage et de synthèse</h3>.<br>

<b>Concepts Clés</b>

– Base de Données Vectorielle (ChromaDB) : Stockage et recherche de vecteurs générés avec Ollama
Embeddings.<br>
– Recherche Hybride : Fusion des scores de pertinence sémantique (vecteurs) et lexicale (e.g., BM25).<br>
– Query Expansion : Utilisation de Gemma (via Ollama) pour reformuler la requête initiale.<br>
– Recherche à Facettes : Filtrage des résultats basé sur des métadonnées structurées.<br>
Fonctionnalités Attendues<br>
  • Pipeline d’Ingestion et d’Indexation : Extraction, segmentation, génération d’embeddings (Ollama) et
indexation dans ChromaDB.<br>
  • Moteur d’Interrogation Avancé : Expansion de requête, calcul et fusion des scores pour un classement
hybride.<br>
  • Interface de Recherche Web : Développement d’une application Streamlit pour la recherche et le
filtrage.<br>
  • Synthèse à la Volée : Générer un résumé synthétique des N meilleurs résultats avec Gemma.<br>
  • Analyse de Tendances : Visualiser l’évolution temporelle de mots-clés dans le corpus.<br>
  • Visualisation du Réseau d’Auteurs : Construire et afficher un graphe de co-auteurs.
