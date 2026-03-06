# Architecture

## Vue d'ensemble

Le projet suit un pipeline simple et lisible:

1. ingestion multi-fichiers
2. consolidation pandas
3. nettoyage et normalisation
4. calcul des KPI
5. generation de visualisations
6. export CSV / PDF

Deux points d'entree sont disponibles:

- `main.py`: execution batch / CLI
- `dashboard/app.py`: execution interactive via Streamlit

## Modules

### `main.py`

Point d'entree CLI.

Responsabilites:

- lire les arguments
- lancer le pipeline de bout en bout
- ecrire les fichiers de sortie

### `dashboard/app.py`

Interface Streamlit.

Responsabilites:

- gerer les uploads
- piloter les themes
- declencher la fusion
- afficher les KPI et les graphiques
- proposer les exports

### `scripts/ingestion.py`

Responsable de l'entree des fichiers.

Responsabilites:

- convertir des fichiers uploades en objets `SourceFile`
- charger des fichiers depuis un dossier
- lire les formats `CSV`, `XLSX`, `XLS`
- inferer la `region` depuis le nom du fichier
- fusionner plusieurs sources

### `scripts/cleaning.py`

Noyau de normalisation metier.

Responsabilites:

- standardiser les noms de colonnes
- detecter les colonnes metier utiles
- nettoyer les montants, dates et champs texte
- ajouter des valeurs par defaut quand necessaire

Le module tient compte:

- des alias de colonnes
- de mots-cles
- du contenu des colonnes

Cela permet de traiter des entrees heterogenes sans exiger une nomenclature stricte.

### `scripts/aggregation.py`

Responsable des KPI globaux et des agregations simples.

Responsabilites:

- calculer les KPI principaux
- agregater par region
- agregater par flux
- formater les montants

### `scripts/charts.py`

Responsable de la couche Plotly generique.

Responsabilites:

- lister les types de graphiques disponibles
- construire les figures numeriques et de repartition
- appliquer la palette active
- centraliser le style visuel des graphiques

### `scripts/dashboard_profiles.py`

Responsable des dashboards metier.

Responsabilites:

- preparer un jeu de donnees commun
- construire les KPI et graphiques pour chaque profil
- encapsuler le resultat dans `DashboardBundle`

Ce module concentre la logique de restitution.

### `scripts/reporting.py`

Responsable du PDF.

Responsabilites:

- generer le rapport de synthese
- formater les tableaux
- fournir un helper `generate_pdf_report_now` pour les points d'entree

### `scripts/types.py`

Responsable des types partages.

Responsabilites:

- `SourceFile`
- `UploadedFileLike`
- `ColumnMapping`
- `KpiMetrics`

## Flux de traitement

### 1. Ingestion

Les sources entrent soit:

- depuis la sidebar Streamlit
- depuis `data/inputs` en mode CLI

Chaque fichier est charge en memoire sous forme de `SourceFile`.

### 2. Consolidation

`consolidate_files` concatene toutes les sources valides dans un `DataFrame` unique.

Les erreurs non bloquantes sont collectees dans une liste de warnings.

### 3. Nettoyage

`clean_dataframe`:

- normalise les noms de colonnes
- resout les colonnes metier
- convertit les montants en `float`
- convertit les dates au format `YYYY-MM-DD`
- remplit les valeurs manquantes
- supprime les doublons

### 4. KPI et agregations

`compute_kpis`, `aggregate_by_region` et `aggregate_by_flow` fournissent:

- montant total des engagements
- nombre de PME
- nombre de transactions
- nombre de regions
- repartitions regionales et par flux

### 5. Dashboards

`build_dashboard_bundle` construit:

- un titre
- une description
- des cartes KPI
- un ensemble de figures Plotly

Le dashboard est choisi par l'utilisateur dans la sidebar.

### 6. Exports

Le projet peut exporter:

- CSV consolide
- PDF de synthese

## Choix techniques

## Pandas comme colonne vertebrale

Pandas a ete retenu pour:

- la consolidation multi-sources
- le nettoyage tabulaire
- les agregations rapides
- la compatibilite CSV / Excel

## Streamlit pour la demonstration rapide

Streamlit a ete retenu pour:

- la rapidite de prototypage
- la lisibilite du code
- la restitution immediate des KPI
- l'integration simple avec Plotly

## Plotly pour les visualisations

Plotly a ete retenu pour:

- l'interactivite native
- les graphiques financiers classiques
- la souplesse de theming

## Pyright et pylint stricts

Le projet est maintenu avec:

- `pyright` en configuration stricte
- `pylint` strict

Note:

- `pyright` est a 0 erreur
- certaines warnings restent normales sur des APIs dynamiques comme `pandas`, `plotly` ou `streamlit`
- `scripts/dashboard_profiles.py` contient un assouplissement local sur quelques categories de warnings pyright pour rester pragmatique sur du code pandas fortement dynamique

## Themes

La thematisation repose sur deux niveaux:

- theme Streamlit global via `themes/*.toml`
- palette Plotly via `scripts/charts.py`

L'utilisateur peut:

- choisir un theme visuel
- choisir une palette de graphiques synchronisee ou distincte

## Extension du projet

Les points d'extension naturels sont:

- ajout d'un nouveau dashboard dans `scripts/dashboard_profiles.py`
- ajout d'un nouveau type de graphique dans `scripts/charts.py`
- ajout de nouveaux alias de colonnes dans `scripts/cleaning.py`
- ajout d'un export supplementaire dans `scripts/reporting.py`

## Bonnes pratiques pour contribuer

- conserver un typage explicite
- eviter les effets de bord hors des points d'entree
- centraliser les transformations de donnees dans `scripts/`
- garder `dashboard/app.py` focalise sur l'interface
- revalider avec `compileall`, `pylint` et `pyright`
