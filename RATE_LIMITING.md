# Gestion du Rate Limiting (Erreurs 429)

## Problème

Lors du traitement de nombreux chunks avec l'API Mistral AI (ou toute autre API), vous pouvez rencontrer des erreurs **429 - Service tier capacity exceeded**. Cela signifie que vous dépassez les limites de requêtes de votre plan API.

Exemple d'erreur :
```
Error code: 429 - {'object': 'error', 'message': 'Service tier capacity exceeded for this model.', 'type': 'service_tier_capacity_exceeded', 'param': None, 'code': '3505'}
```

## Solution 1 : Désactiver le LLM (Simple et rapide)

La solution la plus simple est de désactiver temporairement le LLM et d'utiliser la classification par mots-clés.

### Configuration

Dans `config/04_enrichment.yaml` :

```yaml
llm:
  enabled: false  # ← Désactiver le LLM
```

### Avantages
- ✅ Pas de limite de requêtes
- ✅ Traitement instantané
- ✅ Pas de coût API

### Inconvénients
- ❌ Classification moins précise (basée sur mots-clés)
- ❌ Pas de compréhension sémantique

---

## Solution 2 : Rate Limiting Intelligent (Recommandé)

Système de gestion automatique des limites avec retry et backoff exponentiel.

### Configuration

Dans `config/04_enrichment.yaml` :

```yaml
llm:
  enabled: true  # ← Activer le LLM
  provider: "mistral_ai"
  model: "mistral-small-latest"

  # Gestion du rate limiting
  rate_limiting:
    enabled: true                  # Activer la gestion du rate limiting
    delay_between_requests: 0.5    # Délai entre chaque requête (secondes)
    max_retries: 3                 # Nombre maximum de tentatives en cas d'erreur 429
    retry_delay_base: 2            # Délai de base pour retry (secondes)
    exponential_backoff: true      # Utiliser backoff exponentiel (2s, 4s, 8s, etc.)
```

### Fonctionnement

1. **Délai préventif** : Attend `delay_between_requests` secondes entre chaque requête
2. **Détection 429** : Détecte automatiquement les erreurs de rate limit
3. **Retry avec backoff** :
   - Tentative 1 : Erreur 429 → Attend 2s
   - Tentative 2 : Erreur 429 → Attend 4s
   - Tentative 3 : Erreur 429 → Attend 8s
   - Tentative 4 : Erreur 429 → **Abandon** + Fallback sur mots-clés

### Avantages
- ✅ Classification LLM précise (quand possible)
- ✅ Gestion automatique des erreurs 429
- ✅ Fallback sur mots-clés en cas d'échec
- ✅ Optimisation automatique du débit de requêtes

### Inconvénients
- ❌ Traitement plus lent (délais entre requêtes)
- ❌ Coût API (si requêtes réussies)

---

## Recommandations par Cas d'Usage

### Pour le développement / tests
**→ Solution 1** (LLM désactivé)
- Traitement rapide
- Pas de consommation d'API
- Classification basique suffisante pour les tests

### Pour la production avec quota limité
**→ Solution 2** avec délais plus longs
```yaml
rate_limiting:
  delay_between_requests: 1.0  # 1 seconde entre requêtes
  max_retries: 5
  retry_delay_base: 5
```

### Pour la production avec quota élevé
**→ Solution 2** avec délais courts
```yaml
rate_limiting:
  delay_between_requests: 0.1  # 100ms entre requêtes
  max_retries: 3
  retry_delay_base: 2
```

### Pour traitement volumineux (>1000 chunks)
**→ Combiner les deux** :
1. Désactiver LLM pour enrichissement (étape 4)
2. Garder LLM pour résumés d'audit (étape 5, moins de requêtes)

```yaml
# config/04_enrichment.yaml
llm:
  enabled: false  # Pas de LLM pour classification (166 chunks = trop)

# config/05_audit.yaml
llm:
  enabled: true   # LLM pour résumés d'audit (1 seule requête)
```

---

## Monitoring

Surveillez les logs pour ajuster les paramètres :

```bash
# Comptez les erreurs 429
grep "429" logs/rag_audit.log | wc -l

# Comptez les fallbacks sur mots-clés
grep "Fallback sur mots-clés" logs/rag_audit.log | wc -l

# Temps total de traitement
tail -100 logs/rag_audit.log | grep "PIPELINE TERMINÉ"
```

## Calcul du Débit Optimal

Pour un quota API de **N requêtes/minute** :

```
delay_between_requests = 60 / N

Exemples :
- 60 req/min  → delay = 1.0s
- 120 req/min → delay = 0.5s
- 10 req/min  → delay = 6.0s
```

---

## FAQ

### Le pipeline est trop lent avec le rate limiting
→ Augmentez votre plan API ou désactivez le LLM pour l'enrichissement

### J'ai encore des erreurs 429 malgré le rate limiting
→ Augmentez `delay_between_requests` et `retry_delay_base`

### Je veux classification LLM SEULEMENT pour certains chunks
→ Implémentez une logique conditionnelle dans `_classify_sensitivity()` :
```python
# Exemple : LLM uniquement si chunk contient "confidentiel"
if "confidentiel" in text.lower():
    return self._classify_sensitivity_with_llm(text)
else:
    return self._classify_sensitivity_keywords(text)
```

### Puis-je utiliser un provider local (Ollama, LM Studio) ?
→ **OUI !** Pas de limite de requêtes avec les providers locaux :
```yaml
llm:
  provider: "ollama"  # ou lm_studio
  model: "llama3"
  rate_limiting:
    enabled: false  # Pas nécessaire pour providers locaux
```
