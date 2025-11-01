# Guide des Profils de Fallback pour l'Extraction de Documents

## Vue d'ensemble

Le système de fallback du preprocessing (étape 2) supporte **5 profils prédéfinis** qui optimisent automatiquement la chaîne d'extraction selon vos besoins :

- 🚀 **speed** : Rapidité maximale
- 💾 **memory** : Utilisation mémoire minimale
- ⚖️ **compromise** : Équilibre qualité/performance
- 💎 **quality** : Qualité maximale
- 🎯 **custom** : Configuration manuelle

---

## Configuration

Dans `config/02_preprocessing.yaml` :

```yaml
fallback:
  enabled: true
  profile: "compromise"  # Choisir : speed | memory | compromise | quality | custom
```

---

## Profils Détaillés

### 1️⃣ Profil `speed` - Rapidité Maximale

**Cas d'usage :**
- Traitement de gros volumes de documents
- PDF textuels simples (rapports, contrats, articles)
- Besoin de latence minimale
- Documents générés numériquement (pas scannés)

**Extracteurs :**
```
PyPDF2 uniquement
```

**Caractéristiques :**
| Métrique | Valeur |
|----------|--------|
| RAM | ~50 MB |
| Vitesse | ⚡⚡⚡⚡⚡ (5/5) |
| Qualité | ⭐⭐ (2/5) |
| Temps moyen | 0.1-0.5s / doc |

**Limites :**
- ❌ PDF scannés (images)
- ❌ Mises en page complexes
- ❌ Tableaux structurés
- ❌ OCR

**Exemple de résultat :**
```python
{
    "extraction_method": "pypdf2",
    "confidence_score": 0.4,
    "extraction_time_seconds": 0.12
}
```

---

### 2️⃣ Profil `memory` - Utilisation Mémoire Minimale

**Cas d'usage :**
- Serveurs avec RAM limitée (< 2 GB)
- Environnements cloud avec quotas mémoire
- Containers Docker légers
- Documents variés (textuels + scannés occasionnels)

**Extracteurs :**
```
1. PyPDF2 (rapide, 50 MB)
   ↓ (si échec)
2. Docling (OCR, 200 MB) - sans ML lourd
```

**Caractéristiques :**
| Métrique | Valeur |
|----------|--------|
| RAM | ~200 MB |
| Vitesse | ⚡⚡⚡⚡ (4/5) |
| Qualité | ⭐⭐⭐ (3/5) |
| Temps moyen | 0.5-2s / doc |

**Avantages :**
- ✅ OCR pour PDF scannés
- ✅ Analyse de layout basique
- ✅ Évite Marker (modèles ML lourds)
- ✅ Bonne compatibilité

**Configuration appliquée :**
```yaml
extractors:
  - name: pypdf2
    config:
      min_text_length: 100
      min_confidence: 0.3

  - name: docling
    config:
      ocr_enabled: true
      extract_tables: false  # Désactivé pour économiser RAM
      min_confidence: 0.4
```

---

### 3️⃣ Profil `compromise` - Équilibre Optimal (DÉFAUT)

**Cas d'usage :**
- Usage général production
- Documents professionnels variés
- Budget mémoire raisonnable (< 1 GB)
- Besoin de qualité correcte sans latence excessive

**Extracteurs :**
```
1. PyPDF2 (rapide, textuels simples)
   ↓ (si échec)
2. Docling (OCR + layout + tableaux)
```

**Caractéristiques :**
| Métrique | Valeur |
|----------|--------|
| RAM | ~300 MB |
| Vitesse | ⚡⚡⚡ (3/5) |
| Qualité | ⭐⭐⭐⭐ (4/5) |
| Temps moyen | 1-3s / doc |

**Avantages :**
- ✅ OCR pour PDF scannés
- ✅ Extraction de tableaux structurés
- ✅ Analyse de layout avancée
- ✅ Bon compromis vitesse/qualité
- ✅ Recommandé pour 80% des cas

**Configuration appliquée :**
```yaml
extractors:
  - name: pypdf2
    config:
      min_text_length: 100
      min_confidence: 0.3

  - name: docling
    config:
      ocr_enabled: true
      extract_tables: true  # Tableaux activés
      min_confidence: 0.5
```

**Exemple de résultat :**
```python
{
    "extraction_method": "docling",
    "confidence_score": 0.85,
    "metadata": {
        "num_pages": 12,
        "tables_count": 3
    },
    "extraction_time_seconds": 2.3
}
```

---

### 4️⃣ Profil `quality` - Qualité Maximale

**Cas d'usage :**
- Documents critiques (contrats, dossiers médicaux)
- PDF complexes (scientifiques, techniques)
- Besoin de précision maximale
- Extraction de formules mathématiques
- Dernier recours pour documents illisibles

**Extracteurs :**
```
1. Marker (ML, haute précision)
   ↓ (si échec)
2. Docling (OCR + layout)
   ↓ (si échec)
3. VLM (Vision AI - GPT-4V, Claude 3)
```

**Caractéristiques :**
| Métrique | Valeur |
|----------|--------|
| RAM | ~2 GB (CPU) / ~6 GB (GPU) |
| Vitesse | ⚡⚡ (2/5) |
| Qualité | ⭐⭐⭐⭐⭐ (5/5) |
| Temps moyen | 5-20s / doc (CPU) |
| Coût | $0.01-0.05 / doc (VLM) |

**Avantages :**
- ✅ Modèles ML de pointe (Marker)
- ✅ Préserve structure complexe
- ✅ Gestion des équations/formules
- ✅ Fallback VLM pour documents impossibles
- ✅ Qualité proche de l'humain

**Limites :**
- ⚠️ Lent (5-20s / document)
- ⚠️ Nécessite beaucoup de RAM
- ⚠️ VLM coûte de l'argent (API)
- ⚠️ GPU recommandé pour Marker

**Configuration appliquée :**
```yaml
extractors:
  - name: marker
    config:
      use_gpu: false  # Passer à true si GPU disponible
      min_confidence: 0.6

  - name: docling
    config:
      ocr_enabled: true
      extract_tables: true
      min_confidence: 0.5

  - name: vlm
    config:
      provider: "openai"  # Ou : anthropic, ollama, etc.
      model: "gpt-4-vision-preview"
      max_pages: 10  # Limite pour éviter coûts excessifs
      min_confidence: 0.4
```

**Exemple de résultat :**
```python
{
    "extraction_method": "marker",
    "confidence_score": 0.95,
    "metadata": {
        "num_pages": 25,
        "images_extracted": 8,
        "tables_count": 5
    },
    "extraction_time_seconds": 12.4
}
```

---

### 5️⃣ Profil `custom` - Configuration Manuelle

**Cas d'usage :**
- Besoins très spécifiques
- Fine-tuning de la chaîne de fallback
- Tests et expérimentations
- Optimisation pour un type de document précis

**Configuration :**

Lorsque `profile: "custom"`, le système utilise directement la section `extractors` de votre config YAML.

**Exemple 1 : Seulement Docling (PDF scannés uniquement)**

```yaml
fallback:
  profile: "custom"
  extractors:
    - name: "docling"
      enabled: true
      config:
        ocr_enabled: true
        extract_tables: true
        min_confidence: 0.3
```

**Exemple 2 : Marker + VLM (qualité extrême, pas de PyPDF2)**

```yaml
fallback:
  profile: "custom"
  extractors:
    - name: "marker"
      enabled: true
      config:
        use_gpu: true
        max_pages: null

    - name: "vlm"
      enabled: true
      config:
        provider: "anthropic"
        model: "claude-3-opus-20240229"
        max_pages: 20
        temperature: 0.0
```

**Exemple 3 : Ordre inversé (VLM en premier)**

```yaml
fallback:
  profile: "custom"
  extractors:
    # VLM en premier (pour documents spéciaux)
    - name: "vlm"
      enabled: true
      config:
        provider: "ollama"
        model: "llava:13b"
        max_pages: 5

    # Fallback classique
    - name: "pypdf2"
      enabled: true
```

---

## Tableau Comparatif

| Profil | RAM | Vitesse | Qualité | Coût | Cas d'usage principal |
|--------|-----|---------|---------|------|----------------------|
| **speed** | 50 MB | ⚡⚡⚡⚡⚡ | ⭐⭐ | Gratuit | Gros volumes, PDF simples |
| **memory** | 200 MB | ⚡⚡⚡⚡ | ⭐⭐⭐ | Gratuit | Serveurs limités |
| **compromise** | 300 MB | ⚡⚡⚡ | ⭐⭐⭐⭐ | Gratuit | Usage général (défaut) |
| **quality** | 2 GB | ⚡⚡ | ⭐⭐⭐⭐⭐ | $0.01-0.05 / doc | Documents critiques |
| **custom** | Variable | Variable | Variable | Variable | Besoins spécifiques |

---

## Arbre de Décision

```
Quel est votre besoin principal ?

├─ Rapidité maximale ?
│  └─ → profile: "speed"
│
├─ RAM limitée (< 1 GB) ?
│  └─ → profile: "memory"
│
├─ Qualité critique ?
│  ├─ Oui + Budget OK pour VLM
│  │  └─ → profile: "quality"
│  └─ Non
│     └─ → profile: "compromise"
│
└─ Besoin très spécifique ?
   └─ → profile: "custom"
```

---

## Configuration VLM pour le Profil `quality`

### Architecture Unifiée LLM/VLM

**IMPORTANT** : Les VLM (Vision Language Models) utilisent la **même architecture** que les LLM.

Les providers VLM sont définis dans `global.yaml > llm_providers` et chaque extracteur VLM spécifie :
- `provider` : Nom du provider (doit exister dans global.yaml)
- `model` : Nom du modèle vision à utiliser
- `temperature` : Paramètre de génération

### Configuration dans `global.yaml`

Les providers suivants supportent les modèles **vision** :

```yaml
llm_providers:
  # OpenAI - GPT-4 Vision, GPT-4o (modèles vision haute qualité)
  openai:
    access_method: "openai_compatible"
    base_url: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"  # Variable d'environnement

  # Anthropic - Claude 3 avec capacité vision (Opus, Sonnet)
  anthropic:
    access_method: "openai_compatible"
    base_url: "https://api.anthropic.com/v1"
    api_key: "${ANTHROPIC_API_KEY}"

  # Ollama - LLaVA (modèles vision open-source, gratuit, local)
  ollama:
    access_method: "openai_compatible"
    base_url: "http://localhost:11434/v1"
    api_key: "ollama"  # Pas besoin de vraie clé
```

### Modèles VLM Disponibles par Provider

| Provider | Modèles Vision | Qualité | Coût | Vitesse |
|----------|----------------|---------|------|---------|
| **openai** | `gpt-4-vision-preview`<br>`gpt-4o`<br>`gpt-4-turbo` | ⭐⭐⭐⭐⭐ | $0.01-0.03/page | Moyen |
| **anthropic** | `claude-3-opus-20240229`<br>`claude-3-sonnet-20240229` | ⭐⭐⭐⭐⭐ | $0.02-0.05/page | Moyen |
| **ollama** | `llava:13b`<br>`llava:7b`<br>`bakllava` | ⭐⭐⭐ | Gratuit | Lent (CPU) |

### Configuration dans Fallback Profile

Dans `config/02_preprocessing.yaml` (ou via profil predefined) :

```yaml
extractors:
  - name: "vlm"
    enabled: true
    config:
      provider: "openai"  # Référence à global.yaml > llm_providers
      model: "gpt-4-vision-preview"
      temperature: 0.0
      max_tokens_per_page: 2000
      max_pages: 10  # Limite pour éviter coûts excessifs
```

**Recommandations** :
- OpenAI `gpt-4o` : Meilleur rapport qualité/prix/vitesse
- Anthropic `claude-3-opus` : Meilleure qualité absolue
- Ollama `llava:13b` : Gratuit pour tests/développement

---

## Métriques et Monitoring

Le système enregistre automatiquement des métriques pour chaque extraction :

```python
{
    "file_path": "contrat_2024.pdf",
    "extraction_method": "docling",  # Quel extracteur a réussi
    "confidence_score": 0.85,
    "original_length": 45230,
    "cleaned_length": 42100,
    "metadata": {
        "extraction_time_seconds": 2.3,
        "num_pages": 12,
        "tables_count": 3
    }
}
```

**Analyser les performances :**

```python
from pathlib import Path
import json

# Charger les résultats d'extraction
results = data["extracted_documents"]

# Statistiques par extracteur
from collections import Counter
methods = Counter(doc["extraction_method"] for doc in results)
print(f"Méthodes utilisées : {methods}")
# → {'pypdf2': 45, 'docling': 12, 'marker': 3}

# Temps moyen d'extraction
avg_time = sum(
    doc["metadata"]["extraction_time_seconds"]
    for doc in results
) / len(results)
print(f"Temps moyen : {avg_time:.2f}s")
```

---

## FAQ

### Q1 : Puis-je changer de profil dynamiquement ?

Oui, vous pouvez modifier `config/02_preprocessing.yaml` et relancer le pipeline. Aucun changement de code nécessaire.

### Q2 : Le profil `quality` nécessite-t-il toujours une API payante ?

Non. Si vous utilisez Ollama avec LLaVA en local, le VLM est gratuit. Mais la qualité sera inférieure à GPT-4V.

### Q3 : Que se passe-t-il si tous les extracteurs échouent ?

Le système lève une `RuntimeError` avec le détail de tous les échecs. Vous pouvez activer `error_handling.skip_on_error: true` pour ignorer le document.

### Q4 : Comment optimiser le profil `quality` pour réduire les coûts VLM ?

Dans le profil quality, réduisez `max_pages` du VLM :

```yaml
extractors:
  - name: vlm
    config:
      max_pages: 5  # Traiter maximum 5 pages avec VLM
```

### Q5 : Peut-on créer ses propres profils prédéfinis ?

Oui ! Modifiez `rag_framework/extractors/fallback_manager.py` :

```python
PROFILES: ClassVar[dict[str, list[dict[str, Any]]]] = {
    # ... profils existants ...

    # Votre profil custom
    "mon_profil": [
        {
            "name": "docling",
            "enabled": True,
            "config": {"ocr_enabled": True}
        }
    ]
}
```

Puis utilisez `profile: "mon_profil"` dans votre config.

---

## Bonnes Pratiques

1. **Commencez par `compromise`** : C'est le meilleur équilibre pour 80% des cas
2. **Utilisez `speed` pour les prototypes** : Tests rapides pendant le développement
3. **Passez à `quality` pour la production critique** : Documents importants seulement
4. **Activez `memory` sur les petits serveurs** : Évite les crashes OOM
5. **Loggez les métriques** : Analysez quel extracteur est le plus utilisé
6. **Testez avec vos documents réels** : Chaque corpus est différent

---

## Exemples Complets

### Exemple 1 : Startup avec budget limité

```yaml
fallback:
  profile: "memory"  # RAM limitée sur serveur cloud
```

### Exemple 2 : Entreprise avec documents critiques

```yaml
fallback:
  profile: "quality"  # Qualité maximale, budget OK
```

### Exemple 3 : Plateforme grand public

```yaml
fallback:
  profile: "compromise"  # Bon compromis pour tous
```

### Exemple 4 : Pipeline de recherche

```yaml
fallback:
  profile: "custom"
  extractors:
    - name: "marker"  # Qualité scientifique
      enabled: true
      config:
        use_gpu: true
        max_pages: null
```

---

## Conclusion

Le système de profils de fallback permet d'**adapter automatiquement** l'extraction à votre contexte :

- 🚀 **Speed** : Démarrage rapide, tests
- 💾 **Memory** : Serveurs limités
- ⚖️ **Compromise** : Production générale (recommandé)
- 💎 **Quality** : Documents critiques
- 🎯 **Custom** : Besoins spécifiques

**Recommandation :** Commencez avec `compromise`, mesurez les performances, puis ajustez si nécessaire.
