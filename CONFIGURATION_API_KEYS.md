# Configuration des Clés API

## Vue d'ensemble

Le pipeline supporte plusieurs providers LLM/VLM. Par défaut, **toutes les clés API sont désactivées** avec des valeurs factices.

Vous n'avez besoin de configurer **que les providers que vous utilisez réellement**.

## Providers disponibles

| Provider | Gratuit | Local | Cloud | Usage |
|---|---|---|---|---|
| **Ollama** | ✅ | ✅ | ❌ | Recommandé pour débuter (gratuit, local) |
| **LM Studio** | ✅ | ✅ | ❌ | Alternative locale avec interface graphique |
| **vLLM** | ✅ | ✅ | ❌ | Production haute performance (local) |
| OpenAI | ❌ | ❌ | ✅ | Meilleure qualité mais payant |
| Anthropic | ❌ | ❌ | ✅ | Claude 3 (excellent pour extraction) |
| Mistral AI | ❌ | ❌ | ✅ | Provider français, bon rapport qualité/prix |
| Hugging Face | ❌ | ❌ | ✅ | Accès à des milliers de modèles |

## Configuration rapide (providers locaux gratuits)

### Option 1 : Ollama (recommandé)

**Installation** :
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Démarrer Ollama
ollama serve
```

**Télécharger un modèle** :
```bash
# Modèle LLM pour enrichissement (optionnel)
ollama pull mistral:7b

# Modèle VLM pour extraction d'images (optionnel)
ollama pull llava:13b
```

**Configuration** : Aucune clé API requise ! C'est déjà configuré dans `config/global.yaml` :
```yaml
ollama:
  access_method: "openai_compatible"
  base_url: "http://127.0.0.1:11434/v1"
  api_key: "ollama"  # Clé factice (non vérifiée)
```

### Option 2 : LM Studio

1. Télécharger depuis https://lmstudio.ai/
2. Installer et démarrer LM Studio
3. Télécharger un modèle depuis l'interface
4. Démarrer le serveur local (onglet "Local Server")

**Configuration** : Déjà prête dans `config/global.yaml`

### Option 3 : vLLM

Pour production haute performance :
```bash
# Installation
pip install vllm

# Démarrer avec un modèle
vllm serve mistralai/Mistral-7B-v0.1 --port 8000
```

## Configuration des providers cloud (payants)

Si vous voulez utiliser OpenAI, Anthropic, etc., vous devez configurer les clés API.

### Méthode 1 : Fichier .env (recommandé)

Créer/modifier le fichier `.env` à la racine du projet :

```bash
# OpenAI
OPENAI_API_KEY=sk-proj-xxx...

# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-xxx...

# Mistral AI
MISTRAL_AI_API_KEY=xxx...

# Hugging Face
HUGGINGFACE_API_KEY=hf_xxx...
```

**Puis modifier** `config/global.yaml` pour utiliser les variables d'environnement :

```yaml
llm_providers:
  openai:
    api_key: "${OPENAI_API_KEY}"  # Charge depuis .env

  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"  # Charge depuis .env
```

### Méthode 2 : Directement dans global.yaml (moins sécurisé)

**⚠️ ATTENTION** : Ne jamais commiter ce fichier dans git avec de vraies clés !

```yaml
llm_providers:
  openai:
    api_key: "sk-proj-votre-vraie-cle-ici"
```

## Obtenir les clés API

### OpenAI
1. Aller sur https://platform.openai.com/
2. Créer un compte
3. Onglet "API keys" → "Create new secret key"
4. Copier la clé (commence par `sk-proj-`)

### Anthropic (Claude)
1. Aller sur https://console.anthropic.com/
2. Créer un compte
3. "API Keys" → "Create Key"
4. Copier la clé (commence par `sk-ant-`)

### Mistral AI
1. Aller sur https://console.mistral.ai/
2. Créer un compte
3. "API Keys" → "Create API Key"
4. Copier la clé

### Hugging Face
1. Aller sur https://huggingface.co/settings/tokens
2. Créer un compte
3. "Access Tokens" → "New token"
4. Copier le token (commence par `hf_`)

## Vérifier la configuration

```bash
# Tester avec dry-run
./start.sh --dry-run

# Vérifier les logs
cat logs/rag_audit.log
```

## Configuration par défaut (sans clés)

**Le pipeline fonctionne sans aucune clé API** tant que vous n'utilisez pas les fonctionnalités suivantes :

- ✅ **Extraction de texte** (PDF, DOCX, etc.) → Fonctionne sans API
- ✅ **Chunking** → Fonctionne sans API
- ✅ **Audit** → Fonctionne sans API
- ❌ **Enrichissement avec LLM** → Nécessite un provider configuré
- ❌ **Embedding** → Nécessite un provider configuré
- ❌ **Extraction VLM** (images) → Nécessite un provider VLM

## Providers recommandés par cas d'usage

### Développement local (gratuit)
```yaml
# config/04_enrichment.yaml
provider: "ollama"
model: "mistral:7b"

# config/06_embedding.yaml
provider: "ollama"
model: "nomic-embed-text"
```

### Production (meilleure qualité)
```yaml
# config/04_enrichment.yaml
provider: "openai"
model: "gpt-4-turbo-preview"

# config/06_embedding.yaml
provider: "openai"
model: "text-embedding-3-large"
```

### Budget limité (bon compromis)
```yaml
# config/04_enrichment.yaml
provider: "mistral_ai"
model: "mistral-small-latest"

# config/06_embedding.yaml
provider: "openai"
model: "text-embedding-3-small"
```

## Sécurité

### ✅ Bonnes pratiques

1. **Utiliser .env** pour les clés API
2. **Ajouter .env au .gitignore**
3. **Ne jamais commiter les clés** dans git
4. **Révoquer les clés compromises** immédiatement
5. **Utiliser des clés différentes** pour dev/prod

### ❌ À éviter

1. ❌ Clés en dur dans `global.yaml` commitées dans git
2. ❌ Partager les clés par email/Slack
3. ❌ Utiliser la même clé pour tous les environnements
4. ❌ Oublier de révoquer les anciennes clés

## Dépannage

### Erreur : "Variable d'environnement non définie"

**Problème** : Une clé API utilise `${VAR}` mais la variable n'existe pas.

**Solution 1** : Définir la variable dans `.env`
```bash
echo "OPENAI_API_KEY=sk-proj-xxx" >> .env
```

**Solution 2** : Remplacer par une valeur factice dans `global.yaml`
```yaml
api_key: "not-configured"  # Au lieu de ${OPENAI_API_KEY}
```

### Erreur : "Invalid API key"

**Problème** : La clé API est incorrecte ou expirée.

**Solution** :
1. Vérifier que la clé est correcte (pas de copier-coller partiel)
2. Vérifier qu'elle n'a pas expiré
3. Régénérer une nouvelle clé sur le site du provider

### Erreur : "Connection refused"

**Problème** : Le provider local (Ollama, LM Studio, vLLM) n'est pas démarré.

**Solution** :
```bash
# Ollama
ollama serve

# LM Studio
# Démarrer l'application et onglet "Local Server"

# vLLM
vllm serve model-name --port 8000
```

## Résumé

**Pour débuter sans clé API** :
1. ✅ Installer Ollama
2. ✅ Télécharger un modèle : `ollama pull mistral:7b`
3. ✅ Démarrer : `ollama serve`
4. ✅ Lancer le pipeline : `./start.sh`

**Pour utiliser OpenAI/Anthropic** :
1. Obtenir une clé API
2. Créer `.env` avec `OPENAI_API_KEY=sk-proj-xxx`
3. Modifier `config/global.yaml` pour utiliser `${OPENAI_API_KEY}`
4. Configurer le provider dans les étapes (enrichment, embedding)

**État actuel** : Toutes les clés sont configurées avec des valeurs factices. Le pipeline **fonctionne sans erreur** pour l'extraction de texte (étapes 1-2).
