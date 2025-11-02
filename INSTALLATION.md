# Guide d'Installation - Framework RAG

## 📋 Prérequis

- **Python 3.9+** (Python 3.12 recommandé)
- **macOS**, Linux ou Windows (WSL)

## 🚀 Installation Rapide (Recommandée)

### Option 1 : Installation avec rye (Recommandé)

**Étape 1 : Installer rye**

```bash
# Sur macOS/Linux
curl -sSf https://rye-up.com/get | bash

# Ajouter rye au PATH
source "$HOME/.rye/env"

# Vérifier l'installation
rye --version
```

**Étape 2 : Ajouter rye au shell de façon permanente**

Ajoutez cette ligne à votre `~/.zshrc` (ou `~/.bashrc` si vous utilisez bash) :

```bash
source "$HOME/.rye/env"
```

Puis rechargez :

```bash
source ~/.zshrc  # ou source ~/.bashrc
```

**Étape 3 : Installer le framework**

```bash
cd /Users/cdagorn/Projets_Python/rag
./install.sh
```

### Option 2 : Installation avec pip (Alternative)

Si vous préférez utiliser pip directement :

```bash
cd /Users/cdagorn/Projets_Python/rag

# Créer un environnement virtuel
python3 -m venv .venv

# Activer l'environnement
source .venv/bin/activate

# Installer le framework
pip install -e .

# Créer les répertoires nécessaires
./install_with_pip.sh
```

## 🔧 Installation Manuelle Pas à Pas

Si les scripts automatiques échouent, suivez ces étapes :

### 1. Installer rye

```bash
# Installation
curl -sSf https://rye-up.com/get | bash

# Configuration du PATH
echo 'source "$HOME/.rye/env"' >> ~/.zshrc
source ~/.zshrc

# Vérification
rye --version
```

### 2. Cloner et configurer le projet

```bash
cd /Users/cdagorn/Projets_Python/rag

# Synchroniser les dépendances
rye sync

# Créer les répertoires
mkdir -p data/input/{compliance_docs,audit_reports,docs}
mkdir -p data/output/{extracted,chunks,embeddings}
mkdir -p logs
mkdir -p chroma_db
```

### 3. Configurer les variables d'environnement

```bash
# Copier le template
cp .env.example .env

# Éditer avec vos clés API
nano .env
```

Ajoutez vos clés API :

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Vérifier l'installation

```bash
# Vérifier que le package est importable
rye run python -c "import rag_framework; print('✅ OK')"

# Vérifier les librairies installées
rye run python /tmp/test_all_imports.py
```

## 🗄️ Installation des Bases Vectorielles Optionnelles

Par défaut, seul **ChromaDB** est installé. Pour utiliser d'autres bases vectorielles :

### Qdrant

```bash
rye sync --features qdrant
```

### pgvector (PostgreSQL)

```bash
rye sync --features pgvector
```

**Note** : Nécessite PostgreSQL avec l'extension pgvector.

### Milvus

```bash
rye sync --features milvus
```

### Weaviate

```bash
rye sync --features weaviate
```

### Toutes les bases vectorielles

```bash
rye sync --features qdrant --features pgvector --features milvus --features weaviate
```

## 🐳 Démarrage des Services Docker (Optionnel)

Si vous utilisez une base vectorielle externe :

### Qdrant

```bash
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
```

### PostgreSQL avec pgvector

```bash
docker run -d \
  --name pgvector \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  ankane/pgvector
```

### Milvus

```bash
docker run -d \
  --name milvus-standalone \
  -p 19530:19530 \
  -p 9091:9091 \
  milvusdb/milvus:latest \
  milvus run standalone
```

### Weaviate

```bash
docker run -d \
  --name weaviate \
  -p 8080:8080 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH=/var/lib/weaviate \
  semitechnologies/weaviate:latest
```

## ✅ Vérification de l'Installation

### Test complet

```bash
# Test des imports
rye run python -c "import rag_framework; import chromadb; import langchain; print('✅ Installation OK')"

# Test du pipeline (nécessite des documents)
./start.sh
```

### Test des bases vectorielles

```bash
# ChromaDB (toujours disponible)
rye run python -c "import chromadb; print('✅ ChromaDB OK')"

# Qdrant (si installé)
rye run python -c "import qdrant_client; print('✅ Qdrant OK')"

# pgvector (si installé)
rye run python -c "import psycopg2; print('✅ pgvector OK')"

# Milvus (si installé)
rye run python -c "import pymilvus; print('✅ Milvus OK')"

# Weaviate (si installé)
rye run python -c "import weaviate; print('✅ Weaviate OK')"
```

## 🆘 Dépannage

### Erreur "rye: command not found"

Le PATH n'est pas configuré. Exécutez :

```bash
source "$HOME/.rye/env"
```

Puis ajoutez à votre shell :

```bash
echo 'source "$HOME/.rye/env"' >> ~/.zshrc
```

### Erreur "Python version incompatible"

Vérifiez votre version de Python :

```bash
python3 --version  # Doit être >= 3.9
```

Si nécessaire, installez Python 3.12 :

```bash
# macOS avec Homebrew
brew install python@3.12

# macOS avec pyenv
pyenv install 3.12.2
pyenv global 3.12.2
```

### Erreur "ImportError: No module named 'marker_pdf'"

Les dépendances ne sont pas installées. Exécutez :

```bash
rye sync
```

### Erreur "Connection refused" avec les bases vectorielles

Le service Docker n'est pas démarré. Vérifiez :

```bash
# Lister les containers Docker
docker ps

# Démarrer le service (exemple avec Qdrant)
docker start qdrant
```

### Erreur de compilation psycopg2

Le package `psycopg2-binary` devrait éviter ce problème, mais si l'erreur persiste :

```bash
# macOS
brew install postgresql

# Linux
sudo apt-get install libpq-dev
```

## 📊 Structure après Installation

```
/Users/cdagorn/Projets_Python/rag/
├── .venv/                    # Environnement virtuel (créé par rye)
├── config/                   # Fichiers de configuration YAML
│   ├── global.yaml
│   ├── 01_monitoring.yaml
│   ├── 02_preprocessing.yaml
│   ├── ...
│   └── 08_vector_storage.yaml
├── data/
│   ├── input/               # Documents à traiter
│   │   ├── compliance_docs/
│   │   ├── audit_reports/
│   │   └── docs/
│   └── output/              # Résultats du pipeline
│       ├── extracted/
│       ├── chunks/
│       └── embeddings/
├── logs/                    # Logs du pipeline
├── chroma_db/              # Base ChromaDB (si utilisée)
├── rag_framework/          # Code source du framework
├── .env                    # Variables d'environnement (à créer)
├── install.sh              # Script d'installation
└── start.sh                # Démarrage du pipeline
```

## 📝 Prochaines Étapes

Après installation réussie :

1. **Configurer les clés API** : Éditer `.env`
2. **Ajuster la configuration** : Éditer `config/global.yaml` et `config/08_vector_storage.yaml`
3. **Ajouter des documents** : Copier vos PDF/Office dans `data/input/docs/`
4. **Démarrer le pipeline** : `./start.sh`

## 🔗 Ressources

- [Documentation rye](https://rye-up.com/)
- [Guide des bases vectorielles](/tmp/VECTOR_STORES_INSTALL.md)
- [Guide de configuration](README.md)
- [Charte qualité GEMINI](GEMINI.md)
