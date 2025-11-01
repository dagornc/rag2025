# Configuration des LLM Providers - Guide d'utilisation

## 🎯 Architecture de Configuration

La configuration des LLM suit une **architecture en deux niveaux** :

### Niveau 1 : Configuration Transversale (global.yaml)

**Localisation :** `config/global.yaml` → section `llm_providers`

**Rôle :** Définir les **connexions** aux services LLM (infrastructure)

**Contient :**
- `base_url` : URL du service API
- `api_key` : Clé d'authentification (ou `${ENV_VAR}`)
- `access_method` : Méthode d'accès (openai_compatible, huggingface_inference_api)

### Niveau 2 : Configuration Fonctionnelle (par étape)

**Localisation :** Chaque fichier `config/XX_step_name.yaml`

**Rôle :** Choisir **quel modèle utiliser** pour cette tâche spécifique

**Contient :**
- `provider` : Nom du provider (référence à global.yaml)
- `model` : Modèle spécifique (ex: "llama3", "mistral-large-latest")
- `temperature` : Température pour cette tâche (0.0 = déterministe, 1.0 = créatif)
- `max_tokens` : Limite de tokens pour les réponses

## 📋 Providers Disponibles

### Providers Locaux (Gratuits)

#### 1. LM Studio
```yaml
# global.yaml
llm_providers:
  lm_studio:
    access_method: "openai_compatible"
    base_url: "http://127.0.0.1:1234/v1"
    api_key: "lm-studio"
```

**Utilisation dans une étape :**
```yaml
# 04_enrichment.yaml
llm:
  enabled: true
  provider: "lm_studio"
  model: "llama-3.1-8b-instruct"  # Nom du modèle chargé dans LM Studio
  temperature: 0.0
```

**Installation :** https://lmstudio.ai/

#### 2. Ollama
```yaml
# global.yaml
llm_providers:
  ollama:
    access_method: "openai_compatible"
    base_url: "http://127.0.0.1:11434/v1"
    api_key: "ollama"
```

**Utilisation dans une étape :**
```yaml
# 04_enrichment.yaml
llm:
  enabled: true
  provider: "ollama"
  model: "llama3"  # ou "mistral", "gemma2", etc.
  temperature: 0.0
```

**Installation :**
```bash
# macOS
brew install ollama
ollama serve

# Télécharger un modèle
ollama pull llama3
```

#### 3. vLLM (Production)
```yaml
# global.yaml
llm_providers:
  vllm:
    access_method: "openai_compatible"
    base_url: "http://127.0.0.1:8000/v1"
    api_key: "vllm"
```

**Utilisation :**
```bash
# Démarrer vLLM
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-3-8B-Instruct \
    --port 8000
```

### Providers Cloud (Payants)

#### 4. Hugging Face
```yaml
# global.yaml
llm_providers:
  huggingface:
    access_method: "huggingface_inference_api"
    base_url: "https://api-inference.huggingface.co/v1"
    api_key: "${HUGGINGFACE_API_KEY}"
```

**Configuration de la clé :**
```bash
export HUGGINGFACE_API_KEY="hf_your_actual_key_here"
```

**Utilisation dans une étape :**
```yaml
llm:
  enabled: true
  provider: "huggingface"
  model: "mistralai/Mistral-7B-Instruct-v0.2"
  temperature: 0.0
```

#### 5. Mistral AI
```yaml
# global.yaml
llm_providers:
  mistral_ai:
    access_method: "openai_compatible"
    base_url: "https://api.mistral.ai/v1"
    api_key: "${MISTRAL_API_KEY}"
```

**Utilisation dans une étape :**
```yaml
llm:
  enabled: true
  provider: "mistral_ai"
  model: "mistral-large-latest"  # ou "mistral-small-latest"
  temperature: 0.0
```

**Obtenir une clé :** https://console.mistral.ai/

## 🔧 Configuration par Étape

### Étape 4 : Enrichissement

**Cas d'usage :** Classification intelligente de documents

```yaml
# config/04_enrichment.yaml
llm:
  enabled: true  # Activer LLM pour classification
  provider: "ollama"
  model: "llama3"
  temperature: 0.0  # Déterministe pour classification
  max_tokens: 500
```

**Avantages :** Classification plus précise qu'avec mots-clés simples

### Étape 5 : Audit

**Cas d'usage :** Génération de résumés narratifs d'audit

```yaml
# config/05_audit.yaml
llm:
  enabled: false  # Désactivé par défaut (logs structurés suffisent)
  provider: "ollama"
  model: "llama3"
  temperature: 0.3  # Légèrement créatif pour narratifs
  max_tokens: 1000
```

**Avantages :** Résumés lisibles pour rapports de conformité

### Étape 3 : Chunking Sémantique

**Cas d'usage :** Découpage basé sur similarité sémantique

```yaml
# config/03_chunking.yaml
strategy: "semantic"  # Activer chunking sémantique

semantic:
  provider: "openai"
  model: "text-embedding-3-large"
  similarity_threshold: 0.75
```

## 🔐 Gestion des Clés API

### Méthode 1 : Variables d'Environnement (Recommandé)

```bash
# .env
export HUGGINGFACE_API_KEY="hf_xxxxx"
export MISTRAL_API_KEY="xxxxx"
export OPENAI_API_KEY="sk-xxxxx"
```

```yaml
# global.yaml
llm_providers:
  mistral_ai:
    api_key: "${MISTRAL_API_KEY}"  # Substitution automatique
```

### Méthode 2 : Fichier de Secrets (Production)

```bash
# Créer un fichier secrets.env (gitignored)
echo "MISTRAL_API_KEY=xxxxx" > secrets.env
source secrets.env
```

### ⚠️ Méthode 3 : Hardcodé (NON RECOMMANDÉ)

```yaml
# NE JAMAIS FAIRE EN PRODUCTION
llm_providers:
  mistral_ai:
    api_key: "76cwpvjZqnFw1U0jLCEBKOHh5FprX2OJ"  # ❌ Visible dans git!
```

**Danger :** Les clés commited dans git sont compromises immédiatement.

## 📊 Exemples de Configuration Complète

### Configuration Développement (Local)

```yaml
# config/global.yaml - Section llm_providers
llm_providers:
  ollama:
    access_method: "openai_compatible"
    base_url: "http://127.0.0.1:11434/v1"
    api_key: "ollama"

# config/04_enrichment.yaml
llm:
  enabled: true
  provider: "ollama"  # Gratuit, local
  model: "llama3"
  temperature: 0.0
```

### Configuration Production (Cloud)

```yaml
# config/global.yaml
llm_providers:
  mistral_ai:
    access_method: "openai_compatible"
    base_url: "https://api.mistral.ai/v1"
    api_key: "${MISTRAL_API_KEY}"

# config/04_enrichment.yaml
llm:
  enabled: true
  provider: "mistral_ai"  # API cloud professionnelle
  model: "mistral-large-latest"
  temperature: 0.0
```

## 🎛️ Paramètres Température

| Temperature | Comportement | Cas d'usage |
|-------------|--------------|-------------|
| 0.0 | Déterministe | Classification, extraction de données |
| 0.3 | Légèrement varié | Résumés, narratifs d'audit |
| 0.7 | Créatif | Génération de rapports, suggestions |
| 1.0 | Très créatif | Brainstorming (déconseillé pour audit) |

**Recommandation :** Utiliser 0.0 pour toutes les tâches d'audit et conformité (reproductibilité).

## 🔄 Migration depuis Ancienne Configuration

**Avant (global.yaml uniquement) :**
```yaml
llm_config:
  default_provider: "openai"
  openai:
    model: "gpt-4"
    temperature: 0.0
```

**Après (séparation infrastructure/fonctionnel) :**
```yaml
# global.yaml - Infrastructure
llm_providers:
  ollama:
    access_method: "openai_compatible"
    base_url: "http://127.0.0.1:11434/v1"
    api_key: "ollama"

# 04_enrichment.yaml - Fonctionnel
llm:
  enabled: true
  provider: "ollama"
  model: "llama3"
  temperature: 0.0
```

**Avantages :**
- ✅ Chaque étape choisit son modèle optimal
- ✅ Facile de tester différents providers
- ✅ Configuration centralisée des connexions
- ✅ Granularité fine (température par tâche)

## 🧪 Test de Configuration

```python
# test_llm_config.py
from rag_framework.config import load_config, load_step_config

# Charger config globale
global_config = load_config()
print("Providers disponibles:", global_config.llm_providers.keys())

# Charger config d'étape
step_config = load_step_config("04_enrichment.yaml")
if step_config.get("llm", {}).get("enabled"):
    print(f"LLM activé: {step_config['llm']['provider']}/{step_config['llm']['model']}")
```

## 📚 Ressources

- [LM Studio](https://lmstudio.ai/) - Interface locale
- [Ollama](https://ollama.ai/) - Runner LLM open-source
- [vLLM](https://docs.vllm.ai/) - Serveur haute performance
- [Hugging Face](https://huggingface.co/) - Plateforme modèles
- [Mistral AI](https://mistral.ai/) - Provider français

---

**Version:** 0.1.0
**Date:** 2025-10-30
**Statut:** ✅ Configuration multi-provider opérationnelle
