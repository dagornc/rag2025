# Stratégie de Chunking LLM-Guided

## Vue d'ensemble

La stratégie **`llm_guided`** utilise un LLM pour analyser le contenu et déterminer les meilleurs points de découpage en fonction du contexte sémantique. Elle produit des chunks de meilleure qualité que les stratégies simples mais est **beaucoup plus coûteuse** en termes d'appels API.

## ⚠️ Attention : Rate Limiting

### Problème

Pour un document de **132 808 caractères** :
- Découpage préliminaire → ~8-10 chunks de 8000 caractères
- **8-10 appels LLM** pour analyser chaque chunk
- **Risque élevé d'erreur 429** (rate limit exceeded)

### Solution

La stratégie inclut maintenant :
- ✅ **Retry automatique** avec backoff exponentiel
- ✅ **Délai préventif** entre requêtes
- ✅ **Fallback sur `recursive`** en cas d'échec

Mais cela peut **multiplier par 10-20 le temps de traitement** et **le coût API**.

## Comparaison des Stratégies

| Stratégie | Appels API | Temps | Qualité | Coût | Recommandation |
|-----------|-----------|-------|---------|------|----------------|
| **recursive** | 0 | ~1s | ⭐⭐⭐⭐ | Gratuit | ✅ **Recommandé** |
| **fixed** | 0 | ~0.5s | ⭐⭐⭐ | Gratuit | Pour tests rapides |
| **semantic** | 0 | ~5-10s | ⭐⭐⭐⭐⭐ | Gratuit (local) | Si embeddings disponibles |
| **llm_guided** | 8-10 | ~30-60s | ⭐⭐⭐⭐⭐ | €€€ | ⚠️ Pour production avec quota élevé |

## Configuration

### Option 1 : Recursive (Recommandée)

**Pour la plupart des cas d'usage** :

```yaml
# config/03_chunking.yaml
strategy: "recursive"

recursive:
  chunk_size: 1000
  chunk_overlap: 200
```

**Avantages** :
- ✅ Rapide (pas d'appel API)
- ✅ Gratuit
- ✅ Qualité excellente (découpage hiérarchique)
- ✅ Pas de rate limit

### Option 2 : LLM-Guided (Production avec quota élevé)

**Uniquement si** :
- Vous avez un quota API élevé
- Le coût n'est pas un problème
- Vous avez besoin de la meilleure qualité possible

```yaml
# config/03_chunking.yaml
strategy: "llm_guided"

llm:
  enabled: true
  provider: "mistral_ai"
  model: "mistral-small-latest"

  rate_limiting:
    enabled: true
    delay_between_requests: 1.0  # 1s entre requêtes
    max_retries: 3
    retry_delay_base: 2
    exponential_backoff: true
```

**Implications** :
- ❌ 8-10 appels API par document
- ❌ Temps de traitement ~30-60s par document
- ❌ Coût élevé (€€€)
- ⚠️ Risque de rate limit si quota faible

### Option 3 : LLM-Guided avec Provider Local

**Meilleur compromis** :

```yaml
# config/03_chunking.yaml
strategy: "llm_guided"

llm:
  enabled: true
  provider: "ollama"  # ou lm_studio
  model: "llama3"

  rate_limiting:
    enabled: false  # Pas nécessaire en local
```

**Avantages** :
- ✅ Qualité LLM
- ✅ Gratuit (local)
- ✅ Pas de rate limit
- ❌ Nécessite modèle local installé
- ❌ Plus lent qu'une API cloud

## Calcul du Coût

### Avec Mistral AI

Pour un document de **132 808 caractères** :
- **10 appels** × 4000 tokens input × 0.001 € / 1000 tokens
- **Coût estimé** : ~0.04 € par document

Pour **1000 documents** :
- **10 000 appels API**
- **Coût estimé** : ~40 €

### Avec OpenAI

Pour un document de **132 808 caractères** :
- **10 appels** × 4000 tokens input × 0.015 € / 1000 tokens (GPT-3.5)
- **Coût estimé** : ~0.60 € par document

Pour **1000 documents** :
- **Coût estimé** : ~600 €

## Calcul du Temps

### Avec Rate Limiting (delay=1.0s)

```
Temps total = (nombre_appels × delay) + (temps_traitement_LLM × nombre_appels)
            = (10 × 1.0s) + (10 × 1-2s)
            = 10s + 10-20s
            = 20-30s par document
```

### Sans Rate Limiting (risque 429)

```
Temps total = nombre_appels × temps_traitement_LLM
            = 10 × 1-2s
            = 10-20s par document
```

Mais avec **forte probabilité d'erreurs 429** nécessitant des retries (×3-4).

## Recommandation Finale

### Pour le Développement
```yaml
strategy: "recursive"
```
- Rapide, gratuit, excellente qualité

### Pour la Production (Usage Normal)
```yaml
strategy: "recursive"
```
- Le découpage hiérarchique de `recursive` est **suffisant** pour 95% des cas

### Pour la Production (Usage Premium)
```yaml
strategy: "llm_guided"
llm:
  provider: "ollama"  # Provider local
  model: "llama3"
```
- Qualité maximale sans coût API

### Pour la Production (Très Haute Qualité + Budget)
```yaml
strategy: "llm_guided"
llm:
  provider: "mistral_ai"
  model: "mistral-small-latest"
  rate_limiting:
    delay_between_requests: 2.0  # 2s = max 30 req/min
```
- Meilleure qualité possible
- Coût élevé accepté
- Quota API suffisant

## Test de la Stratégie

Pour tester `llm_guided` sans dépenser :

```bash
# Tester avec un petit fichier (< 10 000 caractères)
rye run python test_chunking_strategies.py

# Ou utiliser un provider local
# 1. Installer Ollama
brew install ollama

# 2. Télécharger un modèle
ollama pull llama3

# 3. Configurer
# config/03_chunking.yaml
strategy: "llm_guided"
llm:
  provider: "ollama"
  model: "llama3"
```

## Comparaison Visuelle

### Recursive (Rapide, Gratuit)
```
Document (132KB)
    ↓ Découpage hiérarchique (séparateurs)
    → 166 chunks en ~1s
    ✅ Gratuit, Rapide, Excellente qualité
```

### LLM-Guided (Lent, Coûteux, Premium)
```
Document (132KB)
    ↓ Découpage préliminaire
    → 10 chunks de 8KB
    ↓ Analyse LLM (10 appels × 1-2s + délais)
    → Détection boundaries sémantiques
    ↓ Découpage final
    → 150-180 chunks en ~30-60s
    ⚠️ 10 appels API, Lent, Qualité maximale
```

## Conclusion

**Pour 99% des cas d'usage** : Utilisez `strategy: "recursive"`

**Seulement si** :
- Budget API élevé
- Quota suffisant
- Besoin absolu de qualité maximale
- Documents complexes nécessitant découpage contextuel

→ Utilisez `strategy: "llm_guided"` avec provider local (Ollama) ou cloud avec rate limiting strict.
