# RAG Framework - Audit & Conformité

Framework RAG (Retrieval-Augmented Generation) modulaire et configurable pour l'analyse de documents d'audit et de conformité réglementaire.

## Caractéristiques

- **Architecture modulaire** : 8 étapes configurables indépendamment
- **Pilotage par configuration** : Fichiers YAML pour chaque étape
- **Conformité intégrée** : Audit logging, traçabilité, métadonnées réglementaires
- **Qualité code** : PEP 8, typage statique (mypy), tests automatisés (pytest)
- **Standards ouverts** : ChromaDB, LangChain, OpenAI, Sentence Transformers

## Architecture

Le framework est composé de 8 étapes séquentielles :

1. **Monitoring** : Surveillance de fichiers sources (Watchdog)
2. **Preprocessing** : Extraction et nettoyage de documents (marker-pdf)
3. **Chunking** : Découpage sémantique ou récursif
4. **Enrichment** : Métadonnées de conformité (RGPD, ISO27001, SOC2)
5. **Audit** : Logging immuable et traçabilité (SHA-256, timestamps)
6. **Embedding** : Génération de vecteurs (OpenAI, Sentence Transformers, Ollama)
7. **Normalization** : Normalisation L2 et validation
8. **Vector Storage** : Stockage vectoriel (ChromaDB, Qdrant)

## Installation

### Prérequis

- Python ≥ 3.12
- [uv](https://github.com/astral-sh/uv) (gestionnaire de packages)

### Installation rapide

```bash
# 1. Installer uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Cloner le projet
git clone <votre-repo>
cd rag

# 3. Installer les dépendances
uv sync

# 4. Installer les dépendances de développement
uv sync --dev

# 5. Configurer pre-commit
uv run pre-commit install
```

## Configuration

### Variables d'environnement

Créer un fichier `.env` à la racine du projet :

```env
# OpenAI API
OPENAI_API_KEY=sk-...

# Ollama (optionnel)
OLLAMA_HOST=http://localhost:11434
```

### Fichiers de configuration

Tous les fichiers de configuration sont dans le dossier `config/` :

- `global.yaml` : Configuration globale (VLM, logging, compliance)
- `01_monitoring.yaml` : Surveillance de fichiers
- `02_preprocessing.yaml` : Extraction PDF
- `03_chunking.yaml` : Stratégie de découpage
- `04_enrichment.yaml` : Métadonnées de conformité
- `05_audit.yaml` : Audit logging
- `06_embedding.yaml` : Génération d'embeddings
- `07_normalization.yaml` : Normalisation
- `08_vector_storage.yaml` : Stockage vectoriel

## Utilisation

### CLI

```bash
# Afficher le statut du pipeline
uv run rag-pipeline --status

# Exécuter le pipeline complet
uv run rag-pipeline

# Spécifier un répertoire de configuration
uv run rag-pipeline --config-dir ./config

# Mode debug
uv run rag-pipeline --log-level DEBUG
```

### API Python

```python
from rag_framework import RAGPipeline

# Initialiser le pipeline
pipeline = RAGPipeline(config_dir="config")

# Exécuter le pipeline
result = pipeline.execute({
    "file_paths": ["data/input/compliance_docs/doc1.pdf"]
})

# Accéder aux résultats
chunks = result["normalized_chunks"]
print(f"Chunks créés: {len(chunks)}")

# Exécuter une étape spécifique
data = {"monitored_files": ["doc.pdf"]}
result = pipeline.execute_step("PreprocessingStep", data)
```

## Git Auto-Sync

Le framework inclut un système de synchronisation Git automatique qui surveille les modifications de fichiers et effectue des push GitHub automatiques.

### Configuration

La configuration se trouve dans `config/global.yaml` section `git_sync` :

```yaml
git_sync:
  enabled: true
  mode: "sync"  # Mode synchrone
  frequency:
    type: "debounce"  # immediate | debounce | periodic
    debounce_seconds: 30
  watch_paths:
    - "."
  include_patterns:
    - ".*\\.py$"
    - ".*\\.yaml$"
    - ".*\\.md$"
  repository:
    branch: "main"
    remote: "origin"
```

### Token GitHub

Créer un Personal Access Token GitHub :

1. Aller sur https://github.com/settings/tokens
2. Cliquer "Generate new token (classic)"
3. Permissions requises : `repo` (full control)
4. Copier le token et l'ajouter dans `.env` :

```env
GITHUB_TOKEN=ghp_votre_token_ici
```

**IMPORTANT** : Ne JAMAIS commiter le fichier `.env` contenant votre token !

### Lancement

```bash
# Démarrer la synchronisation automatique
rye run python -m rag_framework.cli.git_sync_cli

# Ou avec uv
uv run python -m rag_framework.cli.git_sync_cli
```

### Fonctionnement

1. **Surveillance** : Watchdog surveille les modifications de fichiers
2. **Filtrage** : Seuls les fichiers correspondant aux patterns sont pris en compte
3. **Debounce** : Attend 30s d'inactivité pour regrouper les modifications
4. **Commit & Push** : Crée un commit et push vers GitHub automatiquement

### Arrêt propre

Appuyer sur `CTRL+C` pour arrêter proprement. Les fichiers en attente seront synchronisés avant l'arrêt.

### Exclusions

Les fichiers suivants ne déclenchent **PAS** de synchronisation :
- Dossier `.git/`, `.venv/`, `__pycache__/`
- Contenu de `data/input/*` et `data/output/*` (sauf `.gitkeep`)
- Fichiers de cache (`.pytest_cache`, `.mypy_cache`, `.ruff_cache`)
- Logs (`*.log`, `logs/`)
- Bases de données (`chroma_db/`)

L'arborescence des dossiers `data/input/` et `data/output/` est préservée grâce aux fichiers `.gitkeep`.

## Développement

### Stack qualité (conforme GEMINI)

- **Formatting** : `ruff format`
- **Linting** : `ruff check`
- **Type checking** : `mypy`
- **Tests** : `pytest` + `pytest-cov` + `hypothesis`
- **Pre-commit** : Validation automatique avant commit

### Commandes de développement

```bash
# Formater le code
uv run ruff format .

# Linter le code
uv run ruff check .

# Vérifier le typage
uv run mypy rag_framework

# Lancer les tests
uv run pytest

# Tests avec couverture
uv run pytest --cov=rag_framework --cov-report=html

# Tests d'intégration uniquement
uv run pytest -m integration

# Pre-commit sur tous les fichiers
uv run pre-commit run --all-files
```

## Tests

### Structure des tests

```
tests/
├── unit/                  # Tests unitaires
│   ├── test_config.py
│   ├── test_pipeline.py
│   └── test_steps/
├── integration/           # Tests d'intégration
│   └── test_rag_evaluation.py
└── data/                  # Données de test
```

### Exécution

```bash
# Tous les tests
uv run pytest

# Tests unitaires uniquement
uv run pytest tests/unit

# Test spécifique
uv run pytest tests/unit/test_config.py::TestLoadConfig

# Mode verbeux
uv run pytest -v

# Avec couverture
uv run pytest --cov=rag_framework --cov-report=term-missing
```

## Conformité et Audit

### Métadonnées de conformité

Chaque chunk est enrichi avec :

- **Hash SHA-256** : Empreinte immuable du contenu
- **Timestamp ISO8601** : Date de traitement
- **Classification** : Sensibilité (public, interne, confidentiel, secret)
- **Type de document** : Contrat, rapport d'audit, politique, procédure
- **Tags réglementaires** : RGPD, ISO27001, SOC2, HIPAA

### Audit Trail

Tous les traitements sont enregistrés dans `logs/audit_trail.jsonl` (format JSONL) avec :

- Timestamp immuable
- Documents traités
- Opérations effectuées
- Durée d'exécution
- Métadonnées complètes

## Exemples d'utilisation

### Traiter des documents de conformité RGPD

```python
from rag_framework import RAGPipeline

pipeline = RAGPipeline()

result = pipeline.execute({
    "file_paths": [
        "data/input/compliance_docs/politique_rgpd.pdf",
        "data/input/compliance_docs/procedure_donnees.pdf"
    ]
})

# Filtrer les chunks avec tags RGPD
rgpd_chunks = [
    chunk for chunk in result["normalized_chunks"]
    if "RGPD" in chunk["metadata"]["regulatory_tags"]
]

print(f"Chunks RGPD: {len(rgpd_chunks)}")
```

### Recherche sémantique (après stockage)

```python
# TODO: Implémenter après ajout retriever
# from rag_framework import RAGRetriever
#
# retriever = RAGRetriever()
# results = retriever.search(
#     query="Quelle est la politique de conservation des données ?",
#     k=5,
#     filters={"regulatory_tags": ["RGPD"]}
# )
```

## Roadmap

### V1.0 (MVP actuel)

- [x] Architecture modulaire 8 étapes
- [x] Configuration YAML
- [x] Audit logging et traçabilité
- [x] Métadonnées de conformité
- [x] Tests unitaires et d'intégration
- [x] CI/CD GitHub Actions

### V2.0 (Améliorations)

- [ ] Implémentation réelle des embeddings (OpenAI, Sentence Transformers)
- [ ] Implémentation ChromaDB et Qdrant
- [ ] Retriever avec filtres métadonnées
- [ ] Évaluation Ragas (faithfulness, relevancy)
- [ ] Chunking sémantique avec embeddings
- [ ] OCR Tesseract pour PDF scannés
- [ ] API REST FastAPI
- [ ] Interface web Streamlit
- [ ] Support multi-langues (i18n)

## Contribution

### Standards de code

Ce projet respecte la charte GEMINI :

1. **Clarté** : Code auto-documenté, docstrings Google style
2. **Fiabilité** : Typage strict (mypy), tests exhaustifs
3. **Efficacité** : Workflow automatisé (uv, pre-commit)
4. **Cohérence** : Configuration centralisée (pyproject.toml)

### Workflow

1. Fork du projet
2. Créer une branche (`git checkout -b feature/amazing-feature`)
3. Commit avec pre-commit activé
4. Push vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

## Licence

MIT License - Voir [LICENSE](LICENSE) pour les détails.

## Support

Pour toute question ou problème :

- Issues GitHub : [votre-repo/issues]
- Documentation : [docs/api/]

## Références

- [Charte GEMINI](GEMINI.md) : Gouvernance technique Python
- [LangChain](https://python.langchain.com/)
- [ChromaDB](https://www.trychroma.com/)
- [Ragas](https://docs.ragas.io/)
- [uv](https://github.com/astral-sh/uv)
