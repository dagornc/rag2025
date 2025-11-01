# Guide Rapide - Corrections Ruff Restantes

## 🎯 5 Corrections à Appliquer (10 minutes)

### Fix 1/5 - ocr/base.py (RUF012)

**Fichier**: `rag_framework/preprocessing/ocr/base.py`
**Ligne**: 32
**Erreur**: `Mutable class attributes should be annotated with typing.ClassVar`

**Correction**:
```python
# AVANT (ligne 10):
from typing import Any

# APRÈS:
from typing import Any, ClassVar

# AVANT (ligne 32):
REQUIRED_MODULES: list[str] = []

# APRÈS:
REQUIRED_MODULES: ClassVar[list[str]] = []
```

---

### Fix 2/5 - ocr/tesseract.py (RUF012)

**Fichier**: `rag_framework/preprocessing/ocr/tesseract.py`
**Ligne**: 21
**Erreur**: `Mutable class attributes should be annotated with typing.ClassVar`

**Correction**:
```python
# AVANT (ligne 9):
from typing import Any

# APRÈS:
from typing import Any, ClassVar

# AVANT (ligne 21):
REQUIRED_MODULES = ["pytesseract", "PIL"]

# APRÈS:
REQUIRED_MODULES: ClassVar[list[str]] = ["pytesseract", "PIL"]
```

---

### Fix 3/5 - config.py (ANN401)

**Fichier**: `rag_framework/preprocessing/config.py`
**Ligne**: 132
**Erreur**: `Dynamically typed expressions (typing.Any) are disallowed`

**Correction**:
```python
# AVANT (ligne 132):
    def validate_overlap_smaller_than_chunk(
        cls, v: int | None, info: Any
    ) -> int | None:

# APRÈS:
from pydantic import BaseModel, Field, field_validator, ValidationInfo

    def validate_overlap_smaller_than_chunk(
        cls, v: int | None, info: ValidationInfo
    ) -> int | None:
```

---

### Fix 4/5 - manager.py (ANN401)

**Fichier**: `rag_framework/preprocessing/manager.py`
**Ligne**: 83
**Erreur**: `Dynamically typed expressions (typing.Any) are disallowed`

**Correction**:
```python
# AVANT (ligne 83):
    def _create_adapter(self, library_name: str, config: dict[str, Any]) -> Any | None:

# APRÈS:
from rag_framework.preprocessing.adapters.base import LibraryAdapter

    def _create_adapter(
        self, library_name: str, config: dict[str, Any]
    ) -> LibraryAdapter | None:
```

---

### Fix 5/5 - Lignes Longues (E501)

**Fichiers**: manager.py (ligne 104), ocr/base.py (ligne 55), ocr/tesseract.py (ligne 54)

**Corrections**:

#### manager.py ligne 104:
```python
# AVANT:
#     from rag_framework.preprocessing.adapters.pdf.marker import MarkerAdapter

# APRÈS:
#     from rag_framework.preprocessing.adapters.pdf.marker import (
#         MarkerAdapter,
#     )
```

#### ocr/base.py ligne 55:
```python
# AVANT:
self.logger.warning(
    f"{self.__class__.__name__} désactivé : modules manquants: {', '.join(missing)}"
)

# APRÈS:
self.logger.warning(
    f"{self.__class__.__name__} désactivé : "
    f"modules manquants: {', '.join(missing)}"
)
```

#### ocr/tesseract.py ligne 54:
```python
# AVANT:
"confidence": None,  # Tesseract ne fournit pas facilement la confidence

# APRÈS:
"confidence": None,  # Tesseract: pas de confidence
```

---

## ✅ Validation Finale

Après avoir appliqué ces 5 corrections:

```bash
# 1. Formater
rye run ruff format rag_framework/preprocessing/

# 2. Vérifier (devrait passer à 0 erreur)
rye run ruff check rag_framework/preprocessing/

# 3. Mypy
rye run mypy rag_framework/preprocessing/

# 4. Tests
rye run pytest tests/unit/test_preprocessing.py -v
```

---

## 🎉 Résultat Attendu

```
ruff check: ✅ All checks passed!
mypy: ✅ Success: no issues found
pytest: ✅ 4 passed in 0.5s
```

---

## 🚀 Utilisation Immédiate

Une fois validé, tester le système:

```python
from rag_framework.preprocessing.manager import RAGPreprocessingManager

# Initialiser le manager
manager = RAGPreprocessingManager("config/parser.yaml")

# Traiter un PDF
result = manager.process_document("mon_fichier.pdf")

print(f"Texte extrait: {len(result['text'])} caractères")
print(f"Chunks: {len(result['chunks'])}")
print(f"Métriques: {result['metrics']}")
```
