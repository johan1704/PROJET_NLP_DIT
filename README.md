# PROJET_NLP_DIT

<h3>Objectif Mettre en œuvre un moteur de recherche local pour un corpus d’articles scientifiques (arXiv),
doté de capacités d’interrogation sémantique, de filtrage et de synthèse</h3><br>

<b>Concepts Clés</b>

– Base de Données Vectorielle (ChromaDB) : Stockage et recherche de vecteurs générés avec Ollama
Embeddings.<br>
– Recherche Hybride : Fusion des scores de pertinence sémantique (vecteurs) et lexicale (e.g., BM25).<br>
– Query Expansion : Utilisation de Gemma (via Ollama) pour reformuler la requête initiale.<br>
– Recherche à Facettes : Filtrage des résultats basé sur des métadonnées structurées.<br>
<h6>Fonctionnalités Attendues</h6><br>
  • Pipeline d’Ingestion et d’Indexation : Extraction, segmentation, génération d’embeddings (Ollama) et
indexation dans ChromaDB.<br>
  • Moteur d’Interrogation Avancé : Expansion de requête, calcul et fusion des scores pour un classement
hybride.<br>
  • Interface de Recherche Web : Développement d’une application Streamlit pour la recherche et le
filtrage.<br>
  • Synthèse à la Volée : Générer un résumé synthétique des N meilleurs résultats avec Gemma.<br>
  • Analyse de Tendances : Visualiser l’évolution temporelle de mots-clés dans le corpus.<br>
  • Visualisation du Réseau d’Auteurs : Construire et afficher un graphe de co-auteurs.


DETAILS <br>

1-ChromaDB (Base vectorielle)

On stocke non pas les mots, mais des vecteurs qui représentent le sens du texte.

Ces vecteurs sont générés grâce à Ollama qui produit des embeddings (représentations numériques du texte).

2-Recherche Hybride

On combine deux méthodes :

Recherche sémantique (trouver les textes qui veulent dire la même chose que ta requête).

Recherche lexicale (BM25 : trouver les textes contenant les mêmes mots).

Les scores des deux méthodes sont fusionnés pour un meilleur classement.

3-Expansion de requête (Query Expansion)

Si ta requête est trop courte ou imprécise, Gemma (via Ollama) la reformule ou l’enrichit pour trouver plus de résultats pertinents.

4-Recherche à facettes

Permet de filtrer les résultats par métadonnées (ex : auteur, date, domaine).

5-Pipeline d’ingestion

On prend les documents, on les découpe en morceaux (segmentation), on crée les vecteurs (embeddings) et on les stocke dans ChromaDB.

6-Interface web (Streamlit)

L’utilisateur tape sa requête, voit les résultats, filtre par facettes, et consulte des résumés automatiques générés par Gemma.

7-Analyse et visualisations

Tendances : voir comment certains mots-clés apparaissent/disparaissent dans le temps.

Graphe de co-auteurs : voir quels auteurs collaborent ensemble dans le corpus.

