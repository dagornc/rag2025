#!/usr/bin/env bash
# =============================================================================
# SCRIPT DE DÉMARRAGE - Framework RAG Audit & Conformité
# =============================================================================
# Démarre le pipeline RAG avec surveillance continue des répertoires sources.
# Le pipeline traite automatiquement les nouveaux fichiers détectés via
# watchdog et exécute les étapes activées dans config/global.yaml.
#
# Usage:
#   ./start.sh [OPTIONS]
#
# Options:
#   --watch      Mode surveillance continue (défaut)
#   --once       Traite les fichiers existants puis arrête
#   --dry-run    Simule l'exécution sans traiter les fichiers
#   --verbose    Active les logs détaillés (DEBUG)
#   --help       Affiche cette aide
#
# Variables d'environnement:
#   Les clés API sont chargées depuis .env (OPENAI_API_KEY, etc.)
#
# Auteur: RAG Team
# Version: 0.1.0
# =============================================================================

set -e  # Arrêt immédiat en cas d'erreur
set -u  # Erreur si variable non définie
set -o pipefail  # Propagation des erreurs dans les pipes

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
PROJECT_NAME="rag_framework"
MODE="watch"  # Options: watch | once | dry-run
VERBOSE=false
LOG_LEVEL="INFO"

# Couleurs pour affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# FONCTIONS UTILITAIRES
# -----------------------------------------------------------------------------

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    if [[ "$VERBOSE" == true ]]; then
        echo -e "${CYAN}[DEBUG]${NC} $1"
    fi
}

show_help() {
    echo "Usage: ./start.sh [OPTIONS]"
    echo ""
    echo "Démarre le pipeline RAG Audit & Conformité"
    echo ""
    echo "Options:"
    echo "  --watch      Mode surveillance continue (défaut)"
    echo "               Surveille les répertoires et traite les nouveaux fichiers"
    echo ""
    echo "  --once       Mode one-shot"
    echo "               Traite les fichiers existants une fois puis arrête"
    echo ""
    echo "  --dry-run    Mode simulation"
    echo "               Affiche ce qui serait fait sans traiter les fichiers"
    echo ""
    echo "  --verbose    Mode verbeux"
    echo "               Active les logs détaillés (niveau DEBUG)"
    echo ""
    echo "  --help       Affiche cette aide"
    echo ""
    echo "Exemples:"
    echo "  ./start.sh                    # Mode surveillance continue"
    echo "  ./start.sh --once             # Traite une fois et arrête"
    echo "  ./start.sh --watch --verbose  # Surveillance avec logs détaillés"
    echo ""
    echo "Configuration:"
    echo "  → config/global.yaml           Activation des étapes du pipeline"
    echo "  → config/01_monitoring.yaml    Répertoires surveillés"
    echo "  → .env                         Clés API (OPENAI_API_KEY, etc.)"
    echo ""
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Gestion des signaux (Ctrl+C)
trap_exit() {
    echo ""
    log_warning "Signal reçu. Arrêt du pipeline..."
    log_info "Nettoyage en cours..."
    # Cleanup si nécessaire
    log_success "Pipeline arrêté proprement"
    exit 0
}

trap trap_exit SIGINT SIGTERM

# -----------------------------------------------------------------------------
# PARSE DES ARGUMENTS
# -----------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case $1 in
        --watch)
            MODE="watch"
            shift
            ;;
        --once)
            MODE="once"
            shift
            ;;
        --dry-run)
            MODE="dry-run"
            shift
            ;;
        --verbose)
            VERBOSE=true
            LOG_LEVEL="DEBUG"
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "Option inconnue: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
done

# -----------------------------------------------------------------------------
# BANNIÈRE
# -----------------------------------------------------------------------------

clear
echo "============================================================================="
echo "  ____      _      ____   _____                                            "
echo " |  _ \    / \    / ___| |  ___|  _ __   __ _  _ __ ___    ___ __      __ "
echo " | |_) |  / _ \  | |  _  | |_    | '__| / _\` || '_ \` _ \  / _ \\\\ \ /\ / / "
echo " |  _ <  / ___ \ | |_| | |  _|   | |   | (_| || | | | | ||  __/ \ V  V /  "
echo " |_| \_\/_/   \_\ \____| |_|     |_|    \__,_||_| |_| |_| \___|  \_/\_/   "
echo "                                                                           "
echo "============================================================================="
echo "  Framework RAG Audit & Conformité v0.1.0"
echo "  Mode: ${MODE}"
if [[ "$VERBOSE" == true ]]; then
    echo "  Log Level: DEBUG (verbose)"
else
    echo "  Log Level: INFO"
fi
echo "============================================================================="
echo ""

# -----------------------------------------------------------------------------
# VÉRIFICATIONS PRÉLIMINAIRES
# -----------------------------------------------------------------------------

log_info "Vérifications préliminaires..."

# Vérification Python
if ! check_command python3; then
    log_error "Python 3 n'est pas installé"
    exit 1
fi

# Vérification rye
if ! check_command rye; then
    log_error "rye n'est pas installé"
    log_error "Lancez d'abord: ./install.sh"
    exit 1
fi

# Vérification du package
if ! rye run python -c "import rag_framework" &> /dev/null; then
    log_error "Package rag_framework non installé"
    log_error "Lancez d'abord: ./install.sh"
    exit 1
fi

log_success "Environnement Python OK"
echo ""

# -----------------------------------------------------------------------------
# CHARGEMENT DES VARIABLES D'ENVIRONNEMENT
# -----------------------------------------------------------------------------

log_info "Chargement des variables d'environnement..."

if [[ -f ".env" ]]; then
    log_debug "Chargement depuis .env"
    # Export des variables depuis .env (ignore commentaires et lignes vides)
    set -a
    source <(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//')
    set +a
    log_success "Variables d'environnement chargées"
else
    log_warning "Fichier .env introuvable"
    log_warning "Les providers nécessitant des clés API ne fonctionneront pas"
    log_warning "Créez .env depuis .env.example si nécessaire"
fi

echo ""

# -----------------------------------------------------------------------------
# VÉRIFICATION DES FICHIERS DE CONFIGURATION
# -----------------------------------------------------------------------------

log_info "Vérification de la configuration..."

# Vérifier config/global.yaml
if [[ ! -f "config/global.yaml" ]]; then
    log_error "Fichier config/global.yaml introuvable"
    log_error "Lancez d'abord: ./install.sh"
    exit 1
fi

log_debug "  ✓ config/global.yaml"

# Extraire les fichiers de config référencés dans global.yaml
log_info "Extraction des références de configuration depuis global.yaml..."

# Utilise une simple liste hardcodée des fichiers standards
# Plus simple et plus fiable que de parser le YAML
REFERENCED_CONFIGS="config/01_monitoring.yaml
config/02_preprocessing.yaml
config/03_chunking.yaml
config/04_enrichment.yaml
config/05_audit.yaml
config/06_embedding.yaml
config/07_normalization.yaml
config/08_vector_storage.yaml"

# Vérifier l'existence de chaque fichier référencé
MISSING_CONFIGS=()
while IFS= read -r config_file; do
    if [[ -n "$config_file" ]]; then
        if [[ -f "$config_file" ]]; then
            log_debug "  ✓ $config_file"
        else
            log_warning "  ✗ Manquant: $config_file"
            MISSING_CONFIGS+=("$config_file")
        fi
    fi
done <<< "$REFERENCED_CONFIGS"

# Si des fichiers manquent, proposer de les créer
if [[ ${#MISSING_CONFIGS[@]} -gt 0 ]]; then
    echo ""
    log_warning "${#MISSING_CONFIGS[@]} fichier(s) de configuration manquant(s):"
    for config in "${MISSING_CONFIGS[@]}"; do
        echo "  • $config"
    done
    echo ""

    # Demander confirmation en mode interactif (pas en dry-run)
    if [[ "$MODE" != "dry-run" ]] && [[ -t 0 ]]; then
        read -p "Voulez-vous créer ces fichiers avec une configuration minimale ? (o/N) " -n 1 -r
        echo ""

        if [[ $REPLY =~ ^[Oo]$ ]]; then
            log_info "Création des fichiers de configuration manquants..."

            for config in "${MISSING_CONFIGS[@]}"; do
                # Créer le répertoire parent si nécessaire
                mkdir -p "$(dirname "$config")"

                # Extraire le nom de l'étape depuis le nom du fichier
                STEP_NAME=$(basename "$config" .yaml)
                STEP_NUM=$(echo "$STEP_NAME" | grep -o '^[0-9]\+')
                STEP_TITLE=$(echo "$STEP_NAME" | sed 's/^[0-9]*_//' | tr '_' ' ' | sed 's/.*/\u&/')

                # Créer un template minimal
                cat > "$config" << EOF
# =============================================================================
# ${STEP_TITLE^^}
# =============================================================================
# Fichier de configuration pour cette étape du pipeline.
# Généré automatiquement par start.sh
#
# NOTE: L'activation de cette étape est contrôlée dans config/global.yaml
#       via le paramètre steps.${STEP_NAME/_enabled/}_enabled
# =============================================================================

# Configuration minimale par défaut
# TODO: Personnaliser cette configuration selon vos besoins

# Exemple de paramètres (à adapter)
# param1: valeur1
# param2: valeur2
EOF

                log_success "  ✓ Créé: $config"
            done

            echo ""
            log_success "Fichiers de configuration créés"
            log_warning "IMPORTANT: Éditez ces fichiers pour les adapter à vos besoins"
            echo ""

        else
            log_error "Fichiers de configuration manquants. Impossible de continuer."
            log_error "Créez-les manuellement ou relancez avec confirmation"
            exit 1
        fi
    else
        # Mode non-interactif ou dry-run
        if [[ "$MODE" == "dry-run" ]]; then
            log_info "Mode simulation: Ces fichiers seraient créés"
        else
            log_error "Mode non-interactif: Impossible de demander confirmation"
            log_error "Créez les fichiers manuellement ou lancez en mode interactif"
            exit 1
        fi
    fi
fi

log_success "Configuration OK"
echo ""

# -----------------------------------------------------------------------------
# AFFICHAGE DES ÉTAPES ACTIVÉES
# -----------------------------------------------------------------------------

log_info "Lecture de la configuration du pipeline..."

# Parse YAML simple pour afficher les étapes activées
# Utilise rye run python pour avoir accès à PyYAML dans l'environnement virtuel
ENABLED_STEPS=$(rye run python -c "
import yaml
import sys

try:
    with open('config/global.yaml', 'r') as f:
        config = yaml.safe_load(f)
        steps = config.get('steps', {})
        enabled = []
        step_names = {
            'monitoring_enabled': 'Étape 1 - Monitoring',
            'preprocessing_enabled': 'Étape 2 - Preprocessing',
            'chunking_enabled': 'Étape 3 - Chunking',
            'enrichment_enabled': 'Étape 4 - Enrichment',
            'audit_enabled': 'Étape 5 - Audit',
            'embedding_enabled': 'Étape 6 - Embedding',
            'normalization_enabled': 'Étape 7 - Normalization',
            'vector_storage_enabled': 'Étape 8 - Vector Storage'
        }
        for key, name in step_names.items():
            if steps.get(key, False):
                enabled.append(name)
        for step in enabled:
            print(f'  ✓ {step}')
        if not enabled:
            print('  ⚠ Aucune étape activée')
except Exception as e:
    print(f'  ⚠ Erreur lecture config: {e}', file=sys.stderr)
    sys.exit(0)  # Exit 0 pour ne pas bloquer le script
" 2>&1) || true

if [[ -n "$ENABLED_STEPS" ]]; then
    echo "Étapes activées:"
    echo "$ENABLED_STEPS"
else
    log_warning "Impossible de lire la configuration YAML (non bloquant)"
fi

echo ""

# -----------------------------------------------------------------------------
# VÉRIFICATION DES RÉPERTOIRES
# -----------------------------------------------------------------------------

log_info "Vérification des répertoires..."

# Répertoires d'entrée (surveillés)
INPUT_DIRS=(
    "data/input/compliance_docs"
    "data/input/audit_reports"
    "data/input/docs"
)

MISSING_DIRS=false
for dir in "${INPUT_DIRS[@]}"; do
    if [[ ! -d "$dir" ]]; then
        log_warning "  ⚠ Manquant: $dir"
        mkdir -p "$dir"
        log_info "    → Créé: $dir"
    else
        log_debug "  ✓ $dir"
    fi
done

# Répertoires de sortie
mkdir -p data/output/extracted
mkdir -p data/output/chunks
mkdir -p data/output/embeddings
mkdir -p logs
mkdir -p chroma_db

log_success "Répertoires OK"
echo ""

# -----------------------------------------------------------------------------
# AFFICHAGE DU MODE D'EXÉCUTION
# -----------------------------------------------------------------------------

case $MODE in
    watch)
        log_info "Mode SURVEILLANCE CONTINUE activé"
        echo "  → Le pipeline surveille les répertoires et traite les nouveaux fichiers"
        echo "  → Appuyez sur Ctrl+C pour arrêter"
        ;;
    once)
        log_info "Mode ONE-SHOT activé"
        echo "  → Le pipeline traite les fichiers existants une fois puis s'arrête"
        ;;
    dry-run)
        log_info "Mode SIMULATION activé"
        echo "  → Aucun fichier ne sera traité (simulation uniquement)"
        ;;
esac

echo ""

# -----------------------------------------------------------------------------
# DÉMARRAGE DU PIPELINE
# -----------------------------------------------------------------------------

log_info "Démarrage du pipeline RAG..."
echo "============================================================================="
echo ""

# Construction de la commande Python
# Utilise le point d'entrée défini dans pyproject.toml
PYTHON_CMD="rye run rag-pipeline"

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
    log_info "Mode surveillance continue activé"
    log_info "Le pipeline surveillera les répertoires en continu (Ctrl+C pour arrêter)"
    echo ""
    PYTHON_ARGS="$PYTHON_ARGS --watch"
elif [[ "$MODE" == "dry-run" ]]; then
    log_info "Mode simulation - Affichage du statut uniquement"
    PYTHON_ARGS="$PYTHON_ARGS --status"
fi

# Export du log level pour le framework Python
export RAG_LOG_LEVEL="$LOG_LEVEL"

# Exécution du pipeline
log_debug "Commande: $PYTHON_CMD $PYTHON_ARGS"
echo ""

# Exécution du pipeline
if $PYTHON_CMD $PYTHON_ARGS; then
    echo ""
    if [[ "$MODE" == "dry-run" ]]; then
        log_success "Simulation terminée (statut affiché)"
    else
        log_success "Pipeline terminé avec succès"
    fi
else
    EXIT_CODE=$?
    echo ""
    log_error "Pipeline terminé avec des erreurs (code: $EXIT_CODE)"
    log_error "Consultez les logs dans: logs/rag_audit.log"
    exit $EXIT_CODE
fi

echo ""
echo "============================================================================="
log_info "Pour relancer le pipeline: ./start.sh"
log_info "Pour voir l'aide: ./start.sh --help"
echo "============================================================================="
