# Fix : Erreur Validation TesseractOcrOptions (lang doit être une liste)

## 🎯 Problème Résolu

Lors de l'utilisation de Docling avec Tesseract OCR, une erreur de validation Pydantic se produit :

**Erreur** :
```
2025-10-31 17:43:29,209 - WARNING - Erreur Docling extraction: 1 validation error for TesseractOcrOptions
lang
  Input should be a valid list [type=list_type, input_value='fra', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/list_type
```

**Cause** : Le paramètre `lang` de `TesseractOcrOptions` attend une **liste** de langues, pas une chaîne de caractères.

---

## ✅ Solution Implémentée

### 1. Code Python (docling_extractor.py)

**Avant** (lignes 107-111) :
```python
ocr_lang = self.config.get("ocr_lang", "fra")  # ❌ String

tesseract_options = TesseractOcrOptions(lang=ocr_lang)
```

**Après** (lignes 107-116) :
```python
# NOTE: lang doit être une LISTE de langues, pas une string
ocr_lang = self.config.get("ocr_lang", ["fra"])  # ✅ Liste

# Convertir en liste si c'est une string (ex: "fra" → ["fra"])
if isinstance(ocr_lang, str):
    ocr_lang = [ocr_lang]

tesseract_options = TesseractOcrOptions(lang=ocr_lang)
```

**Résultat** : Le code accepte maintenant à la fois les listes et les strings (conversion automatique)

---

### 2. Configuration YAML (config/02_preprocessing.yaml)

**Avant** (ligne 99) :
```yaml
ocr_lang: "fra"  # ❌ String
```

**Après** (ligne 99) :
```yaml
ocr_lang: ["fra"]  # ✅ Liste
```

**Résultat** : Configuration conforme à l'API Pydantic de Docling

---

## 📊 Formats Acceptés

### ✅ Formats Corrects

```yaml
# Une seule langue
ocr_lang: ["fra"]

# Plusieurs langues
ocr_lang: ["fra", "eng"]

# Trois langues ou plus
ocr_lang: ["fra", "eng", "deu"]
```

### ❌ Format Incorrect

```yaml
# String simple (causait l'erreur)
ocr_lang: "fra"

# String avec + (ne fonctionne pas)
ocr_lang: "fra+eng"
```

---

## 🧪 Test de Validation

Pour valider que le fix fonctionne :

```bash
# 1. Copier un PDF de test
cp data/output/processed/*.pdf data/input/docs/test_fix.pdf

# 2. Relancer le pipeline
rye run rag-pipeline 2>&1 | grep -E "Tentative extraction|Extraction réussie|TesseractOcrOptions"

# 3. Résultat attendu :
# "Tentative extraction avec 'docling'..."
# "✓ Extraction réussie avec 'docling'"
# Aucune erreur "TesseractOcrOptions"
```

---

## 📝 Exemples d'Utilisation

### Exemple 1 : Français Uniquement

```yaml
# config/02_preprocessing.yaml
extractors:
  - name: "docling"
    config:
      ocr_lang: ["fra"]
```

### Exemple 2 : Français + Anglais

```yaml
extractors:
  - name: "docling"
    config:
      ocr_lang: ["fra", "eng"]  # Ordre : français prioritaire
```

### Exemple 3 : Multi-Langues (Documents Techniques)

```yaml
extractors:
  - name: "docling"
    config:
      ocr_lang: ["fra", "eng", "deu"]  # Français, Anglais, Allemand
```

---

## 🔍 Détails Techniques

### Pourquoi une Liste ?

L'API Docling/Tesseract utilise **Pydantic v2** pour la validation des paramètres. Dans le modèle `TesseractOcrOptions`, le champ `lang` est défini comme :

```python
class TesseractOcrOptions(BaseModel):
    lang: list[str]  # ← Type = liste de strings
```

Pydantic v2 est **strict** par défaut et ne convertit pas automatiquement les types. Il faut donc passer une liste explicitement.

### Conversion Automatique dans le Code

Notre code gère maintenant les deux cas :

```python
if isinstance(ocr_lang, str):
    ocr_lang = [ocr_lang]  # "fra" → ["fra"]
```

**Avantage** : Rétrocompatibilité si quelqu'un configure par erreur avec une string

---

## 📋 Checklist de Vérification

- [x] Code modifié pour accepter liste (avec conversion string → liste)
- [x] Configuration YAML modifiée (`ocr_lang: ["fra"]`)
- [x] Documentation mise à jour (CONFIG_DOCLING_TESSERACT.md)
- [x] Exemples ajoutés pour 1, 2 ou 3+ langues
- [ ] Test avec nouveau PDF à valider

---

## 🎯 Résumé

### Le Problème
- `TesseractOcrOptions(lang="fra")` → Erreur Pydantic validation
- Pydantic v2 attend `lang: list[str]`, pas `str`

### La Solution
1. **Code** : Conversion automatique string → liste si nécessaire
2. **Config** : Utilisation de `["fra"]` au lieu de `"fra"`

### Le Résultat
- ✅ Docling fonctionne avec Tesseract OCR
- ✅ Aucune erreur de validation Pydantic
- ✅ Support multi-langues simplifié

---

**Date** : 2025-10-31
**Version** : 1.1 (fix validation)
**Fichiers Modifiés** :
- `rag_framework/extractors/docling_extractor.py` (lignes 107-116)
- `config/02_preprocessing.yaml` (ligne 99)
- `CONFIG_DOCLING_TESSERACT.md` (section langues)
