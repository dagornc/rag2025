#!/usr/bin/env bash

# =============================================================================
# SCRIPT DE SYNCHRONISATION GIT AUTOMATIQUE
# =============================================================================
# Lance la surveillance watchdog et la synchronisation automatique avec GitHub
#
# Prérequis:
#   - Variable d'environnement GITHUB_TOKEN définie dans .env
#   - Configuration dans config/synchrogithub.yaml
#   - Repository Git initialisé avec remote configuré
#
# Usage:
#   ./sync_github.sh              # Lance en mode foreground
#   ./sync_github.sh --daemon     # Lance en background
#   ./sync_github.sh --stop       # Arrête le daemon
#
# Auteur: RAG Framework
# Version: 1.0.0
# =============================================================================

set -euo pipefail

# Couleurs pour l'affichage
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Fichiers et répertoires
readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly CONFIG_FILE="${PROJECT_ROOT}/config/synchrogithub.yaml"
readonly PID_FILE="${PROJECT_ROOT}/.git_sync.pid"
readonly LOG_FILE="${PROJECT_ROOT}/logs/git_sync.log"

# -----------------------------------------------------------------------------
# Fonctions utilitaires
# -----------------------------------------------------------------------------

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

check_prerequisites() {
    log_info "Vérification des prérequis..."

    # Vérifier que le répertoire est un repo Git
    if [ ! -d "${PROJECT_ROOT}/.git" ]; then
        log_error "Ce répertoire n'est pas un repository Git"
        log_error "Initialiser avec: git init && git remote add origin <url>"
        exit 1
    fi

    # Vérifier que le remote est configuré
    if ! git remote get-url origin &> /dev/null; then
        log_error "Aucun remote 'origin' configuré"
        log_error "Ajouter avec: git remote add origin <url>"
        exit 1
    fi

    # Vérifier que le fichier de configuration existe
    if [ ! -f "${CONFIG_FILE}" ]; then
        log_error "Fichier de configuration introuvable: ${CONFIG_FILE}"
        exit 1
    fi

    # Vérifier que GITHUB_TOKEN est défini
    if [ -z "${GITHUB_TOKEN:-}" ]; then
        log_warning "Variable GITHUB_TOKEN non définie"
        log_info "Tentative de chargement depuis .env..."

        if [ -f "${PROJECT_ROOT}/.env" ]; then
            # shellcheck disable=SC1091
            source "${PROJECT_ROOT}/.env"

            if [ -z "${GITHUB_TOKEN:-}" ]; then
                log_error "GITHUB_TOKEN introuvable dans .env"
                exit 1
            fi
        else
            log_error "Fichier .env introuvable et GITHUB_TOKEN non défini"
            exit 1
        fi
    fi

    # Vérifier que Python et rye sont disponibles
    if ! command -v rye &> /dev/null; then
        log_error "rye n'est pas installé"
        log_error "Installer avec: curl -sSf https://rye.astral.sh/get | bash"
        exit 1
    fi

    log_success "Tous les prérequis sont satisfaits"
}

create_log_directory() {
    local log_dir
    log_dir="$(dirname "${LOG_FILE}")"

    if [ ! -d "${log_dir}" ]; then
        log_info "Création du répertoire de logs: ${log_dir}"
        mkdir -p "${log_dir}"
    fi
}

start_sync() {
    log_info "Démarrage de la synchronisation Git automatique..."

    # Vérifier si déjà en cours
    if [ -f "${PID_FILE}" ]; then
        local old_pid
        old_pid=$(cat "${PID_FILE}")

        if ps -p "${old_pid}" > /dev/null 2>&1; then
            log_error "La synchronisation est déjà en cours (PID: ${old_pid})"
            log_info "Arrêter avec: ./sync_github.sh --stop"
            exit 1
        else
            log_warning "Fichier PID obsolète trouvé, suppression..."
            rm -f "${PID_FILE}"
        fi
    fi

    create_log_directory

    log_info "Configuration: ${CONFIG_FILE}"
    log_info "Logs: ${LOG_FILE}"
    log_info ""
    log_success "Synchronisation démarrée avec succès"
    log_info "Appuyez sur Ctrl+C pour arrêter"
    log_info ""

    # Lancer le script Python de synchronisation
    # TODO: Implémenter rag_framework/git_sync/watcher.py
    cd "${PROJECT_ROOT}" || exit 1
    rye run python -m rag_framework.git_sync.watcher \
        --config "${CONFIG_FILE}" \
        --log-file "${LOG_FILE}"
}

start_daemon() {
    log_info "Démarrage de la synchronisation en mode daemon..."

    # Vérifier si déjà en cours
    if [ -f "${PID_FILE}" ]; then
        local old_pid
        old_pid=$(cat "${PID_FILE}")

        if ps -p "${old_pid}" > /dev/null 2>&1; then
            log_error "La synchronisation est déjà en cours (PID: ${old_pid})"
            exit 1
        else
            rm -f "${PID_FILE}"
        fi
    fi

    create_log_directory

    # Lancer en background avec nohup
    cd "${PROJECT_ROOT}" || exit 1
    nohup rye run python -m rag_framework.git_sync.watcher \
        --config "${CONFIG_FILE}" \
        --log-file "${LOG_FILE}" \
        > "${LOG_FILE}" 2>&1 &

    local pid=$!
    echo "${pid}" > "${PID_FILE}"

    log_success "Synchronisation démarrée en background (PID: ${pid})"
    log_info "Logs: ${LOG_FILE}"
    log_info "Arrêter avec: ./sync_github.sh --stop"
}

stop_daemon() {
    log_info "Arrêt de la synchronisation..."

    if [ ! -f "${PID_FILE}" ]; then
        log_warning "Aucun processus de synchronisation en cours"
        exit 0
    fi

    local pid
    pid=$(cat "${PID_FILE}")

    if ps -p "${pid}" > /dev/null 2>&1; then
        log_info "Arrêt du processus ${pid}..."
        kill "${pid}"

        # Attendre jusqu'à 10 secondes
        local count=0
        while ps -p "${pid}" > /dev/null 2>&1 && [ ${count} -lt 10 ]; do
            sleep 1
            ((count++))
        done

        # Force kill si nécessaire
        if ps -p "${pid}" > /dev/null 2>&1; then
            log_warning "Arrêt forcé du processus..."
            kill -9 "${pid}"
        fi

        rm -f "${PID_FILE}"
        log_success "Synchronisation arrêtée"
    else
        log_warning "Le processus ${pid} n'existe plus"
        rm -f "${PID_FILE}"
    fi
}

show_status() {
    log_info "Statut de la synchronisation Git:"
    echo ""

    if [ -f "${PID_FILE}" ]; then
        local pid
        pid=$(cat "${PID_FILE}")

        if ps -p "${pid}" > /dev/null 2>&1; then
            log_success "En cours d'exécution (PID: ${pid})"

            # Afficher les dernières lignes du log
            if [ -f "${LOG_FILE}" ]; then
                echo ""
                log_info "Dernières lignes du log:"
                tail -n 10 "${LOG_FILE}"
            fi
        else
            log_warning "Arrêtée (fichier PID obsolète)"
        fi
    else
        log_info "Arrêtée"
    fi

    echo ""
    log_info "Configuration: ${CONFIG_FILE}"
    log_info "Logs: ${LOG_FILE}"
}

show_usage() {
    cat << EOF
Usage: ${0} [OPTIONS]

Lance la synchronisation Git automatique avec surveillance watchdog.

OPTIONS:
    (aucune)        Lance en mode foreground (logs dans le terminal)
    --daemon        Lance en background (logs dans ${LOG_FILE})
    --stop          Arrête le daemon
    --status        Affiche le statut de la synchronisation
    --help          Affiche cette aide

EXEMPLES:
    ${0}                  # Lance en foreground
    ${0} --daemon         # Lance en background
    ${0} --stop           # Arrête le daemon
    ${0} --status         # Statut

CONFIGURATION:
    Fichier: ${CONFIG_FILE}
    Token GitHub: Variable GITHUB_TOKEN dans .env

EOF
}

# -----------------------------------------------------------------------------
# Point d'entrée principal
# -----------------------------------------------------------------------------

main() {
    cd "${PROJECT_ROOT}" || exit 1

    # Parser les arguments
    case "${1:-}" in
        --daemon)
            check_prerequisites
            start_daemon
            ;;
        --stop)
            stop_daemon
            ;;
        --status)
            show_status
            ;;
        --help|-h)
            show_usage
            ;;
        "")
            check_prerequisites
            start_sync
            ;;
        *)
            log_error "Option inconnue: ${1}"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Gestion du Ctrl+C
trap 'echo ""; log_info "Interruption reçue, arrêt..."; exit 0' SIGINT SIGTERM

main "$@"
