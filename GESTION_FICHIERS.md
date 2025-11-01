# Gestion Automatique des Fichiers Traités

## Vue d'ensemble

Les fichiers traités sont automatiquement gérés :
- ✅ **Succès** → `data/output/processed/` (fichier original)
- ✅ **Texte extrait** → `data/output/extracted/` (JSON avec métadonnées)
- ✅ **Chunks** → `data/output/chunks/` (JSON des chunks créés)
- ❌ **Erreur** → `data/output/errors/`

## Configuration (`config/01_monitoring.yaml`)

```yaml
# Déplacement des fichiers traités
file_management:
  enabled: true                       # Activer le déplacement
  move_processed: true                # Déplacer les succès
  move_errors: true                   # Déplacer les erreurs
  processed_dir: "./data/output/processed" # Répertoire succès
  errors_dir: "./data/output/errors"       # Répertoire erreurs
  preserve_structure: true            # Garder sous-répertoires
  add_timestamp: true                 # Ajouter horodatage

# Sauvegarde du texte extrait
output:
  save_extracted_text: true           # Activer sauvegarde JSON
  extracted_dir: "./data/output/extracted"  # Répertoire JSON
  preserve_structure: true            # Garder sous-répertoires
  add_timestamp: true                 # Ajouter horodatage
  include_metadata: true              # Inclure métadonnées
  pretty_print: true                  # JSON indenté
```

## Comportement

### Extraction Réussie
```
data/input/docs/rapport.pdf
  → Extraction OK (étape 2)
  → data/output/processed/docs/rapport_20250131_143022.pdf (fichier original)
  → data/output/extracted/docs/rapport_20250131_143022.json (texte + métadonnées)

  → Chunking OK (étape 3)
  → data/output/chunks/rapport_20250131_143022_chunks.json (166 chunks)
```

**Contenu du JSON extrait** :
```json
{
  "file_path": "/path/to/rapport.pdf",
  "text": "Contenu du document...",
  "extraction_method": "pymupdf",
  "confidence_score": 0.95,
  "cleaned_length": 12234,
  "metadata": {...}
}
```

**Contenu du JSON chunks** :
```json
[
  {
    "text": "Premier chunk de texte...",
    "source_file": "/path/to/rapport.pdf",
    "chunk_index": 0,
    "total_chunks": 166
  },
  {
    "text": "Deuxième chunk de texte...",
    "source_file": "/path/to/rapport.pdf",
    "chunk_index": 1,
    "total_chunks": 166
  }
  // ... 164 autres chunks
]
```

### Extraction Échouée
```
data/input/docs/corrupt.pdf
  → Extraction FAIL
  → output/errors/docs/corrupt_20250131_143035.pdf
  → output/errors/docs/corrupt_20250131_143035.pdf.error
```

### Texte Trop Court
```
data/input/docs/empty.pdf
  → Texte < min_length
  → output/errors/docs/empty_20250131_143040.pdf
```

## Structure avec `preserve_structure: true`

**Avant**:
```
data/input/
├── compliance_docs/rgpd/rapport.pdf
└── audit_reports/audit.docx
```

**Après (succès)**:
```
output/processed/
├── compliance_docs/rgpd/rapport_20250131_143022.pdf
└── audit_reports/audit_20250131_143025.docx
```

## Fichiers Créés/Modifiés

### Nouveau
- `rag_framework/utils/file_manager.py` - Classe FileManager

### Modifiés
- `config/01_monitoring.yaml` - Section file_management
- `rag_framework/steps/step_02_preprocessing.py` - Intégration FileManager
- `rag_framework/pipeline.py` - Transfert config

## Activation

```bash
# 1. Configuration déjà activée par défaut

# 2. Créer répertoires output
mkdir -p output/processed output/errors

# 3. Lancer le pipeline
./start.sh --once
```

## Logs

**Succès**:
```
INFO: ✓ Document extrait: rapport.pdf (méthode: pymupdf, 5432 chars, confidence: 0.95)
INFO: 💾 Texte extrait sauvegardé: rapport_20251031_143022.json
INFO: ✓ Fichier déplacé vers processed: rapport.pdf
INFO: Chunking: 166 chunks créés depuis 1 documents
INFO: 💾 Chunks sauvegardés: rapport_20251031_143022_chunks.json (166 chunks)
```

**Erreur**:
```
ERROR: ✗ Erreur extraction corrupt.pdf: Invalid PDF
WARNING: ✗ Fichier déplacé vers errors: corrupt.pdf
```

## Désactivation

```yaml
file_management:
  enabled: false  # Fichiers restent dans data/input/
```
