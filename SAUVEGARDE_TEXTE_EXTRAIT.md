# Sauvegarde du Texte Extrait

## Vue d'ensemble

Le pipeline sauvegarde automatiquement le texte extrait de chaque document au format JSON avec toutes les métadonnées.

**Avantages** :
- ✅ Conservation du texte extrait pour analyse ultérieure
- ✅ Métadonnées complètes (méthode d'extraction, confidence score, etc.)
- ✅ Format JSON facilement exploitable (parsing, recherche, etc.)
- ✅ Traçabilité complète du traitement

## Configuration

Configuration dans `config/01_monitoring.yaml` :

```yaml
output:
  save_extracted_text: true           # Activer la sauvegarde du texte extrait
  extracted_dir: "./data/output/extracted"  # Répertoire pour fichiers JSON
  preserve_structure: true            # Préserver la structure des sous-répertoires
  add_timestamp: true                 # Ajouter timestamp au nom du fichier JSON
  include_metadata: true              # Inclure métadonnées complètes
  pretty_print: true                  # Formater le JSON (indentation)
```

## Structure des fichiers JSON

### Exemple complet (avec métadonnées)

**Fichier** : `data/output/extracted/rapport_20251031_143022.json`

```json
{
  "file_path": "/Users/cdagorn/Projets_Python/rag/data/input/docs/rapport.pdf",
  "text": "Rapport d'Audit de Sécurité\n\nContexte : Ce rapport présente...",
  "original_length": 12543,
  "cleaned_length": 12234,
  "extraction_method": "pymupdf",
  "confidence_score": 0.95,
  "metadata": {
    "pages": 15,
    "author": "ANSSI",
    "creation_date": "2024-10-15"
  },
  "extractor_used": "pymupdf",
  "confidence": 0.95,
  "extracted_json_path": "/Users/cdagorn/Projets_Python/rag/data/output/extracted/rapport_20251031_143022.json",
  "original_file_path": "/Users/cdagorn/Projets_Python/rag/data/input/docs/rapport.pdf",
  "processed_file_path": "/Users/cdagorn/Projets_Python/rag/data/output/processed/rapport_20251031_143022.pdf"
}
```

### Exemple simplifié (sans métadonnées)

**Configuration** :
```yaml
output:
  include_metadata: false
```

**Fichier JSON** :
```json
{
  "file_path": "/path/to/rapport.pdf",
  "text": "Contenu du document extrait..."
}
```

## Organisation des fichiers

### Avec préservation de structure (`preserve_structure: true`)

**Avant** :
```
data/input/
├── compliance_docs/
│   └── rgpd/
│       └── rapport.pdf
└── audit_reports/
    └── audit.docx
```

**Après traitement** :
```
data/output/extracted/
├── compliance_docs/
│   └── rgpd/
│       └── rapport_20251031_143022.json
└── audit_reports/
    └── audit_20251031_143025.json

data/output/processed/
├── compliance_docs/
│   └── rgpd/
│       └── rapport_20251031_143022.pdf
└── audit_reports/
    └── audit_20251031_143025.docx
```

### Sans préservation de structure (`preserve_structure: false`)

**Après traitement** :
```
data/output/extracted/
├── rapport_20251031_143022.json
└── audit_20251031_143025.json

data/output/processed/
├── rapport_20251031_143022.pdf
└── audit_20251031_143025.docx
```

## Contenu des métadonnées

Les fichiers JSON contiennent :

| Champ | Type | Description |
|---|---|---|
| `file_path` | string | Chemin absolu du fichier source |
| `text` | string | Texte extrait et nettoyé |
| `original_length` | int | Longueur du texte brut (avant nettoyage) |
| `cleaned_length` | int | Longueur du texte nettoyé |
| `extraction_method` | string | Méthode utilisée (pymupdf, docling, etc.) |
| `confidence_score` | float | Score de confiance (0.0 à 1.0) |
| `metadata` | object | Métadonnées spécifiques au format (pages, auteur, etc.) |
| `extractor_used` | string | Nom de l'extracteur utilisé |
| `confidence` | float | Duplication du confidence_score |
| `extracted_json_path` | string | Chemin du fichier JSON créé |
| `original_file_path` | string | Chemin du fichier source avant déplacement |
| `processed_file_path` | string | Chemin du fichier après déplacement vers processed |

## Cas d'usage

### 1. Analyse et recherche

**Objectif** : Rechercher des mots-clés dans tous les documents extraits.

```bash
# Rechercher "RGPD" dans tous les JSON
grep -r "RGPD" data/output/extracted/

# Ou avec jq pour une recherche JSON structurée
find data/output/extracted -name "*.json" -exec jq 'select(.text | contains("RGPD"))' {} \;
```

### 2. Statistiques d'extraction

**Objectif** : Analyser la qualité de l'extraction.

```bash
# Compter les documents par méthode d'extraction
find data/output/extracted -name "*.json" -exec jq -r '.extraction_method' {} \; | sort | uniq -c

# Calculer la moyenne des confidence scores
find data/output/extracted -name "*.json" -exec jq -r '.confidence_score' {} \; | awk '{sum+=$1; n++} END {print sum/n}'
```

### 3. Reconstruction du texte

**Objectif** : Reconstruire le texte complet d'un document.

```python
import json
from pathlib import Path

json_file = Path("data/output/extracted/rapport_20251031_143022.json")
with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Document: {data['file_path']}")
print(f"Méthode: {data['extraction_method']}")
print(f"Confidence: {data['confidence_score']}")
print(f"\nTexte extrait ({data['cleaned_length']} chars):\n")
print(data['text'])
```

### 4. Export vers autre format

**Objectif** : Convertir les JSON en fichiers TXT.

```bash
# Script pour extraire uniquement le texte
for json_file in data/output/extracted/**/*.json; do
    txt_file="${json_file%.json}.txt"
    jq -r '.text' "$json_file" > "$txt_file"
done
```

## Logs

**Sauvegarde réussie** :
```
INFO: ✓ Document extrait: rapport.pdf (méthode: pymupdf, 12234 chars, confidence: 0.95)
INFO: 💾 Texte extrait sauvegardé: rapport_20251031_143022.json
DEBUG:   Chemin complet: /Users/.../data/output/extracted/rapport_20251031_143022.json
```

**Erreur de sauvegarde** :
```
ERROR: Erreur sauvegarde JSON pour rapport.pdf: Permission denied
```

## Options de configuration

### Désactiver la sauvegarde

```yaml
output:
  save_extracted_text: false  # Aucun JSON créé
```

### Sauvegarde minimale (texte uniquement)

```yaml
output:
  save_extracted_text: true
  include_metadata: false      # Seulement file_path et text
  pretty_print: false          # JSON compact (sans indentation)
```

### Sauvegarde complète avec structure plate

```yaml
output:
  save_extracted_text: true
  preserve_structure: false    # Tous les JSON dans extracted/
  add_timestamp: true
  include_metadata: true
  pretty_print: true
```

## Intégration avec les étapes suivantes

Les fichiers JSON peuvent être utilisés par les étapes ultérieures du pipeline :

**Étape 3 (Chunking)** : Charger le texte depuis JSON plutôt que ré-extraire
**Étape 4 (Enrichment)** : Utiliser les métadonnées pour enrichir
**Étape 6 (Embedding)** : Créer embeddings depuis les JSON sauvegardés

## Performance

**Impact sur les performances** :
- Sauvegarde rapide (écriture JSON = ~1-5ms par document)
- Espace disque : ~10-50% de la taille du document original (texte compressé)
- Pas d'impact sur l'extraction (sauvegarde asynchrone possible)

**Exemple** :
- PDF 2 MB → JSON 200 KB (texte + métadonnées)
- DOCX 500 KB → JSON 100 KB

## Désactivation temporaire

**Via configuration** :
```yaml
output:
  save_extracted_text: false
```

**Via variable d'environnement** :
```bash
export RAG_SAVE_EXTRACTED=false
./start.sh
```

## Résumé

La sauvegarde du texte extrait permet de :

1. ✅ **Conserver** le texte extrait pour analyse future
2. ✅ **Tracer** la méthode d'extraction et la qualité
3. ✅ **Explorer** facilement avec outils JSON (jq, Python, etc.)
4. ✅ **Optimiser** en évitant de ré-extraire les documents
5. ✅ **Auditer** le traitement avec métadonnées complètes

**Commande recommandée** :
```bash
# Configuration par défaut (activée)
./start.sh

# Vérifier les JSON créés
ls -la data/output/extracted/

# Lire un JSON
jq '.' data/output/extracted/rapport_*.json
```
