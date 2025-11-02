# Quick Start - Installation en 3 Étapes

## ⚡ Installation Rapide

Vous avez le choix entre **deux méthodes d'installation** :

---

## Option A : Installation avec rye (Recommandée)

**Avantages** : Gestion moderne des dépendances, isolement parfait, reproductibilité

### Étape 1 : Installer rye

```bash
# Installation
curl -sSf https://rye-up.com/get | bash

# Configurer le PATH
echo 'source "$HOME/.rye/env"' >> ~/.zshrc
source ~/.zshrc
```

### Étape 2 : Installer le framework

```bash
cd /Users/cdagorn/Projets_Python/rag
./install.sh
```

### Étape 3 : Configurer et démarrer

```bash
# Configurer les clés API
cp .env.example .env
nano .env  # Ajoutez vos clés API

# Démarrer le pipeline
./start.sh
```

---

## Option B : Installation avec pip (Alternative)

**Avantages** : Plus familier, pas besoin d'installer rye

### Étape 1 : Créer un environnement virtuel

```bash
cd /Users/cdagorn/Projets_Python/rag

# Créer le venv
python3 -m venv .venv

# Activer
source .venv/bin/activate
```

### Étape 2 : Installer le framework

```bash
# Installation automatique
./install_with_pip.sh

# OU installation manuelle
pip install -e .
mkdir -p data/input/docs data/output logs chroma_db
```

### Étape 3 : Configurer et démarrer

```bash
# Configurer les clés API
cp .env.example .env
nano .env  # Ajoutez vos clés API

# Activer l'environnement
source .venv/bin/activate

# Démarrer le pipeline
./start.sh
```

---

## 🔧 Vérification Rapide

```bash
# Test d'import (avec rye)
rye run python -c "import rag_framework; print('✅ OK')"

# Test d'import (avec pip/venv)
source .venv/bin/activate
python -c "import rag_framework; print('✅ OK')"
```

---

## 📝 Configuration Minimale

Créez un fichier `.env` avec vos clés API :

```bash
OPENAI_API_KEY=sk-...
```

Ajustez `config/08_vector_storage.yaml` si besoin :

```yaml
provider: "chromadb"  # Options: chromadb, qdrant, pgvector, milvus, weaviate
```

---

## 🚀 Premier Test

```bash
# 1. Ajoutez un document PDF dans data/input/docs/
cp votre_document.pdf data/input/docs/

# 2. Démarrez le pipeline
./start.sh

# 3. Vérifiez les logs
tail -f logs/audit_trail.jsonl
```

---

## ❓ Dépannage Express

### Erreur : "rye: command not found"

```bash
source "$HOME/.rye/env"
```

### Erreur : "No module named 'rag_framework'"

**Avec rye** :
```bash
rye sync
```

**Avec pip** :
```bash
source .venv/bin/activate
pip install -e .
```

### Erreur : "Connection refused" (base vectorielle)

Si vous utilisez Qdrant/Milvus/Weaviate, démarrez le service Docker :

```bash
# Exemple avec Qdrant
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
```

---

## 📚 Documentation Complète

- **Installation détaillée** : [INSTALLATION.md](INSTALLATION.md)
- **Bases vectorielles** : [/tmp/VECTOR_STORES_INSTALL.md](/tmp/VECTOR_STORES_INSTALL.md)
- **Configuration** : [README.md](README.md)
- **Qualité** : [GEMINI.md](GEMINI.md)

---

## 🎯 Récapitulatif

| Méthode | Commande Installation | Commande Démarrage |
|---------|----------------------|-------------------|
| **rye** (recommandé) | `./install.sh` | `./start.sh` |
| **pip** (alternatif) | `./install_with_pip.sh` | `source .venv/bin/activate && ./start.sh` |

**Choisissez la méthode qui vous convient le mieux !**
