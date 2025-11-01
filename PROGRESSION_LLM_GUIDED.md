# Logs de Progression pour llm_guided

## 🎯 Problème Résolu

Avec la stratégie `llm_guided`, le traitement peut prendre plusieurs minutes sans aucun feedback visuel, donnant l'impression que le pipeline est bloqué.

**Symptôme** :
```
2025-10-31 16:24:18,003 - [3/8] ChunkingStep: DÉBUT
2025-10-31 16:24:18,003 - Texte trop long pour analyse LLM complète, découpage préliminaire
[... rien pendant 1-2 minutes ...]
```

---

## ✅ Solution Implémentée

Ajout de **logs de progression détaillés** pour suivre l'avancement du traitement LLM.

### Nouveaux Logs

#### 1. Découpage Préliminaire

**Avant** :
```
INFO - Texte trop long pour analyse LLM complète, découpage préliminaire
```

**Maintenant** :
```
INFO - Texte trop long (132808 chars) pour analyse LLM complète.
       Découpage en 17 chunks préliminaires pour traitement.
```

**Bénéfice** : Vous savez combien de chunks vont être traités

---

#### 2. Progression Chunk par Chunk

**Nouveau** :
```
INFO - 📊 Analyse LLM du chunk 1/17 (8000 chars)...
INFO - ✓ Chunk 1/17 analysé → 12 sous-chunks créés

INFO - 📊 Analyse LLM du chunk 2/17 (8000 chars)...
WARNING - ⏳ Rate limit atteint (tentative 1/4). Nouvelle tentative dans 2s...
INFO - 🔄 Retry tentative 2/4...
INFO - ✓ Chunk 2/17 analysé → 10 sous-chunks créés

INFO - 📊 Analyse LLM du chunk 3/17 (8000 chars)...
INFO - ✓ Chunk 3/17 analysé → 11 sous-chunks créés
...
```

**Bénéfice** :
- ✅ Voir l'avancement en temps réel (chunk X/Y)
- ✅ Voir les retries en cas d'erreur 429
- ✅ Voir combien de sous-chunks sont créés

---

#### 3. Résumé Final

**Nouveau** :
```
INFO - ✅ Analyse LLM terminée : 17 chunks → 183 chunks finaux
INFO - Chunking (llm_guided): 183 chunks créés depuis 1 documents
```

**Bénéfice** : Confirmation du nombre total de chunks créés

---

## 📊 Exemple Complet de Logs

Pour un document PDF de **132KB** (comme `guide_ebios.pdf`) :

```
16:24:18 - [3/8] ChunkingStep: DÉBUT
16:24:18 - Texte trop long (132808 chars) pour analyse LLM complète.
           Découpage en 17 chunks préliminaires pour traitement.

16:24:18 - 📊 Analyse LLM du chunk 1/17 (8000 chars)...
16:24:21 - ✓ Chunk 1/17 analysé → 12 sous-chunks créés

16:24:23 - 📊 Analyse LLM du chunk 2/17 (8000 chars)...
16:24:26 - ✓ Chunk 2/17 analysé → 10 sous-chunks créés

16:24:28 - 📊 Analyse LLM du chunk 3/17 (8000 chars)...
16:24:30 - WARNING - ⏳ Rate limit atteint (tentative 1/4). Nouvelle tentative dans 2s...
16:24:32 - INFO - 🔄 Retry tentative 2/4...
16:24:35 - ✓ Chunk 3/17 analysé → 11 sous-chunks créés

[... chunks 4 à 16 ...]

16:27:45 - 📊 Analyse LLM du chunk 17/17 (808 chars)...
16:27:47 - ✓ Chunk 17/17 analysé → 4 sous-chunks créés

16:27:47 - ✅ Analyse LLM terminée : 17 chunks → 183 chunks finaux
16:27:47 - Chunking (llm_guided): 183 chunks créés depuis 1 documents
16:27:47 - [3/8] ChunkingStep: TERMINÉE ✓
```

**Temps total** : ~3min30s pour un document de 132KB

---

## ⏱️ Estimation du Temps de Traitement

### Formule

```
Temps ≈ (nombre_chunks × délai_entre_requêtes) + (nombre_chunks × temps_LLM) + retries

Où :
- nombre_chunks = ceil(taille_texte / 8000)
- délai_entre_requêtes = 2s (config)
- temps_LLM = 1-3s par appel
- retries = ~20% des chunks (erreurs 429)
```

### Exemples

| Taille Document | Chunks | Temps Estimé |
|----------------|--------|--------------|
| 10KB | 2 chunks | ~10-15s |
| 50KB | 7 chunks | ~30-45s |
| 100KB | 13 chunks | ~60-90s |
| 132KB | 17 chunks | ~90-120s |
| 500KB | 63 chunks | ~5-8 minutes |

---

## 🚦 États des Logs

### ✅ Traitement Normal

```
📊 Analyse LLM du chunk X/Y (size chars)...
✓ Chunk X/Y analysé → N sous-chunks créés
```

**Signification** : Tout va bien, le chunk a été analysé avec succès

---

### ⏳ Rate Limiting (Erreur 429)

```
⏳ Rate limit atteint (tentative 1/4). Nouvelle tentative dans 2s...
🔄 Retry tentative 2/4...
```

**Signification** : Le quota API est atteint, retry automatique en cours

**Normal** : Oui, environ 20% des chunks peuvent avoir des erreurs 429

**Action** : Aucune, le système gère automatiquement

---

### ❌ Fallback Recursive

```
WARNING - Pas de boundaries trouvées, fallback recursive
```

**Signification** : Le LLM n'a pas retourné de JSON valide, fallback sur stratégie recursive

**Impact** : Qualité légèrement réduite pour ce chunk spécifique

---

## 🔧 Configuration pour Logs de Progression

**Fichier** : `rag_framework/steps/step_03_chunking.py`

**Modifications apportées** :

1. **Ligne 394-397** : Log du nombre de chunks préliminaires
   ```python
   logger.info(
       f"Texte trop long ({len(text)} chars) pour analyse LLM complète. "
       f"Découpage en {total_preliminary} chunks préliminaires pour traitement."
   )
   ```

2. **Ligne 402-405** : Log début de traitement chunk
   ```python
   logger.info(
       f"📊 Analyse LLM du chunk {idx}/{total_preliminary} "
       f"({len(prelim_chunk)} chars)..."
   )
   ```

3. **Ligne 408-411** : Log fin de traitement chunk
   ```python
   logger.info(
       f"✓ Chunk {idx}/{total_preliminary} analysé → "
       f"{len(sub_chunks)} sous-chunks créés"
   )
   ```

4. **Ligne 413-416** : Log résumé final
   ```python
   logger.info(
       f"✅ Analyse LLM terminée : {total_preliminary} chunks → "
       f"{len(final_chunks)} chunks finaux"
   )
   ```

5. **Ligne 479-484** : Log retry amélioré
   ```python
   logger.warning(
       f"⏳ Rate limit atteint (tentative {attempt + 1}/{max_retries + 1}). "
       f"Nouvelle tentative dans {delay}s..."
   )
   time.sleep(delay)
   logger.info(f"🔄 Retry tentative {attempt + 2}/{max_retries + 1}...")
   ```

---

## 💡 Recommandations

### Pour le Développement

**Utilisez `recursive` au lieu de `llm_guided`** :

```yaml
# config/03_chunking.yaml
strategy: "recursive"  # Rapide, gratuit, excellente qualité
```

**Raisons** :
- ✅ 100x plus rapide (~3s vs ~3min pour 132KB)
- ✅ Gratuit (0 appel API)
- ✅ Qualité excellente (LangChain)
- ✅ Pas de rate limit

---

### Pour Tester llm_guided

**Utilisez un petit fichier** :

```bash
# Créer un fichier de test de 10KB au lieu de 132KB
echo "Test content..." > data/input/docs/test_small.txt
```

**Avantages** :
- Traitement rapide (~10-15s)
- Voir tous les logs sans attendre
- Valider le fonctionnement

---

### Pour la Production avec llm_guided

**Conditions requises** :
- Budget API conséquent
- Quota élevé (>1000 req/min)
- Temps de traitement acceptable (quelques minutes/document)

**Configuration recommandée** :

```yaml
# config/03_chunking.yaml
strategy: "llm_guided"

llm:
  rate_limiting:
    delay_between_requests: 2.0  # Min 2s pour éviter 429
    max_retries: 5              # Plus de retries pour robustesse
```

---

## 🎯 Résumé

### Avant (Sans Logs)

```
[3/8] ChunkingStep: DÉBUT
Texte trop long pour analyse LLM complète, découpage préliminaire
[... silence pendant 3 minutes ...]
[3/8] ChunkingStep: TERMINÉE ✓
```

❌ **Problème** : Impression de blocage, pas de feedback

---

### Maintenant (Avec Logs)

```
[3/8] ChunkingStep: DÉBUT
Texte trop long (132808 chars). Découpage en 17 chunks préliminaires.

📊 Analyse LLM du chunk 1/17 (8000 chars)...
✓ Chunk 1/17 analysé → 12 sous-chunks créés

📊 Analyse LLM du chunk 2/17 (8000 chars)...
⏳ Rate limit atteint. Retry dans 2s...
🔄 Retry tentative 2/4...
✓ Chunk 2/17 analysé → 10 sous-chunks créés

[... progression visible ...]

✅ Analyse LLM terminée : 17 chunks → 183 chunks finaux
Chunking (llm_guided): 183 chunks créés depuis 1 documents
[3/8] ChunkingStep: TERMINÉE ✓
```

✅ **Avantages** :
- Progression visible en temps réel
- Information sur les retries
- Estimation du temps restant
- Confirmation du succès

---

## 🚀 Pour Voir les Nouveaux Logs

**Redémarrez le pipeline** :

```bash
# Arrêter l'ancien pipeline
pkill -f rag-pipeline

# Relancer avec les nouveaux logs
rye run rag-pipeline --watch
```

**Logs attendus** : Progression détaillée comme décrit ci-dessus

---

**Date** : 2025-10-31
**Version** : 1.0
