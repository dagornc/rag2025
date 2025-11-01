# Fix : Classification LLM avec Explications Non Désirées

## 🎯 Problème Résolu

Lors de la classification de sensibilité avec LLM (étape 4 - Enrichment), le modèle retournait des réponses avec explications longues au lieu de juste la valeur attendue.

**Symptôme** :
```
WARNING - Classification LLM invalide: 'interne

explication: le document semble être destiné aux membres internes...'.
Utilisation de la valeur par défaut.
```

Le LLM retournait :
```
interne

explication: le document semble être destiné aux membres internes ou au personnel
d'une entreprise, car il fournit une liste de règles et conseils pour améliorer
la sécurité...
```

Au lieu de juste :
```
interne
```

---

## ✅ Solution Implémentée

### 1. Amélioration du Parsing (step_04_enrichment.py)

**Avant** (ligne 300) :
```python
classification: str = content.strip().lower()
```

**Maintenant** (lignes 300-306) :
```python
# Extraire uniquement la première ligne (ignore les explications supplémentaires)
# Le LLM retourne souvent: "interne\n\nexplication: ..."
# On ne garde que le premier mot de la première ligne non-vide
first_line = content.strip().split('\n')[0].strip().lower()

# Extraire le premier mot (au cas où il y aurait du texte sur la même ligne)
classification: str = first_line.split()[0] if first_line.split() else ""
```

**Bénéfice** : Extrait uniquement le premier mot de la première ligne, ignore les explications

---

### 2. Amélioration du Prompt (config/04_enrichment.yaml)

**Avant** (ligne 38-51) :
```yaml
sensitivity_classification: |
  Classifie le niveau de sensibilité du document suivant.
  Réponds UNIQUEMENT par l'un de ces mots: public, interne, confidentiel, secret

  Critères:
  - public: Information accessible à tous
  - interne: Information pour l'entreprise uniquement
  - confidentiel: Information sensible, accès restreint
  - secret: Information hautement sensible, accès très restreint

  Document:
  {text}

  Niveau de sensibilité:
```

**Maintenant** (lignes 38-53) :
```yaml
sensitivity_classification: |
  Classifie le niveau de sensibilité du document suivant.

  IMPORTANT: Réponds UNIQUEMENT avec UN SEUL MOT, sans explication ni justification.
  Valeurs possibles: public, interne, confidentiel, secret

  Exemples de réponses attendues:
  - Si document accessible à tous → réponds: public
  - Si document pour l'entreprise uniquement → réponds: interne
  - Si document sensible, accès restreint → réponds: confidentiel
  - Si document hautement sensible, accès très restreint → réponds: secret

  Document à classifier:
  {text}

  Niveau de sensibilité (un seul mot):
```

**Bénéfice** : Instructions plus claires et exemples explicites pour éviter les explications

---

### 3. Amélioration du Log d'Erreur

**Avant** (ligne 307-310) :
```python
logger.warning(
    f"Classification LLM invalide: '{classification}'. "
    "Utilisation de la valeur par défaut."
)
```

**Maintenant** (lignes 314-317) :
```python
logger.warning(
    f"Classification LLM invalide: '{classification}' "
    f"(réponse complète: '{content[:100]}...'). "
    "Utilisation de la valeur par défaut."
)
```

**Bénéfice** : Log montre la réponse complète du LLM pour faciliter le debug

---

## 📊 Résultat Attendu

### Avant (Avec Warnings)

```
WARNING - Classification LLM invalide: 'interne

explication: le document semble...'. Utilisation de la valeur par défaut.
WARNING - Classification LLM invalide: 'confidentiel

le document discute...'. Utilisation de la valeur par défaut.
[... répété pour chaque chunk ...]
```

❌ **Problème** : Warnings constants, utilisation du fallback au lieu de la classification LLM

---

### Maintenant (Classification Correcte)

```
DEBUG - Classification LLM: 'interne'
DEBUG - Classification LLM: 'confidentiel'
DEBUG - Classification LLM: 'public'
[... pas de warnings ...]

INFO - Enrichment: 106 chunks enrichis
```

✅ **Résultat** : Classification correcte sans warnings, LLM utilisé comme prévu

---

## 🔧 Architecture de la Solution

### Stratégie de Parsing Multi-Niveau

1. **Niveau 1** : Extraire la première ligne
   ```python
   first_line = content.strip().split('\n')[0].strip().lower()
   ```

2. **Niveau 2** : Extraire le premier mot de cette ligne
   ```python
   classification = first_line.split()[0] if first_line.split() else ""
   ```

3. **Niveau 3** : Valider contre les valeurs attendues
   ```python
   valid_levels = ["public", "interne", "confidentiel", "secret"]
   if classification in valid_levels:
       return classification
   ```

4. **Niveau 4** : Fallback sur valeur par défaut si invalide
   ```python
   else:
       logger.warning(...)
       return default_level
   ```

---

## 🎯 Cas de Test

### Test Case 1 : Réponse Propre
**Input LLM** : `"interne"`
**Output** : `"interne"` ✅

### Test Case 2 : Réponse avec Explication (après newline)
**Input LLM** :
```
interne

explication: le document semble être destiné...
```
**Output** : `"interne"` ✅

### Test Case 3 : Réponse avec Texte sur la Même Ligne
**Input LLM** : `"confidentiel car le document contient..."`
**Output** : `"confidentiel"` ✅

### Test Case 4 : Réponse Invalide
**Input LLM** : `"très confidentiel"`
**Output** : `"confidentiel"` (default) + warning ✅

### Test Case 5 : Réponse avec Capitalisation
**Input LLM** : `"INTERNE"`
**Output** : `"interne"` ✅ (toLowerCase appliqué)

---

## 🚦 Configuration Recommandée

Pour éviter les explications du LLM, deux approches complémentaires :

### 1. Approche Prompt Engineering (Préventif)

Ajouter dans le prompt :
- "IMPORTANT: Réponds UNIQUEMENT avec UN SEUL MOT"
- "sans explication ni justification"
- Exemples concrets de réponses attendues

### 2. Approche Parsing Robuste (Correctif)

Extraire juste le premier mot :
```python
classification = content.strip().split('\n')[0].strip().split()[0].lower()
```

**Recommandation** : Utiliser les deux approches ensemble pour maximiser la fiabilité

---

## 💡 Amélioration Future Possible

### Option 1 : Utiliser un Modèle Plus Obéissant

Certains modèles suivent mieux les instructions de format :
- `mistral-small-latest` (bon équilibre)
- `gpt-4-turbo` (excellent, mais coûteux)
- `llama-3-instruct` (bon pour instructions simples)

### Option 2 : System Prompt Dédié

Ajouter un system prompt dans l'appel API :
```python
messages=[
    {"role": "system", "content": "Tu es un classificateur. Tu réponds uniquement avec un mot."},
    {"role": "user", "content": prompt}
]
```

### Option 3 : Temperature à 0.0

Déjà configuré dans `config/04_enrichment.yaml` :
```yaml
temperature: 0.0  # Réponses déterministes
```

---

## 📝 Checklist de Vérification

Pour valider que le fix fonctionne :

✅ **Étape 1** : Vérifier le parsing du code
```bash
grep -A 10 "first_line = content.strip()" rag_framework/steps/step_04_enrichment.py
```

✅ **Étape 2** : Vérifier le prompt amélioré
```bash
grep -A 15 "sensitivity_classification:" config/04_enrichment.yaml
```

✅ **Étape 3** : Redémarrer le pipeline
```bash
pkill -f rag-pipeline
rye run rag-pipeline --watch
```

✅ **Étape 4** : Vérifier les logs (plus de warnings)
```bash
# Observer les logs - devrait voir des DEBUG au lieu de WARNING
```

---

## 🔍 Debug en Cas de Problème Persistant

Si les warnings persistent après le fix :

### 1. Vérifier la Réponse LLM Complète

Ajouter un log temporaire dans `step_04_enrichment.py` ligne 293 :
```python
content = self._call_llm_with_retry(prompt, max_tokens)
logger.debug(f"Réponse LLM complète: '{content}'")  # ← Ajouter ce log
```

### 2. Vérifier le Prompt Envoyé

Ajouter un log temporaire ligne 288 :
```python
prompt = prompt_template.format(text=text[:1000])
logger.debug(f"Prompt envoyé: '{prompt[:500]}...'")  # ← Ajouter ce log
```

### 3. Tester avec un Autre Modèle

Modifier `config/04_enrichment.yaml` :
```yaml
provider: "mistral_ai"  # Au lieu de lm_studio
model: "mistral-small-latest"
```

---

**Date** : 2025-10-31
**Version** : 1.0
**Fichiers Modifiés** :
- `rag_framework/steps/step_04_enrichment.py` (lignes 300-321)
- `config/04_enrichment.yaml` (lignes 38-53)
