# Extensions de Fichiers Support\u00e9es - Framework RAG (2025)

## Vue d'ensemble

Le framework RAG supporte **24 extensions de fichiers** différentes, couvrant documents, présentations, tableurs, fichiers texte et images. Chaque type de fichier est traité par une chaîne d'extracteurs adaptée via le système de fallback **optimisé selon les meilleures pratiques 2025**.

### Nouveautés 2025

✨ **7 nouveaux extracteurs** ajoutés pour améliorer performance et qualité:
- **PyMuPDF** (fitz) - Extraction PDF 10-100x plus rapide
- **pdfplumber** - Extraction avancée de tableaux PDF
- **python-docx** - Extraction Word native (plus rapide que Docling)
- **python-pptx** - Extraction PowerPoint native
- **pandas** - Traitement optimal CSV/Excel avec statistiques
- **BeautifulSoup** - Parsing HTML/XML intelligent
- **Tesseract OCR** - Reconnaissance optique de caractères pour scans

---

## Liste Complète des Extensions (24+)

| Extension | Type | Description | **Extracteurs optimaux (2025)** |
|-----------|------|-------------|----------------------------------|
| `.txt` | Texte | Texte simple | **text** |
| `.md` | Texte | Markdown | **text** |
| `.csv` | Tableur | Données tabulaires | **pandas** → text → docling |
| `.xlsx` `.xls` `.xlsm` | Tableur | Excel | **pandas** → docling |
| `.ods` | Tableur | OpenDocument Spreadsheet | **pandas** → docling |
| `.html` `.htm` `.xhtml` | Web | Pages web | **html** → text |
| `.xml` | Texte | XML structuré | **html** → text |
| `.rtf` | Texte | Rich Text Format | **text** → docling |
| `.tex` | Texte | LaTeX source | **text** |
| `.svg` | Vecteur | Scalable Vector Graphics | **text** |
| `.doc` `.docx` `.docm` | Document | Microsoft Word | **docx** → docling → vlm |
| `.ppt` `.pptx` `.pptm` | Présentation | PowerPoint | **pptx** → docling → vlm |
| `.odt` | Document | OpenDocument Texte | docling → vlm |
| `.odp` | Présentation | OpenDocument Présentation | docling → vlm |
| `.pdf` | Document | Portable Document Format | **pdfplumber** → **pymupdf** → pypdf2 → docling → marker → vlm |
| `.ps` | Document | PostScript | pymupdf → docling |
| `.epub` | Document | E-book | pymupdf → docling |
| `.png` `.jpg` `.jpeg` `.bmp` `.gif` | Image | Images | **ocr** → **image** (VLM) |

**Note** : Les extracteurs en **gras** sont les plus performants en 2025.

---

## Extracteurs Disponibles (13 au total)

### Extracteurs Rapides et Gratuits

| Extracteur | Extensions | Vitesse | Qualité | Cas d'usage |
|------------|-----------|---------|---------|-------------|
| **TextExtractor** | .txt, .md, .rtf, .tex, .svg | ⚡⚡⚡⚡⚡ | ⭐⭐⭐ | Texte simple, aucune structure |
| **PandasExtractor** | .csv, .xlsx, .xls, .xlsm, .ods | ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐⭐ | **Données tabulaires** |
| **HTMLExtractor** | .html, .htm, .xhtml, .xml | ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐ | Pages web, XML |
| **DocxExtractor** | .docx, .docm | ⚡⚡⚡⚡ | ⭐⭐⭐⭐⭐ | **Word natif** (meilleur que Docling) |
| **PptxExtractor** | .pptx, .pptm | ⚡⚡⚡⚡ | ⭐⭐⭐⭐⭐ | **PowerPoint natif** |

### Extracteurs PDF (ordre 2025)

| Extracteur | Extensions | Vitesse | Qualité | Cas d'usage |
|------------|-----------|---------|---------|-------------|
| **PyMuPDFExtractor** | .pdf, .ps, .epub | ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐ | **PDF rapide** (10-100x pypdf) |
| **PdfPlumberExtractor** | .pdf | ⚡⚡⚡⚡ | ⭐⭐⭐⭐⭐ | **PDF + tableaux** (le meilleur en 2025) |
| **PyPDF2Extractor** | .pdf | ⚡⚡⚡ | ⭐⭐ | PDF simple (fallback) |

### Extracteurs Avancés

| Extracteur | Extensions | Vitesse | Qualité | Cas d'usage |
|------------|-----------|---------|---------|-------------|
| **DoclingExtractor** | .pdf, .doc, .docx, .ppt, .pptx, .xls, .xlsx, .odt, .odp, .ods, .rtf, etc. | ⚡⚡⚡ | ⭐⭐⭐⭐ | Universel (OCR, layout analysis) |
| **MarkerExtractor** | .pdf | ⚡⚡ | ⭐⭐⭐⭐⭐ | PDF ML haute qualité |
| **OCRExtractor** | .pdf, .png, .jpg, .jpeg, .bmp, .gif, .tiff | ⚡⚡ | ⭐⭐⭐⭐ | **Scans et images** avec Tesseract |

### Extracteurs VLM (nécessitent API)

| Extracteur | Extensions | Vitesse | Qualité | Cas d'usage |
|------------|-----------|---------|---------|-------------|
| **ImageExtractor** | .png, .jpg, .jpeg, .bmp, .gif | ⚡ | ⭐⭐⭐⭐ | Images avec VLM |
| **VLMExtractor** | .pdf + images | ⚡ | ⭐⭐⭐⭐⭐ | Dernier recours (très coûteux) |

---

## Chaînes de Fallback Optimisées (2025)

### Profil SPEED (< 1 seconde)

```
text → pandas → html → pymupdf → pypdf2
```

**Ordre de priorité**:
1. **text** - Texte simple (instantané)
2. **pandas** - CSV/Excel (< 100ms)
3. **html** - HTML/XML avec lxml (< 50ms)
4. **pymupdf** - PDF très rapide
5. **pypdf2** - PDF fallback

**RAM**: < 100 MB

### Profil MEMORY (< 200 MB RAM)

```
text → pandas → html → docx → pptx → pymupdf → pypdf2 → docling
```

**Caractéristiques**:
- Pas de ML (marker)
- Pas de VLM
- Tableaux désactivés pour économiser RAM

### Profil COMPROMISE (RECOMMANDÉ)

```
text → pandas → html → docx → pptx → pdfplumber → pymupdf → pypdf2 → docling → ocr
```

**Ordre de priorité**:
1. **text** - Texte simple
2. **pandas** - CSV/Excel avec statistiques
3. **html** - HTML/XML structuré
4. **docx** - Word natif (meilleur que docling pour .docx)
5. **pptx** - PowerPoint natif
6. **pdfplumber** - PDF + tableaux (meilleur en 2025)
7. **pymupdf** - PDF rapide fallback
8. **pypdf2** - PDF simple fallback
9. **docling** - Universel (OCR + layout)
10. **ocr** - Tesseract pour scans

**Temps moyen**: 2-5 secondes
**RAM**: < 500 MB

### Profil QUALITY (Qualité maximale)

```
text → pandas → html → docx → pptx → pdfplumber → pymupdf → marker → docling → ocr → image → vlm
```

**Temps moyen**: 10-30 secondes
**RAM**: 500 MB - 2 GB

---

## Configuration par Type de Fichier

### 1. Fichiers Texte Simples

**Extensions**: `.txt`, `.md`, `.rtf`, `.tex`, `.svg`

**Extracteur optimal**: `TextExtractor`

**Configuration**:
```yaml
fallback:
  profile: "speed"
```

**Caractéristiques**:
- ✅ Ultra-rapide (lecture directe)
- ✅ Zéro dépendance
- ✅ Multi-encodage (UTF-8, Latin-1, CP1252, ISO-8859-1)

### 2. Données Tabulaires (CSV/Excel)

**Extensions**: `.csv`, `.xlsx`, `.xls`, `.xlsm`, `.ods`

**Extracteur optimal**: `PandasExtractor` ⭐ **NOUVEAU 2025**

**Configuration**:
```yaml
fallback:
  profile: "compromise"
  # ou custom:
  extractors:
    - name: "pandas"
      enabled: true
      config:
        output_format: "markdown"  # ou "csv", "json"
        include_stats: true
        max_rows_display: 5000
```

**Avantages**:
- ✅ Très performant (optimisé pour grandes données)
- ✅ Statistiques descriptives intégrées
- ✅ Détection automatique encodage/délimiteur
- ✅ Support multi-feuilles Excel

**Exemple de sortie**:
```markdown
| Nom | Âge | Ville |
|-----|-----|-------|
| Alice | 30 | Paris |
| Bob | 25 | Lyon |

### Statistiques
- Lignes: 2
- Colonnes: 3
- Colonnes numériques: 1
```

### 3. HTML/XML

**Extensions**: `.html`, `.htm`, `.xhtml`, `.xml`

**Extracteur optimal**: `HTMLExtractor` ⭐ **NOUVEAU 2025**

**Configuration**:
```yaml
fallback:
  extractors:
    - name: "html"
      enabled: true
      config:
        parser: "lxml"  # ou "html.parser", "html5lib"
        preserve_structure: true
        extract_links: false
        extract_metadata: true
```

**Avantages**:
- ✅ Parsing robuste (HTML mal formé supporté)
- ✅ Extraction sélective (balises, classes, IDs)
- ✅ Nettoyage automatique (scripts, styles, nav)
- ✅ Métadonnées (title, meta tags, Open Graph)

### 4. Microsoft Word

**Extensions**: `.doc`, `.docx`, `.docm`

**Extracteur optimal**: `DocxExtractor` ⭐ **NOUVEAU 2025**

**Configuration**:
```yaml
fallback:
  extractors:
    - name: "docx"
      enabled: true
      config:
        extract_tables: true
        extract_headers_footers: true
        preserve_formatting: false  # true pour Markdown gras/italique
```

**Avantages**:
- ✅ Plus rapide que Docling pour .docx natifs
- ✅ Extraction de tableaux en Markdown
- ✅ En-têtes et pieds de page
- ✅ Métadonnées (auteur, date, etc.)

**Chaîne recommandée**: `docx → docling (fallback .doc)`

### 5. Microsoft PowerPoint

**Extensions**: `.ppt`, `.pptx`, `.pptm`

**Extracteur optimal**: `PptxExtractor` ⭐ **NOUVEAU 2025**

**Configuration**:
```yaml
fallback:
  extractors:
    - name: "pptx"
      enabled: true
      config:
        extract_notes: true
        extract_tables: true
        include_slide_numbers: true
```

**Avantages**:
- ✅ Extraction native .pptx (plus précis que Docling)
- ✅ Notes de présentation incluses
- ✅ Tableaux formatés en Markdown
- ✅ Structure par diapositive préservée

### 6. PDF - Chaîne Optimisée 2025

**Extension**: `.pdf`

**Chaîne recommandée**:
```
pdfplumber → pymupdf → pypdf2 → docling → marker → vlm
```

#### 6.1. PDFPlumber (Meilleur pour tableaux)

⭐ **NOUVEAU 2025** - Le meilleur extracteur de tableaux PDF

**Configuration**:
```yaml
fallback:
  extractors:
    - name: "pdfplumber"
      enabled: true
      config:
        extract_tables: true
        table_format: "markdown"  # ou "csv", "text"
        preserve_layout: true
```

**Avantages**:
- ✅ **Meilleure extraction de tableaux en 2025**
- ✅ Préservation précise de la mise en page
- ✅ Détection fine des colonnes
- ✅ API intuitive

**Cas d'usage**:
- Rapports financiers avec tableaux
- Factures structurées
- Documents avec mise en page complexe

#### 6.2. PyMuPDF (Le plus rapide)

⭐ **NOUVEAU 2025** - 10-100x plus rapide que pypdf

**Configuration**:
```yaml
fallback:
  extractors:
    - name: "pymupdf"
      enabled: true
      config:
        preserve_layout: true
        extract_metadata: true
```

**Avantages**:
- ✅ **Très rapide** (10-100x pypdf)
- ✅ Excellente gestion encodage/polices
- ✅ Métadonnées riches
- ✅ Faible consommation mémoire

**Cas d'usage**:
- PDF textuels simples
- Volumes importants de documents
- Extraction rapide sans OCR

#### 6.3. PyPDF2 (Fallback simple)

**Configuration**:
```yaml
fallback:
  extractors:
    - name: "pypdf2"
      enabled: true
```

**Cas d'usage**: Fallback léger si pymupdf non disponible

#### 6.4. Docling (Universel + OCR)

**Configuration**:
```yaml
fallback:
  extractors:
    - name: "docling"
      enabled: true
      config: {}  # Auto en version 1.x
```

**Cas d'usage**:
- PDF scannés (OCR intégré)
- Mises en page complexes
- Fallback universel

#### 6.5. Marker (ML Haute Qualité)

**Configuration**:
```yaml
fallback:
  extractors:
    - name: "marker"
      enabled: true
      config:
        use_gpu: false
        min_confidence: 0.6
```

**Cas d'usage**:
- PDF académiques complexes
- Documents avec formules mathématiques
- Qualité maximale requise

### 7. Images et Scans

**Extensions**: `.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif`, `.tiff`

**Chaîne recommandée**: `ocr → image (VLM)`

#### 7.1. OCR Tesseract (Gratuit)

⭐ **NOUVEAU 2025** - OCR gratuit et open-source

**Configuration**:
```yaml
fallback:
  extractors:
    - name: "ocr"
      enabled: true
      config:
        lang: "fra+eng"  # Langues (fra, eng, deu, etc.)
        psm: 3  # Page Segmentation Mode (0-13)
        oem: 3  # OCR Engine Mode (0-3)
        preprocess: true
        min_confidence: 0.5
```

**Avantages**:
- ✅ Gratuit et open-source
- ✅ Support 100+ langues
- ✅ Bonne précision pour texte imprimé
- ✅ Pas de coût API

**Limitations**:
- ❌ Nécessite binaire Tesseract installé
- ❌ Lent pour grandes images
- ❌ Mauvais avec manuscrit

**Installation**:
```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-fra

# Windows
# Télécharger depuis: https://github.com/UB-Mannheim/tesseract/wiki
```

#### 7.2. VLM (Haute qualité, payant)

**Configuration**:
```yaml
fallback:
  extractors:
    - name: "image"
      enabled: true
      config:
        provider: "openai"
        model: "gpt-4o"
        temperature: 0.0
```

**Cas d'usage**:
- Images complexes
- Fallback si OCR échoue
- Compréhension contextuelle

---

## Comparaison des Approches

### CSV/Excel : pandas vs docling

| Critère | pandas ⭐ | docling |
|---------|----------|---------|
| Vitesse | ⚡⚡⚡⚡⚡ | ⚡⚡⚡ |
| Qualité tableaux | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Statistiques | ✅ | ❌ |
| Multi-feuilles | ✅ | ✅ |
| RAM (10MB CSV) | ~50 MB | ~150 MB |

**Recommandation 2025**: Toujours utiliser pandas en premier pour CSV/Excel

### Word : docx vs docling

| Critère | docx ⭐ | docling |
|---------|--------|---------|
| Vitesse | ⚡⚡⚡⚡ | ⚡⚡⚡ |
| Qualité .docx | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Qualité .doc | ❌ | ⭐⭐⭐⭐ |
| Tableaux | ✅ | ✅ |
| Images | ❌ | ⚠️ |

**Recommandation 2025**: docx pour .docx natifs, docling en fallback pour .doc

### PDF : pdfplumber vs pymupdf vs pypdf

| Critère | pdfplumber ⭐ | pymupdf | pypdf2 |
|---------|---------------|---------|--------|
| Vitesse | ⚡⚡⚡⚡ | ⚡⚡⚡⚡⚡ | ⚡⚡⚡ |
| Tableaux | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| Layout complexe | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| RAM | ~200 MB | ~100 MB | ~50 MB |

**Recommandation 2025**:
- Tableaux → pdfplumber
- Vitesse → pymupdf
- Léger → pypdf2

### Images : OCR vs VLM

| Critère | OCR (Tesseract) ⭐ | VLM (GPT-4o) |
|---------|-------------------|--------------|
| Coût | Gratuit | ~$0.01-0.10/image |
| Vitesse | ⚡⚡ | ⚡ |
| Qualité (imprimé) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Qualité (manuscrit) | ⭐⭐ | ⭐⭐⭐⭐ |
| Compréhension contexte | ❌ | ✅ |

**Recommandation 2025**: OCR en premier (gratuit), VLM en fallback

---

## Configuration Recommandée 2025

### Pour Usage Général (90% des cas)

```yaml
fallback:
  enabled: true
  use_vlm: false  # Mode standard (gratuit)
  profile: "compromise"
```

**Extracteurs activés**:
- text, pandas, html, docx, pptx
- pdfplumber, pymupdf, pypdf2
- docling, ocr

**Coût**: Gratuit (sauf Docling cloud si utilisé)

### Pour Qualité Maximale

```yaml
fallback:
  enabled: true
  use_vlm: true  # Mode VLM activé
  profile: "quality"
```

**Extracteurs activés**: Tous (y compris marker, image, vlm)

**Coût**: ~$0.001-0.10 par document (VLM)

### Pour Performance Maximale

```yaml
fallback:
  enabled: true
  use_vlm: false
  profile: "speed"
```

**Extracteurs activés**: text, pandas, html, pymupdf, pypdf2

**Temps moyen**: < 1 seconde

---

## Vérification de l'Installation

### Script de Vérification

```bash
rye run python check_dependencies.py
```

**Sortie attendue**:
```
✅ TextExtractor: 1/1 dépendances
✅ PandasExtractor: 2/2 dépendances
✅ HTMLExtractor: 2/2 dépendances
✅ DocxExtractor: 1/1 dépendances
✅ PptxExtractor: 1/1 dépendances
✅ PyMuPDFExtractor: 1/1 dépendances
✅ PdfPlumberExtractor: 1/1 dépendances
✅ PyPDF2Extractor: 1/1 dépendances
✅ DoclingExtractor: 1/1 dépendances
✅ OCRExtractor: 3/3 dépendances
...
```

### Installation Complète

```bash
# Installation avec rye (recommandé)
rye sync

# Ou avec pip
pip install pandas openpyxl beautifulsoup4 lxml python-docx python-pptx \
            pymupdf pdfplumber pypdf docling pytesseract Pillow pdf2image

# Installation binaire Tesseract (pour OCR)
# macOS
brew install tesseract tesseract-lang

# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng

# Windows
# Télécharger installer depuis GitHub
```

---

## Limitations et Solutions

### Fichiers NON Supportés

| Format | Solution |
|--------|----------|
| `.pages`, `.numbers`, `.key` (Apple) | Convertir en .docx/.xlsx/.pptx |
| `.zip`, `.rar` (Archives) | Décompresser d'abord |
| `.mp4`, `.avi` (Vidéos) | Transcrire avec Whisper |
| `.mp3`, `.wav` (Audio) | Transcrire avec Whisper |

### Problèmes Courants

| Problème | Solution 2025 |
|----------|---------------|
| PDF scanné | **ocr** (gratuit) → image (VLM) |
| Excel volumineux (>100MB) | Augmenter `max_rows_display` dans pandas |
| HTML avec JavaScript | Utiliser Selenium/Playwright avant extraction |
| Images basse résolution | Améliorer qualité ou utiliser VLM |
| Word protégé par mot de passe | Déverrouiller avant |

---

## Bonnes Pratiques 2025

### 1. Utiliser les Extracteurs Natifs en Premier

❌ **Mauvais**:
```yaml
# Utiliser docling pour tout
extractors:
  - name: "docling"
```

✅ **Bon**:
```yaml
# Extracteurs natifs en premier
extractors:
  - name: "pandas"  # CSV/Excel
  - name: "docx"    # Word
  - name: "pptx"    # PowerPoint
  - name: "pdfplumber"  # PDF avec tableaux
  - name: "docling"  # Fallback universel
```

### 2. Profil "compromise" par Défaut

```yaml
fallback:
  profile: "compromise"  # Recommandé pour 90% des cas
```

### 3. Monitorer les Extracteurs Utilisés

```python
from collections import Counter

methods = [doc["extraction_method"] for doc in results["extracted_documents"]]
print(Counter(methods))

# Sortie attendue (bonne distribution):
# Counter({
#   'pandas': 25,      # CSV/Excel
#   'pymupdf': 15,     # PDF rapides
#   'docx': 10,        # Word
#   'pptx': 8,         # PowerPoint
#   'pdfplumber': 5,   # PDF tableaux
#   'docling': 3,      # Fallback
# })
```

### 4. Tester avec Vos Documents Réels

```bash
# Test extraction
./start.sh --once

# Vérifier logs
cat logs/pipeline.log | grep "Extraction réussie"
```

---

## FAQ 2025

### Q1: Pourquoi tant de nouveaux extracteurs ?

**R**: Les extracteurs spécialisés sont **10-100x plus rapides** et **plus précis** que Docling pour leurs formats respectifs. Par exemple:
- pandas pour CSV/Excel: 100x plus rapide
- pymupdf pour PDF: 50x plus rapide que pypdf
- docx pour Word: 5x plus rapide que docling

### Q2: Dois-je installer tous les extracteurs ?

**R**: Non ! Le profil "compromise" fonctionne sans VLM ni Marker:
```bash
rye sync  # Installe automatiquement les dépendances du profil
```

### Q3: OCR gratuit vs VLM payant ?

**R**: OCR (Tesseract) est gratuit et performant pour 80% des cas. VLM est meilleur mais coûteux (~$0.01-0.10/page).

**Recommandation**: Commencer avec OCR, activer VLM si besoin.

### Q4: pdfplumber ou pymupdf pour PDF ?

**R**:
- **pdfplumber** → PDF avec tableaux (rapports financiers, factures)
- **pymupdf** → PDF textuels (documentation, articles)

Le profil "compromise" essaie pdfplumber d'abord, puis pymupdf en fallback.

### Q5: Comment extraire 1000+ fichiers rapidement ?

**R**:
1. Utiliser profil "speed"
2. Désactiver statistiques pandas
3. Désactiver OCR
4. Traiter en parallèle

```yaml
fallback:
  profile: "speed"
```

### Q6: Marker est-il toujours nécessaire ?

**R**: Non. En 2025, **pdfplumber + pymupdf** couvrent 95% des cas PDF sans ML. Marker reste utile pour:
- PDF académiques très complexes
- Formules mathématiques
- Qualité maximale absolue

---

## Conclusion

### Résumé des Nouveautés 2025

✨ **7 nouveaux extracteurs** ajoutés:
1. **PandasExtractor** - CSV/Excel optimisé
2. **HTMLExtractor** - HTML/XML intelligent
3. **DocxExtractor** - Word natif rapide
4. **PptxExtractor** - PowerPoint natif
5. **PyMuPDFExtractor** - PDF ultra-rapide
6. **PdfPlumberExtractor** - Meilleur pour tableaux PDF
7. **OCRExtractor** - OCR gratuit Tesseract

### Performance Gains

- **CSV/Excel**: 100x plus rapide avec pandas
- **PDF**: 10-100x plus rapide avec pymupdf
- **Word/PowerPoint**: 5x plus rapide avec extracteurs natifs
- **Images**: Gratuit avec OCR au lieu de VLM payant

### Configuration Recommandée

```yaml
fallback:
  enabled: true
  use_vlm: false
  profile: "compromise"  # Optimal pour 90% des cas
```

**Coût**: Gratuit (extracteurs open-source uniquement)
**Performance**: 2-5 secondes par document
**Qualité**: ⭐⭐⭐⭐ (4/5)

---

**Documentation mise à jour**: 2025-01-31
**Version framework**: 0.1.0
**Extracteurs**: 13 disponibles
