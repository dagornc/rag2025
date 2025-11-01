# Mode Surveillance Continue (Watch Mode)

## Vue d'ensemble

Le mode surveillance continue permet au pipeline RAG de surveiller en permanence les répertoires configurés et de traiter automatiquement les nouveaux fichiers détectés.

**Avantages** :
- ✅ Traitement automatique des fichiers dès leur arrivée
- ✅ Continue même si les répertoires sont vides au démarrage
- ✅ Gestion automatique des erreurs (continue en cas d'échec)
- ✅ Arrêt propre avec Ctrl+C

## Utilisation

### Démarrage du mode watch

```bash
# Via start.sh (mode par défaut)
./start.sh

# Via start.sh avec option explicite
./start.sh --watch

# Via CLI Python directement
rye run rag-pipeline --watch

# Avec intervalle personnalisé (défaut: 10s)
rye run rag-pipeline --watch --watch-interval 30
```

### Arrêt du mode watch

Appuyez sur **Ctrl+C** pour arrêter proprement la surveillance.

Le pipeline terminera l'itération en cours puis s'arrêtera.

## Comportement

### Cycle de surveillance

```
1. Scan des répertoires surveillés
   ↓
2. Traitement des fichiers détectés
   ↓
3. Déplacement vers processed/ ou errors/
   ↓
4. Attente (intervalle configurable)
   ↓
5. Retour à l'étape 1
```

### Logs en mode watch

**Itération avec fichiers détectés** :
```
============================================================
📊 Itération 1 - Scan des répertoires surveillés
============================================================
INFO: Monitoring: 3 fichiers détectés dans 3 répertoires
INFO: ✓ Document extrait: rapport.pdf (méthode: pymupdf, 5432 chars)
INFO: ✓ Fichier déplacé vers processed: rapport.pdf

✅ 3 document(s) traité(s)
📦 125 chunk(s) créé(s)
💾 125 chunk(s) stocké(s)

⏳ Attente de 10s avant le prochain scan...
```

**Itération sans nouveaux fichiers** :
```
============================================================
📊 Itération 2 - Scan des répertoires surveillés
============================================================
INFO: Monitoring: 0 fichiers détectés dans 3 répertoires
INFO: Aucun nouveau fichier détecté

⏳ Attente de 10s avant le prochain scan...
```

**Arrêt avec Ctrl+C** :
```
^C
INFO: 🛑 Arrêt de la surveillance (Ctrl+C détecté)
INFO: ✅ Surveillance arrêtée proprement
```

## Configuration

### Répertoires surveillés

Définis dans `config/01_monitoring.yaml` :

```yaml
watch_paths:
  - "./data/input/compliance_docs"
  - "./data/input/audit_reports"
  - "./data/input/docs"
```

### Intervalle de scan

**Par défaut** : 10 secondes

**Personnalisation** :
```bash
# Scan toutes les 30 secondes
./start.sh --watch --watch-interval 30

# Via CLI
rye run rag-pipeline --watch --watch-interval 5
```

### Gestion des fichiers traités

Configurée dans `config/01_monitoring.yaml` :

```yaml
file_management:
  enabled: true
  move_processed: true      # Déplacer vers data/output/processed
  move_errors: true         # Déplacer vers data/output/errors
  preserve_structure: true  # Préserver sous-répertoires
  add_timestamp: true       # Ajouter horodatage
```

## Cas d'usage

### 1. Surveillance de dépôt de documents

**Scénario** : Les utilisateurs déposent des rapports d'audit dans un répertoire partagé.

**Solution** :
```bash
# Démarrer la surveillance continue
./start.sh --watch

# Le pipeline traite automatiquement chaque nouveau fichier
# Les fichiers traités sont déplacés vers output/processed/
```

### 2. Traitement par lots avec attente

**Scénario** : Des documents arrivent par lots toutes les heures.

**Solution** :
```bash
# Scan toutes les 5 minutes (300s)
./start.sh --watch --watch-interval 300
```

### 3. Développement et test

**Scénario** : Tester le pipeline avec de nouveaux documents.

**Solution** :
```bash
# Lancer en mode watch
./start.sh --watch

# Dans un autre terminal, copier des fichiers de test
cp test_documents/*.pdf data/input/docs/

# Observer le traitement automatique dans les logs
```

## Gestion des erreurs

### Comportement en cas d'erreur

Le mode watch **continue** même en cas d'erreur lors d'une itération :

```
ERROR: ✗ Erreur extraction corrupt.pdf: Invalid PDF
WARNING: ✗ Fichier déplacé vers errors: corrupt.pdf
# La surveillance continue !
⏳ Attente de 10s avant le prochain scan...
```

### Fichiers en erreur

Les fichiers en erreur sont :
1. Déplacés vers `data/output/errors/`
2. Un fichier `.error` est créé avec les détails
3. Le pipeline continue avec les autres fichiers

**Exemple** :
```
data/output/errors/
├── docs/
│   ├── corrupt_20250131_143035.pdf
│   └── corrupt_20250131_143035.pdf.error
```

**Contenu du fichier .error** :
```
Erreur: Invalid PDF header
Fichier: /path/to/corrupt.pdf
Date: 2025-01-31T14:30:35.123456
```

## Comparaison des modes

| Caractéristique | Mode Once (`--once`) | Mode Watch (`--watch`) |
|---|---|---|
| Exécution | Une seule fois | Continue en boucle |
| Arrêt | Automatique après traitement | Ctrl+C requis |
| Répertoires vides | S'arrête immédiatement | Continue la surveillance |
| Nouveaux fichiers | Non détectés | Détectés automatiquement |
| Gestion erreurs | Arrêt si erreur | Continue malgré erreurs |
| Usage | Traitement ponctuel | Surveillance continue |

## Options du CLI

```bash
rye run rag-pipeline --help
```

**Options disponibles** :

```
--config-dir PATH       Répertoire de configuration (défaut: config/)
--env-file PATH        Fichier .env (défaut: .env)
--log-level LEVEL      Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
--status               Afficher le statut du pipeline
--watch                Mode surveillance continue
--watch-interval N     Intervalle entre scans en secondes (défaut: 10)
```

## Architecture technique

### Implémentation

Le mode watch est implémenté dans `rag_framework/cli.py` :

```python
if args.watch:
    # Boucle infinie avec gestion Ctrl+C
    while not stop_watch:
        # 1. Scanner les répertoires (MonitoringStep)
        # 2. Extraire et nettoyer (PreprocessingStep)
        # 3. Chunker (ChunkingStep)
        # 4. Enrichir (EnrichmentStep)
        # 5. Auditer (AuditStep)
        # 6. Embedder (EmbeddingStep)
        # 7. Normaliser (NormalizationStep)
        # 8. Stocker (VectorStorageStep)
        result = pipeline.execute()

        # Attendre avant prochain scan
        time.sleep(args.watch_interval)
```

### Avantages de l'approche polling

Le mode watch utilise un **polling simple** (scan périodique) plutôt qu'une détection événementielle (Watchdog) pour plusieurs raisons :

1. **Simplicité** : Réutilise pipeline.execute() sans modification
2. **Fiabilité** : Pas de risque de perdre des événements
3. **Traçabilité** : Logs clairs pour chaque itération
4. **Compatibilité** : Fonctionne sur tous les systèmes de fichiers

L'intervalle de 10s par défaut est un bon compromis entre :
- Réactivité (fichiers traités rapidement)
- Performance (pas de charge excessive)

## Dépannage

### Le mode watch s'arrête immédiatement

**Cause** : Option `--once` utilisée par erreur.

**Solution** :
```bash
# Vérifier que l'option --watch est bien passée
./start.sh --watch
```

### Fichiers non traités

**Causes possibles** :
1. Extension de fichier non autorisée
2. Fichier trop petit (< min_text_length)
3. Erreur d'extraction

**Diagnostic** :
```bash
# Vérifier les logs
tail -f logs/rag_audit.log

# Vérifier les fichiers en erreur
ls -la data/output/errors/
cat data/output/errors/**/*.error
```

### Performance dégradée

**Causes** :
- Intervalle trop court
- Trop de fichiers à traiter

**Solution** :
```bash
# Augmenter l'intervalle
./start.sh --watch --watch-interval 30

# Traiter les fichiers existants en mode once d'abord
./start.sh --once
# Puis passer en mode watch
./start.sh --watch
```

## Intégration avec systemd (Linux)

Pour exécuter le pipeline en tant que service système :

```ini
# /etc/systemd/system/rag-pipeline.service
[Unit]
Description=RAG Pipeline Watch Mode
After=network.target

[Service]
Type=simple
User=raguser
WorkingDirectory=/path/to/rag
ExecStart=/path/to/rag/start.sh --watch
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Activation** :
```bash
sudo systemctl enable rag-pipeline
sudo systemctl start rag-pipeline
sudo systemctl status rag-pipeline
```

## Logs et monitoring

### Logs du pipeline

**Fichier** : `logs/rag_audit.log`

**Rotation** : Automatique (configurable dans `config/global.yaml`)

**Consultation en temps réel** :
```bash
tail -f logs/rag_audit.log
```

### Métriques utiles

À surveiller en mode watch :
- Nombre de fichiers traités par heure
- Taux d'erreur (fichiers en erreur / total)
- Temps de traitement moyen par fichier
- Nombre de chunks créés

## Résumé

Le mode watch transforme le pipeline RAG en un **service de traitement continu** qui :

1. ✅ Surveille automatiquement les répertoires configurés
2. ✅ Traite les nouveaux fichiers dès leur arrivée
3. ✅ Déplace les fichiers traités pour garder les répertoires propres
4. ✅ Continue même en cas d'erreur sur un fichier
5. ✅ S'arrête proprement avec Ctrl+C

**Commande recommandée** :
```bash
./start.sh --watch
```
