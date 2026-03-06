# Consolidation Financiere Automatisee

Application Python de consolidation, nettoyage et visualisation de donnees financieres.

Le projet permet d'importer plusieurs fichiers CSV ou Excel, de les fusionner dans un pipeline unique, de nettoyer automatiquement les donnees, de produire un dashboard Streamlit multi-profils et d'exporter un rapport PDF de synthese.

## Objectif

Demonstrer un savoir-faire moderne sur un cas d'automatisation financiere:

- ingestion multi-sources
- normalisation de donnees heterogenes
- inference de colonnes sans imposer des noms exacts
- restitution executive via dashboard interactif
- generation de livrables exploitables (CSV + PDF)

## Fonctionnalites

- Import simultane de plusieurs fichiers `CSV`, `XLSX` ou `XLS`
- Consolidation de toutes les sources dans un seul `DataFrame`
- Nettoyage automatique:
  - suppression des doublons
  - gestion des valeurs manquantes
  - normalisation des dates
  - ajout de la colonne `region` a partir du nom de fichier
- Inference automatique des colonnes metier:
  - montant
  - date
  - flux
  - PME / contrepartie
- Dashboard Streamlit avec sidebar de controle
- Export PDF via `fpdf2`
- Export CSV des donnees consolidees
- Themes visuels:
  - Finance Pro
  - Dark Mode
  - Executive Mode
- Palette de graphiques dissociable du theme visuel

## Dashboards disponibles

1. Dashboard de Performance Financiere
2. Dashboard de Tresorerie
3. Dashboard Budget vs Reel
4. Dashboard de Risque Financier
5. Dashboard de Portefeuille d'Investissement
6. Dashboard Comptable
7. Dashboard de Rentabilite Produits / Services
8. Dashboard de KPI Financiers
9. Dashboard de Prevision Financiere
10. Dashboard Fraude & Conformite
11. Dashboard Trading
12. Dashboard de Performance Bancaire

## Types de graphiques

Graphiques numeriques:

- Barres
- Barres horizontales
- Ligne
- Aire
- Waterfall
- Scatter
- Histogramme

Graphiques de repartition:

- Camembert
- Donut
- Treemap
- Sunburst
- Funnel
- Barres

## Structure du projet

```text
.
|-- .streamlit/
|-- dashboard/
|   `-- app.py
|-- data/
|   |-- inputs/
|   `-- outputs/
|-- docs/
|   `-- ARCHITECTURE.md
|-- scripts/
|   |-- aggregation.py
|   |-- charts.py
|   |-- cleaning.py
|   |-- dashboard_profiles.py
|   |-- ingestion.py
|   |-- reporting.py
|   `-- types.py
|-- themes/
|-- main.py
|-- requirements.txt
|-- pyrightconfig.json
`-- .pylintrc
```

## Prerequis

- Python `3.11+`
- PowerShell sous Windows ou un shell compatible

## Installation

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

## Lancement du dashboard

```powershell
streamlit run dashboard/app.py
```

## Lancement du pipeline CLI

```powershell
python main.py --input-dir data/inputs --output-dir data/outputs
```

Exemple:

```powershell
python main.py --input-dir data/inputs --output-dir data/outputs
```

## Contrat d'entree

Les fichiers peuvent utiliser des noms de colonnes differents. Le systeme tente de reconnaitre automatiquement les concepts metier a partir:

- du nom de la colonne
- de son contenu
- du type de valeurs detectees

Exemples de variantes reconnues:

- montant: `montant`, `engagement`, `amount`, `volume financier`, `value`
- date: `date`, `date valeur`, `periode`, `timestamp`
- flux: `flux`, `sens operation`, `type operation`, `flow`
- PME: `pme`, `contrepartie`, `beneficiaire`, `client`, `entreprise`

La `region` est inferee depuis le nom du fichier source.

Exemple:

- `engagements_nord.csv` -> `Nord`
- `operations_sud.xlsx` -> `Sud`

## Sorties generees

Mode dashboard:

- visualisation interactive
- telechargement PDF
- telechargement CSV

Mode CLI:

- `consolidated_data.csv`
- `summary_by_region.csv`
- `summary_by_flow.csv`
- `report_summary.pdf`

## Themes et design

Le projet implemente trois themes:

- Finance Pro: bleu / vert / blanc
- Dark Mode: fond sombre, accent bleu electrique
- Executive Mode: minimaliste, neutre et directeur

Les fichiers de theme Streamlit sont stockes dans `themes/`.

## Qualite de code

Verification statique:

```powershell
.\.venv\Scripts\python.exe -m pyright
.\.venv\Scripts\python.exe -m pylint main.py dashboard scripts switch_theme.py
.\.venv\Scripts\python.exe -m compileall main.py dashboard scripts switch_theme.py
```

Etat actuel du projet:

- `pyright`: 0 erreur
- `pylint`: 10.00/10
- test de fumee pipeline: OK

## Documentation technique

Voir `docs/ARCHITECTURE.md` pour:

- l'architecture interne
- le flux de traitement
- la responsabilite de chaque module
- les choix de typage et de qualite
- les points d'extension

## Cas d'usage cible

Le projet est adapte a:

- direction financiere
- controle de gestion
- reporting bancaire
- consolidation de suivis regionaux
- demonstration de competences d'automatisation et de developpement d'outils
