# Sauvegarde des Chunks

## Vue d'ensemble

Le pipeline sauvegarde automatiquement les chunks créés à partir des documents extraits au format JSON.

**Avantages** :
- ✅ Conservation des chunks pour analyse et débogage
- ✅ Métadonnées complètes (index, fichier source, etc.)
- ✅ Format JSON facilement exploitable
- ✅ Organisation par document source ou fichier unique

## Configuration

Configuration dans `config/03_chunking.yaml` :

```yaml
output:
  save_chunks: true                      # Activer la sauvegarde des chunks
  chunks_dir: "./data/output/chunks"     # Répertoire pour fichiers JSON
  format: "json"                         # Format de sauvegarde
  group_by_document: true                # Un fichier JSON par document source
  add_timestamp: true                    # Ajouter timestamp au nom du fichier
  pretty_print: true                     # Formater le JSON (indentation)
  include_metadata: true                 # Inclure toutes les métadonnées
```

## Structure des fichiers JSON

### Mode groupé par document (`group_by_document: true`)

**Structure** :
```
data/output/chunks/
├── rapport_20251031_120651_chunks.json       # Chunks du rapport.pdf
├── guide_20251031_120652_chunks.json         # Chunks du guide.pdf
└── audit_20251031_120653_chunks.json         # Chunks de audit.docx
```

**Contenu d'un fichier** :
```json
[
  {
    "text": "Rapport d'Audit de Sécurité\n\nContexte\n\nCe rapport présente les résultats de l'audit de sécurité réalisé...",
    "source_file": "/Users/.../data/input/docs/rapport.pdf",
    "chunk_index": 0,
    "total_chunks": 166
  },
  {
    "text": "Méthodologie\n\nL'audit a été réalisé selon la norme ISO 27001 en suivant...",
    "source_file": "/Users/.../data/input/docs/rapport.pdf",
    "chunk_index": 1,
    "total_chunks": 166
  },
  {
    "text": "Résultats\n\nL'audit a révélé plusieurs vulnérabilités critiques...",
    "source_file": "/Users/.../data/input/docs/rapport.pdf",
    "chunk_index": 2,
    "total_chunks": 166
  }
  // ... 163 autres chunks
]
```

### Mode unique (`group_by_document: false`)

**Structure** :
```
data/output/chunks/
└── chunks_20251031_120651.json  # Tous les chunks de tous les documents
```

**Contenu** :
```json
[
  {
    "text": "Chunk du rapport.pdf...",
    "source_file": "/path/to/rapport.pdf",
    "chunk_index": 0,
    "total_chunks": 166
  },
  {
    "text": "Chunk du guide.pdf...",
    "source_file": "/path/to/guide.pdf",
    "chunk_index": 0,
    "total_chunks": 85
  }
  // ... tous les chunks de tous les documents
]
```

## Métadonnées des chunks

Chaque chunk contient :

| Champ | Type | Description |
|---|---|---|
| `text` | string | Texte du chunk |
| `source_file` | string | Chemin absolu du fichier source |
| `chunk_index` | int | Index du chunk dans le document (commence à 0) |
| `total_chunks` | int | Nombre total de chunks pour ce document |

## Cas d'usage

### 1. Analyser les chunks d'un document

```bash
# Lire les chunks d'un document spécifique
cat data/output/chunks/rapport_*_chunks.json | jq '.'

# Compter le nombre de chunks
cat data/output/chunks/rapport_*_chunks.json | jq 'length'

# Extraire le texte du premier chunk
cat data/output/chunks/rapport_*_chunks.json | jq '.[0].text'
```

### 2. Rechercher un mot-clé dans les chunks

```bash
# Trouver tous les chunks contenant "RGPD"
find data/output/chunks -name "*.json" -exec jq '.[] | select(.text | contains("RGPD"))' {} \;

# Compter le nombre de chunks contenant "sécurité"
find data/output/chunks -name "*.json" -exec jq '[.[] | select(.text | contains("sécurité"))] | length' {} \;
```

### 3. Statistiques sur les chunks

```bash
# Taille moyenne des chunks par document
for file in data/output/chunks/*_chunks.json; do
    echo "$(basename $file):"
    jq '[.[].text | length] | add / length' "$file"
done

# Distribution des tailles de chunks
jq '[.[].text | length] | group_by(. / 100 | floor * 100) | map({size: .[0], count: length})' \
   data/output/chunks/rapport_*_chunks.json
```

### 4. Exporter en texte brut

```python
import json
from pathlib import Path

# Lire les chunks d'un document
chunks_file = Path("data/output/chunks/rapport_20251031_120651_chunks.json")
with open(chunks_file, "r", encoding="utf-8") as f:
    chunks = json.load(f)

# Sauvegarder chaque chunk dans un fichier texte séparé
output_dir = Path("data/output/chunks_txt")
output_dir.mkdir(exist_ok=True)

for chunk in chunks:
    chunk_idx = chunk["chunk_index"]
    filename = f"chunk_{chunk_idx:03d}.txt"

    with open(output_dir / filename, "w", encoding="utf-8") as f:
        f.write(chunk["text"])

print(f"✅ {len(chunks)} chunks exportés vers {output_dir}")
```

### 5. Reconstituer le document complet

```python
import json
from pathlib import Path

# Lire les chunks
chunks_file = Path("data/output/chunks/rapport_20251031_120651_chunks.json")
with open(chunks_file, "r", encoding="utf-8") as f:
    chunks = json.load(f)

# Trier par index (normalement déjà trié)
chunks_sorted = sorted(chunks, key=lambda x: x["chunk_index"])

# Reconstituer le texte complet (attention au overlap)
# Note: cela crée des duplications dues au chunk_overlap
full_text = "\n\n".join(chunk["text"] for chunk in chunks_sorted)

# Sauvegarder
output_file = Path("data/output/rapport_reconstruit.txt")
output_file.write_text(full_text, encoding="utf-8")

print(f"✅ Document reconstitué: {output_file}")
print(f"   {len(full_text)} caractères")
```

## Logs

**Sauvegarde réussie (mode groupé)** :
```
INFO: Chunking: 166 chunks créés depuis 1 documents
INFO: 💾 Chunks sauvegardés: rapport_20251031_120651_chunks.json (166 chunks)
```

**Sauvegarde réussie (mode unique)** :
```
INFO: Chunking: 251 chunks créés depuis 3 documents
INFO: 💾 Chunks sauvegardés: chunks_20251031_120651.json (251 chunks)
```

**Erreur de sauvegarde** :
```
ERROR: Erreur sauvegarde chunks JSON: Permission denied
```
Note: En cas d'erreur, le pipeline continue (la sauvegarde n'est pas bloquante).

## Options de configuration

### Désactiver la sauvegarde

```yaml
output:
  save_chunks: false  # Aucun fichier JSON créé
```

### Sauvegarde unique pour tous les documents

```yaml
output:
  save_chunks: true
  group_by_document: false  # Un seul fichier pour tous les chunks
  add_timestamp: true
```

### Sauvegarde compacte (sans indentation)

```yaml
output:
  save_chunks: true
  pretty_print: false  # JSON compact (économise de l'espace)
```

### Sauvegarde avec noms de fichiers sans timestamp

```yaml
output:
  save_chunks: true
  add_timestamp: false  # Noms de fichiers sans timestamp
  # Attention: risque d'écrasement si même document retraité
```

## Stratégies de chunking

Le découpage en chunks affecte la structure des fichiers JSON :

### Stratégie "recursive" (recommandée)

```yaml
strategy: "recursive"
recursive:
  chunk_size: 1000      # Chunks de ~1000 caractères
  chunk_overlap: 200    # Overlap de 200 caractères
```

**Résultat** :
- Chunks de taille variable (~800-1200 caractères)
- Découpage intelligent sur paragraphes/lignes
- Chevauchement pour préserver le contexte

**Exemple** :
```
Document de 132808 chars → 166 chunks
Taille moyenne: 800 chars/chunk
Taille min: 500 chars
Taille max: 1200 chars
```

### Stratégie "fixed"

```yaml
strategy: "fixed"
fixed:
  chunk_size: 1000
  overlap: 200
```

**Résultat** :
- Chunks de taille exacte (1000 caractères)
- Découpage sur position fixe (peut couper au milieu d'un mot)
- Plus rapide mais moins intelligent

## Performance

**Impact sur les performances** :
- Sauvegarde rapide (~5-10ms par fichier JSON)
- Espace disque : ~5-10% de la taille des documents originaux
- Mode groupé : plus de fichiers mais plus facile à naviguer
- Mode unique : un seul fichier mais plus gros

**Exemple de tailles** :
```
Document PDF : 2 MB
→ Texte extrait JSON : 200 KB
→ Chunks JSON : 220 KB (166 chunks)
```

## Intégration avec les étapes suivantes

Les chunks JSON peuvent être utilisés par :

**Étape 4 (Enrichment)** : Enrichir les chunks avec métadonnées
**Étape 6 (Embedding)** : Créer embeddings depuis les chunks JSON
**Étape 8 (Vector Storage)** : Stocker les chunks dans la base vectorielle

## Désactivation temporaire

**Via configuration** :
```yaml
output:
  save_chunks: false
```

**Relancer le pipeline** :
```bash
./start.sh
```

## Résumé

La sauvegarde des chunks permet de :

1. ✅ **Conserver** les chunks pour analyse et débogage
2. ✅ **Tracer** la structure du découpage
3. ✅ **Explorer** facilement avec outils JSON (jq, Python)
4. ✅ **Optimiser** le chunking en analysant les résultats
5. ✅ **Auditer** le traitement avec métadonnées complètes

**Configuration recommandée** :
```yaml
output:
  save_chunks: true
  group_by_document: true    # Un fichier par document
  add_timestamp: true        # Évite les écrasements
  pretty_print: true         # Lisible pour débogage
```

**Commandes utiles** :
```bash
# Vérifier les chunks créés
ls -lh data/output/chunks/

# Lire les chunks d'un document
jq '.' data/output/chunks/rapport_*_chunks.json | less

# Compter les chunks par document
find data/output/chunks -name "*_chunks.json" -exec sh -c 'echo "$1: $(jq length "$1") chunks"' _ {} \;
```
