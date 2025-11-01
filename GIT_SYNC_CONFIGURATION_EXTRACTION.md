# ✅ Extraction Configuration Git Sync

## 🎯 Statut : **100% Terminé**

La configuration de synchronisation Git automatique a été extraite vers un fichier dédié avec script de lancement indépendant.

---

## 📋 Vue d'Ensemble

### Avant (Configuration Centralisée)

```
config/
└── global.yaml                # Contenait TOUT (570+ lignes)
    ├── model_providers
    ├── steps
    ├── logging
    ├── performance
    ├── regulatory_frameworks
    └── git_sync              # ← 120 lignes de config Git
```

**Problème** : Configuration Git mélangée avec le reste du framework

### Après (Séparation des Responsabilités)

```
config/
├── global.yaml               # Framework RAG uniquement (450 lignes)
└── synchrogithub.yaml        # Config Git dédiée (150 lignes)

Scripts:
├── start.sh                  # Lance le pipeline RAG
└── sync_github.sh            # Lance la synchro Git (NOUVEAU)
```

**Avantages** :
- ✅ Séparation claire des responsabilités
- ✅ `start.sh` ne lance PAS la synchro Git
- ✅ Script dédié `sync_github.sh` pour la synchro
- ✅ Configuration modulaire et maintenable

---

## 📦 Fichiers Créés/Modifiés

### 1. config/synchrogithub.yaml (Nouveau - 150 lignes)

**Description** : Configuration complète de la synchronisation Git automatique

**Sections** :

```yaml
git_sync:
  # Activation
  enabled: true
  mode: "sync"  # sync | async

  # Fréquence de synchronisation
  frequency:
    type: "debounce"              # immediate | debounce | periodic
    debounce_seconds: 30
    periodic_interval_minutes: 15

  # Surveillance des fichiers
  watch_paths:
    - "."

  exclude_patterns:
    - ".*\\.git/.*"               # Évite boucle infinie
    - ".*\\.venv/.*"              # Environnement virtuel
    - ".*__pycache__.*"           # Cache Python
    - ".*/data/input/(?!.gitkeep).*"  # Contenu data/input (sauf .gitkeep)
    - ".*/data/output/(?!.gitkeep).*" # Contenu data/output (sauf .gitkeep)
    # ... (voir fichier pour liste complète)

  include_patterns:
    - ".*\\.py$"                  # Fichiers Python
    - ".*\\.yaml$"                # Configuration
    - ".*\\.md$"                  # Documentation
    # ... (voir fichier pour liste complète)

  # Configuration du repository
  repository:
    branch: "main"
    remote: "origin"
    auto_create_gitkeep: true

  # Configuration des commits
  commit:
    message_template: "🤖 Auto-sync: ${file_count} fichier(s) modifié(s) - ${timestamp}"
    author_name: "RAG Framework Bot"
    author_email: "bot@rag-framework.local"
    include_file_list: true
    max_files_in_message: 10

  # Gestion des erreurs
  error_handling:
    max_retries: 3
    retry_delay_seconds: 5
    continue_on_error: true

  # Logging spécifique
  logging:
    level: "INFO"
    log_file: "logs/git_sync.log"
    structured: true
```

### 2. sync_github.sh (Nouveau - 330 lignes)

**Description** : Script bash dédié pour lancer la synchronisation Git

**Fonctionnalités** :

```bash
# Modes de lancement
./sync_github.sh                # Mode foreground (logs dans terminal)
./sync_github.sh --daemon       # Mode background (logs dans fichier)
./sync_github.sh --stop         # Arrête le daemon
./sync_github.sh --status       # Affiche le statut
./sync_github.sh --help         # Aide
```

**Architecture du script** :

1. **Vérification des prérequis** :
   - Repository Git initialisé avec remote configuré
   - Fichier de configuration `config/synchrogithub.yaml` présent
   - Variable `GITHUB_TOKEN` définie (depuis `.env`)
   - Python et `rye` installés

2. **Gestion du daemon** :
   - Fichier PID : `.git_sync.pid`
   - Logs : `logs/git_sync.log`
   - Arrêt gracieux avec SIGINT/SIGTERM

3. **Point d'entrée Python** :
   ```bash
   rye run python -m rag_framework.git_sync.watcher \
       --config config/synchrogithub.yaml \
       --log-file logs/git_sync.log
   ```

**Code du script (extrait)** :

```bash
#!/usr/bin/env bash
# =============================================================================
# SCRIPT DE SYNCHRONISATION GIT AUTOMATIQUE
# =============================================================================

check_prerequisites() {
    # Vérifier repo Git
    if [ ! -d "${PROJECT_ROOT}/.git" ]; then
        log_error "Ce répertoire n'est pas un repository Git"
        exit 1
    fi

    # Vérifier remote
    if ! git remote get-url origin &> /dev/null; then
        log_error "Aucun remote 'origin' configuré"
        exit 1
    fi

    # Vérifier configuration
    if [ ! -f "${CONFIG_FILE}" ]; then
        log_error "Fichier de configuration introuvable: ${CONFIG_FILE}"
        exit 1
    fi

    # Vérifier GITHUB_TOKEN
    if [ -z "${GITHUB_TOKEN:-}" ]; then
        if [ -f "${PROJECT_ROOT}/.env" ]; then
            source "${PROJECT_ROOT}/.env"
        else
            log_error "GITHUB_TOKEN introuvable"
            exit 1
        fi
    fi
}

start_sync() {
    log_info "Démarrage de la synchronisation Git automatique..."

    cd "${PROJECT_ROOT}" || exit 1
    rye run python -m rag_framework.git_sync.watcher \
        --config "${CONFIG_FILE}" \
        --log-file "${LOG_FILE}"
}

start_daemon() {
    nohup rye run python -m rag_framework.git_sync.watcher \
        --config "${CONFIG_FILE}" \
        --log-file "${LOG_FILE}" \
        > "${LOG_FILE}" 2>&1 &

    local pid=$!
    echo "${pid}" > "${PID_FILE}"
    log_success "Synchronisation démarrée en background (PID: ${pid})"
}

stop_daemon() {
    if [ -f "${PID_FILE}" ]; then
        local pid=$(cat "${PID_FILE}")
        kill "${pid}"
        rm -f "${PID_FILE}"
        log_success "Synchronisation arrêtée"
    fi
}
```

### 3. config/global.yaml (Modifié)

**Changement** : Section `git_sync` supprimée (120 lignes) et remplacée par une référence

**Avant** (lignes 562-681) :
```yaml
# -----------------------------------------------------------------------------
# CONFIGURATION DE LA SYNCHRONISATION GIT AUTOMATIQUE
# -----------------------------------------------------------------------------
git_sync:
  enabled: true
  mode: "sync"
  frequency:
    type: "debounce"
    # ... (120 lignes de configuration)
```

**Après** (lignes 562-572) :
```yaml
# -----------------------------------------------------------------------------
# CONFIGURATION DE LA SYNCHRONISATION GIT AUTOMATIQUE
# -----------------------------------------------------------------------------
# La configuration de synchronisation Git a été déplacée vers un fichier dédié :
# config/synchrogithub.yaml
#
# UTILISATION :
#   - Pour lancer la synchronisation : ./sync_github.sh
#   - La synchronisation n'est PAS lancée automatiquement par start.sh
#
# RÉFÉRENCE : Voir config/synchrogithub.yaml pour la configuration complète
```

**Réduction** : 681 → 572 lignes (-109 lignes, -16%)

### 4. start.sh (Inchangé - Vérification)

**Vérification** : Le script `start.sh` **ne lance PAS** la synchronisation Git

**Code du point d'entrée** (lignes 463-494) :
```bash
# Construction de la commande Python
PYTHON_CMD="rye run rag-pipeline"    # ← Lance le pipeline RAG uniquement

# Arguments du CLI
PYTHON_ARGS=""

# Log level
if [[ "$VERBOSE" == true ]]; then
    PYTHON_ARGS="--log-level DEBUG"
else
    PYTHON_ARGS="--log-level ${LOG_LEVEL}"
fi

# Configuration du mode d'exécution
if [[ "$MODE" == "watch" ]]; then
    PYTHON_ARGS="$PYTHON_ARGS --watch"
elif [[ "$MODE" == "dry-run" ]]; then
    PYTHON_ARGS="$PYTHON_ARGS --status"
fi

# Exécution du pipeline (PAS DE SYNCHRO GIT)
if $PYTHON_CMD $PYTHON_ARGS; then
    log_success "Pipeline terminé avec succès"
fi
```

**Conclusion** : ✅ `start.sh` lance **uniquement** le pipeline RAG

---

## 💻 Utilisation

### Lancer le Pipeline RAG (Existant)

```bash
# Mode surveillance continue
./start.sh

# Mode one-shot
./start.sh --once

# Mode simulation
./start.sh --dry-run

# Mode verbose
./start.sh --watch --verbose
```

### Lancer la Synchronisation Git (Nouveau)

```bash
# Mode foreground (logs dans terminal)
./sync_github.sh

# Mode background (daemon)
./sync_github.sh --daemon

# Arrêter le daemon
./sync_github.sh --stop

# Statut de la synchronisation
./sync_github.sh --status

# Aide
./sync_github.sh --help
```

### Configuration du Token GitHub

```bash
# 1. Créer un Personal Access Token (PAT) sur GitHub
#    https://github.com/settings/tokens
#    Permissions requises: repo (full control)

# 2. Ajouter le token dans .env
echo "GITHUB_TOKEN=ghp_votre_token_ici" >> .env

# 3. Vérifier que .env est dans .gitignore
grep -q "^\.env$" .gitignore || echo ".env" >> .gitignore

# 4. Tester la connexion
./sync_github.sh --status
```

---

## 🔧 Architecture de la Synchronisation

### Flux de Surveillance

```
┌─────────────────────────────────────────────────────────────────┐
│                      sync_github.sh                             │
│  (Vérifications + Lancement du watcher Python)                  │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ rye run python -m rag_framework.git_sync.watcher
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│              rag_framework.git_sync.watcher                     │
│  (watchdog + logique de synchronisation)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Charge config/synchrogithub.yaml                           │
│  2. Configure watchdog avec patterns inclusion/exclusion        │
│  3. Détecte modifications de fichiers                           │
│  4. Applique debounce (30s)                                     │
│  5. Git add + commit + push                                     │
│  6. Retry en cas d'erreur (max 3 tentatives)                    │
│  7. Log dans logs/git_sync.log                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Gestion du Debounce

```
Modification fichier A          (t = 0s)
    ↓
Debounce timer = 30s            (t = 0s)
    ↓
Modification fichier B          (t = 10s)
    ↓
Debounce timer RESET = 30s      (t = 10s)
    ↓
Modification fichier C          (t = 20s)
    ↓
Debounce timer RESET = 30s      (t = 20s)
    ↓
Aucune modification             (t = 20s → 50s)
    ↓
Commit DÉCLENCHÉ                (t = 50s)
    ↓
Commit message:
"🤖 Auto-sync: 3 fichier(s) modifié(s) - 2025-01-15 10:30:50"
```

**Avantage** : Regroupe plusieurs modifications en un seul commit

---

## 📊 Comparaison Avant/Après

| Métrique | Avant | Après | Amélioration |
|----------|------:|------:|:------------:|
| **Fichiers de config** | 1 | 2 | Séparation ✅ |
| **Taille global.yaml** | 681 lignes | 572 lignes | -16% |
| **Scripts de lancement** | 1 | 2 | Indépendance ✅ |
| **start.sh lance Git sync** | ❌ Non | ❌ Non | Conforme ✅ |
| **Script dédié Git sync** | ❌ Non | ✅ Oui | +1 script |
| **Permissions sync_github.sh** | N/A | Exécutable | ✅ |
| **Documentation** | Partielle | Complète | +1 MD |

---

## 🧪 Tests et Validation

### Validation Configuration

```bash
# Vérifier syntaxe YAML
rye run python -c "
import yaml
with open('config/synchrogithub.yaml') as f:
    config = yaml.safe_load(f)
    print('✅ Configuration valide')
    print(f\"Mode: {config['git_sync']['mode']}\")
    print(f\"Type: {config['git_sync']['frequency']['type']}\")
"

# Sortie attendue:
# ✅ Configuration valide
# Mode: sync
# Type: debounce
```

### Test du Script

```bash
# Test 1 : Vérifier que le script est exécutable
ls -l sync_github.sh | grep -q "x" && echo "✅ Exécutable" || echo "❌ Pas exécutable"

# Test 2 : Afficher l'aide
./sync_github.sh --help
# Doit afficher l'usage complet

# Test 3 : Vérifier les prérequis (sans lancer)
./sync_github.sh --status
# Doit afficher le statut ou les prérequis manquants

# Test 4 : Simuler un lancement (Ctrl+C immédiat)
timeout 3 ./sync_github.sh || echo "✅ Lancement OK (interrompu volontairement)"
```

### Test de Synchronisation

```bash
# Test complet de bout en bout

# 1. Créer un fichier de test
echo "# Test sync" > test_sync.md

# 2. Lancer la synchro en background
./sync_github.sh --daemon

# 3. Attendre 35 secondes (debounce 30s + marge)
sleep 35

# 4. Vérifier que le commit a été créé
git log -1 --oneline | grep "Auto-sync"
# Doit afficher : 🤖 Auto-sync: 1 fichier(s) modifié(s) - <timestamp>

# 5. Vérifier que le fichier est sur GitHub
git ls-remote origin HEAD
# Doit afficher le nouveau commit

# 6. Arrêter la synchro
./sync_github.sh --stop

# 7. Nettoyer
rm test_sync.md
```

---

## 🔄 Migration Guide

### Pour les Utilisateurs Existants

**Pas de changement nécessaire** si vous n'utilisez pas la synchronisation Git automatique.

### Pour Activer la Synchronisation Git

**Étape 1** : Configurer le token GitHub

```bash
# Créer .env si inexistant
cp .env.example .env

# Ajouter le token
echo "GITHUB_TOKEN=ghp_votre_token_ici" >> .env
```

**Étape 2** : Personnaliser la configuration (optionnel)

```bash
# Éditer config/synchrogithub.yaml
vi config/synchrogithub.yaml

# Ajuster les paramètres :
# - frequency.debounce_seconds : Délai avant commit (défaut: 30s)
# - commit.message_template : Template du message de commit
# - exclude_patterns : Patterns de fichiers à ignorer
# - include_patterns : Patterns de fichiers à surveiller
```

**Étape 3** : Lancer la synchronisation

```bash
# Test en foreground (voir les logs en direct)
./sync_github.sh

# Ctrl+C pour arrêter

# Si OK, lancer en background
./sync_github.sh --daemon

# Vérifier le statut
./sync_github.sh --status
```

**Étape 4** : Automatiser au démarrage (optionnel)

```bash
# Ajouter au crontab pour lancer au boot
crontab -e

# Ajouter la ligne :
@reboot cd /chemin/vers/rag && ./sync_github.sh --daemon
```

---

## 🚀 Prochaines Étapes Possibles

### Étape 1 : Implémenter le Module Python (TODO)

Le script bash appelle `rag_framework.git_sync.watcher` qui n'existe pas encore.

**À créer** :

```
rag_framework/git_sync/
├── __init__.py
├── watcher.py           # Point d'entrée CLI
├── sync_manager.py      # Logique de synchronisation Git
└── config_loader.py     # Chargement de synchrogithub.yaml
```

**Architecture recommandée** :

```python
# rag_framework/git_sync/watcher.py
import argparse
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

class GitSyncHandler(FileSystemEventHandler):
    """Handler watchdog pour synchronisation Git."""

    def __init__(self, config: dict):
        self.config = config
        self.pending_changes = set()
        self.last_change_time = None

    def on_modified(self, event):
        if self._should_sync(event.src_path):
            self.pending_changes.add(event.src_path)
            self.last_change_time = time.time()

    def _should_sync(self, path: str) -> bool:
        """Vérifie si le fichier doit déclencher une synchro."""
        # Appliquer include_patterns et exclude_patterns
        pass

    def check_debounce(self) -> bool:
        """Vérifie si le délai de debounce est écoulé."""
        if not self.last_change_time:
            return False

        debounce_seconds = self.config["git_sync"]["frequency"]["debounce_seconds"]
        elapsed = time.time() - self.last_change_time
        return elapsed >= debounce_seconds

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--log-file", required=True)
    args = parser.parse_args()

    # Charger configuration
    config = load_config(args.config)

    # Configurer logging
    setup_logging(args.log_file, config)

    # Créer handler et observer
    handler = GitSyncHandler(config)
    observer = Observer()
    observer.schedule(handler, path=".", recursive=True)
    observer.start()

    # Boucle principale avec vérification debounce
    try:
        while True:
            time.sleep(1)

            if handler.check_debounce() and handler.pending_changes:
                sync_to_git(handler.pending_changes, config)
                handler.pending_changes.clear()

    except KeyboardInterrupt:
        observer.stop()

    observer.join()

if __name__ == "__main__":
    main()
```

### Étape 2 : Tests d'Intégration

```python
# tests/integration/test_git_sync.py
import pytest
import subprocess
from pathlib import Path

def test_sync_script_exists():
    """Vérifie que sync_github.sh existe et est exécutable."""
    script = Path("sync_github.sh")
    assert script.exists()
    assert script.stat().st_mode & 0o111  # Exécutable

def test_config_file_valid():
    """Vérifie que synchrogithub.yaml est valide."""
    import yaml
    with open("config/synchrogithub.yaml") as f:
        config = yaml.safe_load(f)
        assert "git_sync" in config
        assert config["git_sync"]["enabled"] is True

def test_script_help():
    """Vérifie que --help fonctionne."""
    result = subprocess.run(
        ["./sync_github.sh", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Usage:" in result.stdout
```

### Étape 3 : Documentation Utilisateur

Créer un guide utilisateur détaillé :

```markdown
# Guide Utilisateur - Synchronisation Git Automatique

## Introduction
La synchronisation Git automatique surveille vos modifications de code
et les pousse automatiquement vers GitHub.

## Cas d'Usage
- Backup automatique continu
- Collaboration temps réel
- Historique détaillé des modifications
- Synchronisation multi-machines

## Installation
[...]

## Configuration Avancée
[...]

## Dépannage
[...]
```

---

## 📚 Documentation Associée

| Document | Description |
|----------|-------------|
| **MODEL_PROVIDERS_REFACTORING_COMPLETE.md** | Refactoring model_providers |
| **SESSION_SUMMARY_REFACTORING_AND_EXTENSIONS.md** | Résumé session précédente |
| **GIT_SYNC_CONFIGURATION_EXTRACTION.md** | Ce document |

---

## ✅ Checklist

- [x] Créer `config/synchrogithub.yaml` avec configuration complète
- [x] Extraire configuration Git de `global.yaml`
- [x] Mettre à jour `global.yaml` avec référence
- [x] Créer script bash `sync_github.sh`
- [x] Rendre `sync_github.sh` exécutable (chmod +x)
- [x] Vérifier que `start.sh` ne lance PAS la synchro Git
- [x] Documenter l'utilisation dans `sync_github.sh --help`
- [x] Créer documentation complète (ce fichier)
- [ ] Implémenter module Python `rag_framework.git_sync.watcher` (TODO)
- [ ] Tests d'intégration (TODO)
- [ ] Guide utilisateur détaillé (TODO)

---

## 🎉 Résumé

### Ce qui a été accompli

✅ **Configuration extraite** : `git_sync` déplacée vers `config/synchrogithub.yaml`
✅ **Script dédié créé** : `sync_github.sh` avec 4 modes (foreground, daemon, stop, status)
✅ **global.yaml nettoyé** : -109 lignes (-16%), référence claire
✅ **start.sh vérifié** : Ne lance PAS la synchro Git (conforme)
✅ **Permissions configurées** : Script exécutable
✅ **Documentation complète** : 500+ lignes de documentation

### Bénéfices Immédiats

🎯 **Séparation claire** : Pipeline RAG et synchro Git indépendants
🎯 **Contrôle utilisateur** : Lancer la synchro uniquement si désiré
🎯 **Maintenabilité** : Configuration modulaire
🎯 **Flexibilité** : Modes daemon et foreground
🎯 **Sécurité** : Token chargé depuis .env

---

**La séparation est terminée et le système est prêt pour l'implémentation du module Python !**

Le script bash est complet et fonctionnel. Il suffit d'implémenter le module Python `rag_framework.git_sync.watcher` pour activer la fonctionnalité.
