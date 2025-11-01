***CONTEXTE RAG***
**Analyse Besoins RAG
*Besoins à couvrir :
B1 - Analyse automatisée de conformité :
	•	Ingestion automatique de documents projets (PDF, DOCX, PowerPoint)
	•	Extraction et analyse des exigences techniques et réglementaires
	•	Évaluation automatique contre les référentiels (II 901, ISO 27001, NIST CSF)
	•	Génération de matrices de conformité avec scores et recommandations
B2 - Veille réglementaire automatisée :
	•	Surveillance quotidienne des sites officiels (cyber.gouv.fr, ANSSI, NIST)
	•	Extraction automatique des nouvelles normes et mises à jour
	•	Intégration dans la base de connaissances RAG (après Intelligent Document Processing avec découpage et analyse sémantique)
	•	Notification des évolutions impactant les projets en cours
B3 - Assistant intelligent projet :
	•	Questions/réponses contextualisées sur les documents projets
	•	Génération automatique de résumés techniques
	•	Aide à la rédaction de dossiers d’architecture (DAG)
	•	Suggestions d’amélioration basées sur les meilleures pratiques
B4 - Génération documentaire automatique :
	•	Production de rapports de conformité standardisés
	•	Synthèses de risques et recommandations
	•	Documentation technique auto-générée
	•	Tableaux de bord de suivi projet

*Technologies requises selon le document :
	•	Intelligent Document Processing avec découpage et analyse sémantique
	•	Base vectorielle avec entraînement de modèles d’embedding
	•	Modèles de langage (LLM) entraînés sur la génération de résumés et l’analyse de conformité
	•	Calcul de similarité pour recherche sémantique
	•	Retrieval Augmented Generation (RAG)
	.	Plateforme chat LLM pour requêtes : Anything LLM (déjà installé)

*Contraintes spécifiques :
	•	Outil 100% gratuit et open source
	•	Compatible macOS M1 avec 8GB RAM
	•	Configuration via fichier YAML pour maximum de flexibilité (y compris hyperparamètre temperature et nom des llm)
	•	Pré-traitement obligatoire avec Docling (documents) et Marker (OCR)
	•	LM Studio et LLM Qwen 8B et LLM Embedding (text-embedding-solon-embeddings-base-0.1) sont tous les 3 déjà installés (LM Studio : http://127.0.0.1:1234)
	•	Mise à jour automatique quotidienne des normes (II 901, ISO 27001, NIST CSF, RGPD, etc.) par scrapping sites web

*Analyse des besoins
1. Reformulation du problème
Créer un système RAG automatisé, gratuit et configurable via YAML pour analyser la conformité de projets techniques aux normes de sécurité françaises et internationales, avec capacités de veille automatique et génération documentaire.
2. Reformulation spécifique et mesurable
Développer une pipeline RAG sur macOS M1 (8GB) capable de traiter 100+ documents/jour, maintenir une base de 500+ normes à jour quotidiennement, générer des rapports de conformité en <5 minutes, et répondre aux questions techniques en <10 secondes avec >85% de précision.
3. Décomposition des sous-problèmes
	•	Ingestion documentaire : Pipeline Docling/Marker → embedding → stockage vectoriel
	•	Orchestration multi-agents : Système  pour coordination des tâches d’analyse
	•	Veille automatisée : Scraping quotidien + intégration base de connaissances
	•	Interface RAG : API locale compatible LM Studio avec Qwen 8B
	•	Configuration YAML : Système flexible type Pathway ou RAGFlow
	•	Optimisation M1 : Utilisation native Apple Silicon + quantification GGUF

*Critères de succès
	•	✅ Configuration 100% via YAML sans code Python
	•	✅ Traitement batch de 50+ documents 
	•	✅ Base de normes synchronisée quotidiennement sans intervention
	•	✅ Réponses RAG contextuelles 
	•	✅ Consommation mémoire <6GB sur M1
	•	✅ Matrice de conformité générée automatiquement
	•	✅ Plateforme chat LLM pour requêtes : Anything LLM (déjà installé)


**Cahier des charges
Mission: Construire un système RAG en français, 100% gratuit et local, pour analyser automatiquement la conformité de projets techniques aux normes (ISO 27001, NIST CSF, RGPD, II 901), optimisé pour macOS M1 (8GB RAM), utilisant Docling, Marker, Tesseract, Python 3, LM Studio (Qwen 8B), Solon embeddings, ChromaDB, et AnythingLLM pour le chat. Configuration 100% via YAML, sans Docker/K8s/venv et sans dépendances payantes.

***

## 1. Besoins Fonctionnels Par Priorité

P1 – Analyse de conformité (B1)
- Ingestion de documents PDF/DOCX/PPTX avec Docling, fallback OCR via Marker puis Tesseract.
- Extraction d’exigences et éléments de preuve.
- Évaluation automatique contre référentiels (ISO 27001, NIST CSF, II 901, RGPD).
- Génération d’une matrice de conformité avec scoring et recommandations.

P2 – Assistant RAG intelligent (B3)
- Questions/réponses contextualisées sur les documents et référentiels.
- Génération de résumés techniques et assistance à la rédaction DAG.
- Templates de prompts spécialisés par référentiel.
- Métriques qualité: precision@k > 85%, recall@k > 80%.
- Re-ranking automatique si relevance score < 0.7.
- Interface: AnythingLLM (déjà installé) et API locale LM Studio.

P3 – Veille réglementaire (B2)
- Scraping quotidien des sites: cyber.gouv.fr, ANSSI, NIST.
- Extraction des changements/nouvelles normes, IDP (chunking + analyse sémantique).
- Intégration automatique dans la base RAG, notifications d’impact.

P3 – Rapports automatiques (B4)
- Rapports PDF standardisés (scores, non-conformités, preuves, recommandations).
- Synthèses risques et tableaux de bord projet.

***

## 2. Architecture 4 Modules

Schéma:
Documents → main.py (orchestration) → ingestion.py → rag.py → rapports
              ↓                          ↓            ↓
         config.yaml                ChromaDB     LM Studio/Qwen
              ↓                          ↓            ↓
         security.py ← ← ← chiffrement + logs + backup

Modules et responsabilités:
- main.py: CLI, orchestration, chargement/validation YAML, gestion des jobs (batch), logging.
- ingestion.py: Docling + Marker + Tesseract; chunking adaptatif; normalisation; indexation ChromaDB.
- rag.py: embeddings (Solon-base), retrieval (similarité cosine), génération (Qwen 8B via LM Studio), scoring (relevance), post-traitement, export.


Connecteurs:
- LM Studio API (http://127.0.0.1:1234) pour Qwen 8B (chat/completions).
- ChromaDB local (persist_directory) avec métrique cosine.
- docling/marker/tesseract pour IDP/OCR.

***

## 3. Contraintes Techniques Strictes

Matériel:
- macOS Apple Silicon M1, 8GB RAM, consommation < 6GB (normal), < 7GB (pic court).

Logiciel:
- 100% gratuit et open source.
- Interdits: Docker, Kubernetes, environnements virtuels, chiffrement, anonymisation des logs
- Configuration uniquement via YAML (sans modification de code Python pour les opérations courantes).

Stack imposée:
- LM Studio + Qwen 8B (modèle quantifié GGUF recommandé pour M1 8GB).
- Embeddings: OrdalieTech/Solon-embeddings-base-0.1 (français).
- Vector store: ChromaDB (persistant, métrique cosine).
- IDP: Docling, Marker, Tesseract (fallback).
- Interface: AnythingLLM.

Exécution locale:
- Aucune donnée envoyée vers le cloud.
- Services accessibles uniquement en localhost.

***

## 4. Configuration YAML Enrichie

Exemple de fichier config.yaml:
```yaml
user:
  expert_level: "intermediate"
  preferred_language: "fr"

security:
  encryption: true
  log_anonymization: true
  backup_frequency: "weekly"
  audit_trail: true

rag:
  chunking:
    adaptive: true
    min_size: 256
    max_size: 1024
    overlap_ratio: 0.1
  evaluation:
    precision_threshold: 0.85
    recall_threshold: 0.80
    rerank_threshold: 0.7
  prompts:
    iso27001: "templates/iso27001_prompt.txt"
    nist: "templates/nist_prompt.txt"
    rgpd: "templates/rgpd_prompt.txt"

llm:
  provider: "lm_studio"
  base_url: "http://127.0.0.1:1234"
  model: "qwen-8b"
  temperature: 0.1
  max_tokens: 2048
  top_p: 0.9
  frequency_penalty: 0.1
  timeout: 30

embeddings:
  model: "text-embedding-solon-embeddings-base-0.1"
  provider: "lm_studio"
  batch_size: 32
  normalize: true
  multilingual: false

vectorstore:
  provider: "chromadb"
  collection_name: "conformite_docs"
  persist_directory: "./data/vectorstore"
  similarity_metric: "cosine"
  n_results: 10
  reindex_on_start: false

directories:
  documents: "./data/documents"
  output: "./data/output"
  vectorstore: "./data/vectorstore"
  cache: "./data/cache"
  templates: "./templates"

monitoring:
  enabled: true
  frequency: "daily"
  check_time: "06:00"
  retry_attempts: 3
  backoff_factor: 2
  sources:
    - name: "cyber.gouv.fr"
      url: "https://cyber.gouv.fr"
      parser: "readability"
    - name: "ANSSI"
      url: "https://www.ssi.gouv.fr"
      parser: "readability"
    - name: "NIST"
      url: "https://csrc.nist.gov"
      parser: "readability"

referentiels:
  - name: "ISO 27001"
    description: "Système de management de la sécurité de l'information"
    url: "https://www.iso.org/standard/27001.html"
    update_frequency: "weekly"
    weight: 1.0
  - name: "NIST CSF"
    description: "Cybersecurity Framework"
    url: "https://csrc.nist.gov/framework"
    update_frequency: "monthly"
    weight: 1.0
  - name: "RGPD"
    description: "Règlement Général sur la Protection des Données"
    url: "https://gdpr.eu"
    update_frequency: "monthly"
    weight: 0.8
  - name: "II 901"
    description: "Référentiel d'exigences internes/sectorielles"
    url: ""
    update_frequency: "monthly"
    weight: 0.9

performance:
  max_memory_gb: 6
  max_concurrent_documents: 10
  response_timeout: 10
  batch_size: 32
  cpu_cores: 4
  queue_policy: "fifo"
  max_retries: 3
  backpressure: true

logging:
  level: "INFO"
  file: "rag_conformite.log"
  rotation: "daily"
  retention_days: 30
  format: "json"
  anonymize_docs: true
```

Notes:
- Tous les paramètres sont modifiables sans code.
- Tous les chemins sont relatifs, aucune dépendance à Docker/K8s/venv.
- Les prompts sont externalisés pour itération rapide.
- Pas de chiffrement ni anonymisation
- Pas de backup / restore embedding

***

## 5. Développement Agile (5 Semaines) et Jalons

Phase 1 (Semaines 1-2): MVP Core
- 4 modules + config YAML
- Ingestion Docling + indexation ChromaDB
- RAG initial (Solon + Qwen 8B via LM Studio)
- Tests avec 10 documents échantillon
Jalons:
- YAML opérationnel
- Ingestion 10 PDF sans erreur
- 1re réponse RAG < 30s
- Tests unitaires modules principaux

Phase 2 (Semaines 3-4): Optimisations clés
- Chunking adaptatif 256-1024
- Évaluation: precision@k, recall@k, relevance
- Prompts spécialisés (ISO, NIST, RGPD)
- AnythingLLM intégré
Jalons:
- Précision RAG > 80% (set test)
- Chiffrement ChromaDB actif
- Templates prompts en place
- AnythingLLM connecté/local

Phase 3 (Semaine 5): Features avancées
- Veille automatisée (scraping + intégration)
- Rapports PDF standardisés
- Tests d’acceptation utilisateur
Jalons:
- Veille quotidienne autonome
- Rapport PDF < 5 min
- Backup/restore validé
- Satisfaction utilisateur > 4/5

Validation continue:
- Tests et retours utilisateur à chaque phase.

***

## 6. Livrables et Validation

Code source:
- main.py (200-300 lignes): orchestration, CLI, gestion jobs.
- ingestion.py (300-400 lignes): IDP, chunking adaptatif, indexation.
- rag.py (400-500 lignes): embeddings, retrieval, génération, scoring, re-ranking.
- Tests unitaires par module (500+ lignes total).

Configuration:
- config.yaml (commenté, autoporteur).
- templates/ (prompts ISO27001, NIST, RGPD).
- requirements.txt (versions pinning).

Documentation:
- README.md (installation, configuration) – 1 page
- USER_GUIDE.md (usage + captures) – 2 pages
- TROUBLESHOOTING.md (FAQ) – 1 page
- ARCHITECTURE.md (schémas + interfaces) – 1 page

Scripts:
- install.sh (prérequis, libs, tesseract data)
- start.sh (lancement services, vérification LM Studio)
- backup.sh (snapshot vectorstore et métadonnées)

***

## 7. Critères d’Acceptation Finale

Fonctionnels:
- F1: Ingestion PDF/DOCX/PPTX automatisée – taux succès > 95%
- F2: Q/R RAG – précision > 85% sur set test
- F3: Rapport de conformité complet – < 5 min
- F4: Veille quotidienne – sans intervention manuelle
- F5: Interface AnythingLLM – utilisable et stable

***

## 8. Interfaces et Protocole d’Intégration

LM Studio (Qwen 8B):
- Endpoint: POST /v1/chat/completions
- Paramètres: model, messages, temperature, top_p, max_tokens, seed (optionnel), timeout
- Politique de retry: max_retries=3, backoff_factor=2

Embeddings (Solon-base):
- Endpoint: /v1/embeddings via LM Studio (ou wrapper local)
- Batch_size=32, normalize=true, multilingual=false
- Contrôle d’erreur: skip sur texte vide, log anonymisé

ChromaDB:
- Collection: conformite_docs
- Champs: id (uuid), document_id, chunk_id, text, metadata {source, hash, referentiel_tag, timestamp}
- Similarité: cosine, n_results=10
- Persistence: persist_directory=./data/vectorstore

IDP:
- Docling: parsing PDF/DOCX/PPTX vers texte/markdown structuré
- Marker: fallback OCR pour PDF scannés
- Tesseract: fallback final OCR
- Politique: triage automatique selon confiance extraction

***

## 9. Qualité et Tests

Tests unitaires:
- Parsing (Docling/Marker), chunking, embeddings, retrieval, LLM generation, chiffrement, backup/restore.

Tests d’intégration:
- Pipeline complet: document → rapport PDF
- Scénarios de veille: nouveau contenu détecté → indexation → notification

Tests de performance:
- Batch 50+ documents, mesure temps total, mémoire
- Réponse RAG < 10s sur 20 questions aléatoires

Tests de robustesse:
- Redémarrage à chaud/froid
- Corruption simulée d’un segment d’index → restore automatique

***

## 10. Gouvernance et Propriété

- Code, configurations, index et logs restent locaux et sous contrôle exclusif utilisateur.
- Aucun fournisseur propriétaire unique: modèles et composants interchangeables (Qwen ↔ autres LLM locaux; Solon ↔ autre embedding FR open source; ChromaDB ↔ alternative si besoin).
- Documentation et scripts garantissent autonomie d’exploitation.


