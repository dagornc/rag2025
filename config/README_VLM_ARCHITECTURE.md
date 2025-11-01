# Architecture Unifiée VLM pour l'Extraction de Documents

## Vue d'ensemble

Le système d'extraction de documents utilise une **architecture unifiée** pour les LLM et VLM (Vision Language Models). Les VLM sont traités comme des LLM avec capacité vision, partageant la même infrastructure de configuration.

---

## Principe : Séparation Infrastructure / Fonctionnel

### Niveau 1 : Infrastructure (global.yaml)

Définit les **connexions** aux services LLM/VLM :
- URL de l'API
- Clé d'authentification
- Méthode d'accès

```yaml
# config/global.yaml
llm_providers:
  openai:
    access_method: "openai_compatible"
    base_url: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"

  anthropic:
    access_method: "openai_compatible"
    base_url: "https://api.anthropic.com/v1"
    api_key: "${ANTHROPIC_API_KEY}"

  ollama:
    access_method: "openai_compatible"
    base_url: "http://localhost:11434/v1"
    api_key: "ollama"
```

### Niveau 2 : Fonctionnel (config d'étape)

Chaque extracteur VLM choisit :
- Quel **provider** utiliser (référence à global.yaml)
- Quel **modèle** utiliser
- Les **paramètres** de génération (temperature, max_tokens)

```yaml
# config/02_preprocessing.yaml
fallback:
  extractors:
    - name: "vlm"
      config:
        provider: "openai"  # → global.yaml > llm_providers > openai
        model: "gpt-4-vision-preview"
        temperature: 0.0
        max_tokens_per_page: 2000
```

---

## Implémentation Technique

### 1. Fonction Unifiée : `get_llm_client()`

Dans `rag_framework/config.py`, la fonction `get_llm_client()` crée un client unifié :

```python
from rag_framework.config import get_llm_client, load_config

# Chargement config globale
global_config = load_config()

# Création client VLM (identique à LLM)
vlm_client = get_llm_client(
    provider_name="openai",
    model="gpt-4-vision-preview",
    temperature=0.0,
    global_config=global_config,
)
```

**Cette fonction :**
1. Récupère les infos du provider depuis `global_config.llm_providers`
2. Extrait `base_url` et `api_key`
3. Crée un client OpenAI compatible
4. Attache `model` et `temperature` au client

### 2. VLMExtractor : Utilisation du Client Unifié

Dans `rag_framework/extractors/vlm_extractor.py` :

```python
class VLMExtractor(BaseExtractor):
    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)

        # Chargement de la config globale
        self.global_config = load_config()

        # Création du client VLM via get_llm_client()
        if config.get("provider") and config.get("model"):
            self.vlm_client = get_llm_client(
                provider_name=config["provider"],
                model=config["model"],
                temperature=config.get("temperature", 0.0),
                global_config=self.global_config,
            )
```

**Avantages :**
- ✅ Même infrastructure pour LLM et VLM
- ✅ Centralisation des credentials (global.yaml)
- ✅ Pas de duplication de code
- ✅ Facile d'ajouter de nouveaux providers

---

## Providers VLM Supportés

### OpenAI (Commercial)

**Configuration :**
```yaml
llm_providers:
  openai:
    access_method: "openai_compatible"
    base_url: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
```

**Modèles vision disponibles :**
- `gpt-4-vision-preview` : Premier modèle vision
- `gpt-4o` : Dernière génération, plus rapide
- `gpt-4-turbo` : Équilibre vitesse/qualité

**Caractéristiques :**
- Qualité : ⭐⭐⭐⭐⭐
- Vitesse : Moyenne
- Coût : $0.01-0.03 par page
- API stable et documentée

**Usage dans config :**
```yaml
vlm:
  config:
    provider: "openai"
    model: "gpt-4o"  # Recommandé (meilleur rapport qualité/prix)
```

---

### Anthropic (Commercial)

**Configuration :**
```yaml
llm_providers:
  anthropic:
    access_method: "openai_compatible"
    base_url: "https://api.anthropic.com/v1"
    api_key: "${ANTHROPIC_API_KEY}"
```

**Modèles vision disponibles :**
- `claude-3-opus-20240229` : Meilleure qualité
- `claude-3-sonnet-20240229` : Plus rapide, moins cher

**Caractéristiques :**
- Qualité : ⭐⭐⭐⭐⭐
- Vitesse : Moyenne-Rapide
- Coût : $0.02-0.05 par page
- Excellente compréhension contextuelle

**Usage dans config :**
```yaml
vlm:
  config:
    provider: "anthropic"
    model: "claude-3-opus-20240229"  # Meilleure qualité absolue
```

---

### Ollama (Local, Gratuit)

**Configuration :**
```yaml
llm_providers:
  ollama:
    access_method: "openai_compatible"
    base_url: "http://localhost:11434/v1"
    api_key: "ollama"
```

**Installation préalable :**
```bash
# Installer Ollama
curl https://ollama.ai/install.sh | sh

# Télécharger un modèle vision
ollama pull llava:13b
# ou
ollama pull llava:7b
```

**Modèles vision disponibles :**
- `llava:13b` : Meilleur modèle local (13 milliards paramètres)
- `llava:7b` : Plus léger et rapide
- `bakllava` : Alternative basée sur Mistral

**Caractéristiques :**
- Qualité : ⭐⭐⭐ (inférieure aux modèles commerciaux)
- Vitesse : Lente sur CPU, rapide sur GPU
- Coût : Gratuit
- Parfait pour développement/tests

**Usage dans config :**
```yaml
vlm:
  config:
    provider: "ollama"
    model: "llava:13b"  # Gratuit, local
```

---

## Comparaison des Providers VLM

| Critère | OpenAI | Anthropic | Ollama |
|---------|--------|-----------|--------|
| **Qualité extraction** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Vitesse** | Moyenne | Moyenne-Rapide | Lente (CPU) |
| **Coût** | $0.01-0.03/page | $0.02-0.05/page | Gratuit |
| **Setup** | Clé API requise | Clé API requise | Installation locale |
| **Stabilité** | Excellente | Excellente | Bonne |
| **Tableaux** | Excellent | Excellent | Correct |
| **Formules math** | Excellent | Excellent | Limité |
| **Documents complexes** | Excellent | Excellent | Correct |
| **Offline** | ❌ Non | ❌ Non | ✅ Oui |

---

## Flux de Configuration : Exemple Complet

### 1. Configuration Infrastructure (global.yaml)

```yaml
llm_providers:
  openai:
    access_method: "openai_compatible"
    base_url: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"

  ollama:
    access_method: "openai_compatible"
    base_url: "http://localhost:11434/v1"
    api_key: "ollama"
```

### 2. Configuration Fonctionnelle (02_preprocessing.yaml)

```yaml
fallback:
  profile: "custom"
  extractors:
    # Essayer Ollama d'abord (gratuit)
    - name: "vlm"
      enabled: true
      config:
        provider: "ollama"
        model: "llava:13b"
        temperature: 0.0
        max_pages: 3  # Limite pour tests

    # Fallback sur OpenAI si Ollama échoue
    - name: "vlm"
      enabled: true
      config:
        provider: "openai"
        model: "gpt-4o"
        temperature: 0.0
        max_pages: 10
```

### 3. Exécution

```python
from rag_framework.pipeline import Pipeline

# Lancement du pipeline
pipeline = Pipeline(config_dir="config")
result = pipeline.run(data={"file_paths": ["document.pdf"]})

# Le système essaie automatiquement :
# 1. Ollama LLaVA (gratuit)
# 2. Si échec → OpenAI GPT-4o (payant)
```

---

## Variables d'Environnement

Pour utiliser les providers commerciaux, définir les variables d'environnement :

```bash
# OpenAI
export OPENAI_API_KEY="sk-proj-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
```

Ou créer un fichier `.env` :

```env
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Recommandations par Cas d'Usage

### Développement / Tests

```yaml
vlm:
  config:
    provider: "ollama"
    model: "llava:13b"
```

**Raison :** Gratuit, permet de tester rapidement sans coût.

---

### Production (Budget limité)

```yaml
vlm:
  config:
    provider: "openai"
    model: "gpt-4o"
    max_pages: 5  # Limite pour contrôler coûts
```

**Raison :** Meilleur rapport qualité/prix, API stable.

---

### Production (Qualité critique)

```yaml
vlm:
  config:
    provider: "anthropic"
    model: "claude-3-opus-20240229"
    max_pages: 20
```

**Raison :** Meilleure qualité absolue pour documents importants.

---

### Production (Confidentiel / Offline)

```yaml
vlm:
  config:
    provider: "ollama"
    model: "llava:13b"
```

**Raison :** Données restent locales, pas de connexion internet requise.

---

## Bonnes Pratiques

### 1. Toujours Limiter `max_pages`

```yaml
vlm:
  config:
    max_pages: 10  # Évite coûts excessifs
```

### 2. Utiliser VLM en Dernier Recours

```yaml
fallback:
  extractors:
    - name: "pypdf2"
    - name: "docling"
    - name: "vlm"  # Seulement si les autres échouent
```

### 3. Tester avec Ollama d'abord

Avant de déployer avec OpenAI/Anthropic :

```bash
# Installer Ollama
ollama pull llava:13b

# Tester localement
# config: provider: "ollama"
python test_extraction.py
```

### 4. Monitorer les Coûts

```python
# Après extraction, vérifier les métriques
for doc in results["extracted_documents"]:
    if doc["extraction_method"] == "vlm":
        pages = doc["metadata"]["num_pages_processed"]
        print(f"VLM utilisé pour {pages} pages → ~${pages * 0.02:.2f}")
```

---

## Dépannage

### Erreur : "Provider 'openai' not found"

**Problème :** Le provider n'est pas défini dans `global.yaml`.

**Solution :**
```yaml
llm_providers:
  openai:
    access_method: "openai_compatible"
    base_url: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
```

---

### Erreur : "API key not set"

**Problème :** Variable d'environnement manquante.

**Solution :**
```bash
export OPENAI_API_KEY="sk-proj-..."
```

---

### Ollama : "Connection refused"

**Problème :** Ollama n'est pas démarré.

**Solution :**
```bash
# Démarrer Ollama
ollama serve

# Vérifier que le serveur répond
curl http://localhost:11434/api/tags
```

---

### VLM trop lent

**Problème :** Traitement de trop de pages.

**Solution :**
```yaml
vlm:
  config:
    max_pages: 3  # Limiter à 3 pages
```

---

## Conclusion

L'architecture unifiée VLM permet de :

1. ✅ **Centraliser** la configuration des providers (global.yaml)
2. ✅ **Réutiliser** le code LLM pour les VLM
3. ✅ **Switcher** facilement entre providers
4. ✅ **Tester** gratuitement avec Ollama
5. ✅ **Déployer** en production avec OpenAI/Anthropic

**Best practice :** Commencer avec Ollama pour les tests, puis passer à OpenAI `gpt-4o` en production.
