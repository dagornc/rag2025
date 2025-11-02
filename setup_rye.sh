#!/usr/bin/env bash
# =============================================================================
# SCRIPT DE CONFIGURATION RYE
# =============================================================================
# Ce script installe rye et configure le PATH automatiquement.
# =============================================================================

set -e

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

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

echo "============================================================================="
log_info "Configuration de rye pour le Framework RAG"
echo "============================================================================="
echo ""

# Détecter le shell
SHELL_RC=""
if [[ -n "$ZSH_VERSION" ]]; then
    SHELL_RC="$HOME/.zshrc"
    SHELL_NAME="zsh"
elif [[ -n "$BASH_VERSION" ]]; then
    SHELL_RC="$HOME/.bashrc"
    SHELL_NAME="bash"
else
    SHELL_RC="$HOME/.profile"
    SHELL_NAME="shell"
fi

log_info "Shell détecté: $SHELL_NAME"
log_info "Fichier de configuration: $SHELL_RC"
echo ""

# Vérifier si rye est déjà installé
if command -v rye &> /dev/null; then
    log_success "rye est déjà installé !"
    rye --version
    echo ""
    log_info "Passage à l'installation du framework..."
    sleep 1
    exec ./install.sh
    exit 0
fi

# Installation de rye
log_info "Installation de rye..."
echo ""

if curl -sSf https://rye-up.com/get | bash -s -- --yes; then
    log_success "rye installé avec succès"
else
    log_error "Échec de l'installation de rye"
    exit 1
fi

echo ""

# Configuration du PATH
log_info "Configuration du PATH dans $SHELL_RC..."

# Vérifier si la ligne existe déjà
if grep -q 'source "$HOME/.rye/env"' "$SHELL_RC" 2>/dev/null; then
    log_info "PATH déjà configuré dans $SHELL_RC"
else
    echo "" >> "$SHELL_RC"
    echo '# Rye package manager' >> "$SHELL_RC"
    echo 'source "$HOME/.rye/env"' >> "$SHELL_RC"
    log_success "PATH ajouté à $SHELL_RC"
fi

echo ""

# Sourcer l'environnement rye
log_info "Chargement de l'environnement rye..."
if [[ -f "$HOME/.rye/env" ]]; then
    source "$HOME/.rye/env"
    log_success "Environnement rye chargé"
else
    log_error "Fichier $HOME/.rye/env introuvable"
    exit 1
fi

echo ""

# Vérifier que rye est accessible
log_info "Vérification de l'installation..."
if command -v rye &> /dev/null; then
    log_success "rye est accessible !"
    rye --version
else
    log_error "rye n'est pas dans le PATH"
    log_warning "Rechargez votre shell:"
    echo "  source $SHELL_RC"
    exit 1
fi

echo ""
echo "============================================================================="
log_success "RYE CONFIGURÉ AVEC SUCCÈS"
echo "============================================================================="
echo ""
log_info "Lancement de l'installation du Framework RAG..."
echo ""
sleep 2

# Lancer install.sh
exec ./install.sh
