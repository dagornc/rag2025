#!/usr/bin/env bash
# =============================================================================
# SCRIPT D'INSTALLATION - Framework RAG Audit & Conformité
# =============================================================================
# Installation complète du framework avec gestion des dépendances via rye.
# Ce script configure l'environnement, installe les dépendances et prépare
# les répertoires nécessaires au fonctionnement du pipeline.
#
# Usage:
#   ./install.sh [--dev]
#
# Options:
#   --dev    Installe également les dépendances de développement (ruff, pytest, mypy)
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
MIN_PYTHON_VERSION="3.9"
PROJECT_NAME="rag_framework"
DEV_MODE=false

# Couleurs pour affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

version_compare() {
    # Compare deux versions (format X.Y.Z)
    # Retourne 0 si $1 >= $2, 1 sinon
    if [[ "$1" == "$2" ]]; then
        return 0
    fi

    local IFS=.
    local i ver1=($1) ver2=($2)

    for ((i=0; i<${#ver1[@]}; i++)); do
        if [[ -z ${ver2[i]} ]]; then
            return 0
        fi
        if ((10#${ver1[i]} > 10#${ver2[i]})); then
            return 0
        fi
        if ((10#${ver1[i]} < 10#${ver2[i]})); then
            return 1
        fi
    done
    return 0
}

# -----------------------------------------------------------------------------
# VÉRIFICATIONS PRÉLIMINAIRES
# -----------------------------------------------------------------------------

log_info "Démarrage de l'installation du Framework RAG..."
echo ""

# Parse des arguments
for arg in "$@"; do
    case $arg in
        --dev)
            DEV_MODE=true
            log_info "Mode développement activé"
            ;;
        *)
            log_error "Argument inconnu: $arg"
            echo "Usage: ./install.sh [--dev]"
            exit 1
            ;;
    esac
done

# Vérification Python
log_info "Vérification de Python..."
if ! check_command python3; then
    log_error "Python 3 n'est pas installé"
    log_error "Veuillez installer Python ${MIN_PYTHON_VERSION}+ depuis https://www.python.org/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
log_info "Python version détectée: ${PYTHON_VERSION}"

if ! version_compare "${PYTHON_VERSION}" "${MIN_PYTHON_VERSION}"; then
    log_error "Python ${MIN_PYTHON_VERSION}+ requis (détecté: ${PYTHON_VERSION})"
    exit 1
fi

log_success "Python ${PYTHON_VERSION} OK"
echo ""

# -----------------------------------------------------------------------------
# INSTALLATION DE RYE
# -----------------------------------------------------------------------------

log_info "Vérification de rye..."
if ! check_command rye; then
    log_warning "rye n'est pas installé. Installation en cours..."

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if check_command brew; then
            log_info "Installation via Homebrew..."
            brew install rye
        else
            log_info "Installation via curl..."
            curl -sSf https://rye-up.com/get | bash -s -- --yes

            # Sourcer le fichier de configuration rye
            if [[ -f "$HOME/.rye/env" ]]; then
                source "$HOME/.rye/env"
            fi
            export PATH="$HOME/.rye/shims:$PATH"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        log_info "Installation via curl..."
        curl -sSf https://rye-up.com/get | bash -s -- --yes

        # Sourcer le fichier de configuration rye
        if [[ -f "$HOME/.rye/env" ]]; then
            source "$HOME/.rye/env"
        fi
        export PATH="$HOME/.rye/shims:$PATH"
    else
        log_error "Système d'exploitation non supporté: $OSTYPE"
        log_error "Veuillez installer rye manuellement: https://rye-up.com/"
        exit 1
    fi

    # Vérification post-installation
    if ! check_command rye; then
        log_error "L'installation de rye a échoué ou nécessite un rechargement du shell"
        echo ""
        log_warning "Installation manuelle requise:"
        echo ""
        echo "  1. Installer rye:"
        echo "     curl -sSf https://rye-up.com/get | bash"
        echo ""
        echo "  2. Ajouter rye au PATH (exécutez dans votre terminal):"
        echo "     source \"$HOME/.rye/env\""
        echo ""
        echo "  3. Relancer ce script:"
        echo "     ./install.sh"
        echo ""
        exit 1
    fi

    log_success "rye installé avec succès"
else
    log_success "rye déjà installé"
fi

RYE_VERSION=$(rye --version | cut -d' ' -f2)
log_info "rye version: ${RYE_VERSION}"
echo ""

# -----------------------------------------------------------------------------
# SYNCHRONISATION DES DÉPENDANCES
# -----------------------------------------------------------------------------

log_info "Synchronisation des dépendances avec rye..."
log_info "Cela peut prendre plusieurs minutes..."

# Synchronisation des dépendances principales
if rye sync; then
    log_success "Dépendances principales installées"
else
    log_error "Échec de l'installation des dépendances"
    exit 1
fi

# Installation des dépendances de développement si --dev
if [[ "$DEV_MODE" == true ]]; then
    log_info "Installation des dépendances de développement..."
    if rye sync --all-features; then
        log_success "Dépendances de développement installées"
    else
        log_warning "Échec partiel des dépendances de développement"
    fi
fi

echo ""

# -----------------------------------------------------------------------------
# INSTALLATION DE PRE-COMMIT
# -----------------------------------------------------------------------------

if [[ "$DEV_MODE" == true ]]; then
    log_info "Configuration de pre-commit..."

    if [[ -f ".pre-commit-config.yaml" ]]; then
        if rye run pre-commit install; then
            log_success "pre-commit configuré"
        else
            log_warning "Échec de la configuration pre-commit (non bloquant)"
        fi
    else
        log_warning "Fichier .pre-commit-config.yaml introuvable (skip)"
    fi

    echo ""
fi

# -----------------------------------------------------------------------------
# CRÉATION DES RÉPERTOIRES
# -----------------------------------------------------------------------------

log_info "Création de l'arborescence des répertoires..."

# Répertoires pour les données
DIRECTORIES=(
    "data/input/compliance_docs"
    "data/input/audit_reports"
    "data/input/docs"
    "data/output/extracted"
    "data/output/chunks"
    "data/output/embeddings"
    "logs"
    "chroma_db"
)

for dir in "${DIRECTORIES[@]}"; do
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
        log_info "  ✓ Créé: $dir"
    else
        log_info "  ✓ Existe: $dir"
    fi
done

log_success "Arborescence créée"
echo ""

# -----------------------------------------------------------------------------
# VÉRIFICATION DES FICHIERS DE CONFIGURATION
# -----------------------------------------------------------------------------

log_info "Vérification des fichiers de configuration..."

CONFIG_FILES=(
    "config/global.yaml"
    "config/01_monitoring.yaml"
    "config/02_preprocessing.yaml"
    "config/03_chunking.yaml"
    "config/04_enrichment.yaml"
    "config/05_audit.yaml"
    "config/06_embedding.yaml"
    "config/07_normalization.yaml"
    "config/08_vector_storage.yaml"
)

MISSING_CONFIG=false
for config in "${CONFIG_FILES[@]}"; do
    if [[ ! -f "$config" ]]; then
        log_error "  ✗ Manquant: $config"
        MISSING_CONFIG=true
    else
        log_info "  ✓ OK: $config"
    fi
done

if [[ "$MISSING_CONFIG" == true ]]; then
    log_error "Fichiers de configuration manquants"
    exit 1
fi

log_success "Configuration OK"
echo ""

# -----------------------------------------------------------------------------
# VÉRIFICATION DES VARIABLES D'ENVIRONNEMENT
# -----------------------------------------------------------------------------

log_info "Vérification des variables d'environnement..."

# Créer .env.example si n'existe pas
if [[ ! -f ".env.example" ]]; then
    log_info "Création de .env.example..."
    cat > .env.example << 'EOF'
# =============================================================================
# VARIABLES D'ENVIRONNEMENT - Framework RAG
# =============================================================================
# Copiez ce fichier vers .env et renseignez vos clés API

# OpenAI API Key (pour GPT-4, embeddings, vision)
OPENAI_API_KEY=sk-...

# Anthropic API Key (pour Claude 3)
ANTHROPIC_API_KEY=sk-ant-...

# Hugging Face API Key (pour modèles HF)
HUGGINGFACE_API_KEY=hf_...

# Mistral AI API Key
MISTRAL_API_KEY=...

# Autres providers (optionnels)
GENERIC_API_KEY=...
EOF
    log_success ".env.example créé"
fi

# Vérifier si .env existe
if [[ ! -f ".env" ]]; then
    log_warning "Fichier .env introuvable"
    log_warning "Copiez .env.example vers .env et renseignez vos clés API:"
    log_warning "  cp .env.example .env"
    log_warning "  nano .env"
else
    log_success "Fichier .env détecté"
fi

echo ""

# -----------------------------------------------------------------------------
# VÉRIFICATION DE L'INSTALLATION
# -----------------------------------------------------------------------------

log_info "Vérification de l'installation..."

# Test d'import du package
if rye run python -c "import rag_framework; print('OK')" &> /dev/null; then
    log_success "Package rag_framework importable"
else
    log_error "Impossible d'importer rag_framework"
    log_error "L'installation a échoué"
    exit 1
fi

echo ""

# -----------------------------------------------------------------------------
# TESTS DE QUALITÉ (mode dev uniquement)
# -----------------------------------------------------------------------------

if [[ "$DEV_MODE" == true ]]; then
    log_info "Exécution des tests de qualité..."

    # Ruff format check
    log_info "  • Vérification du formatage (ruff format)..."
    if rye run ruff format --check . &> /dev/null; then
        log_success "    ✓ Formatage OK"
    else
        log_warning "    ⚠ Formatage à corriger (non bloquant)"
    fi

    # Ruff lint check
    log_info "  • Vérification du linting (ruff check)..."
    if rye run ruff check . &> /dev/null; then
        log_success "    ✓ Linting OK"
    else
        log_warning "    ⚠ Problèmes de linting détectés (non bloquant)"
    fi

    # Mypy type checking
    log_info "  • Vérification du typage (mypy)..."
    if rye run mypy rag_framework &> /dev/null; then
        log_success "    ✓ Typage OK"
    else
        log_warning "    ⚠ Erreurs de typage détectées (non bloquant)"
    fi

    echo ""
fi

# -----------------------------------------------------------------------------
# RÉSUMÉ DE L'INSTALLATION
# -----------------------------------------------------------------------------

echo "============================================================================="
log_success "INSTALLATION TERMINÉE AVEC SUCCÈS"
echo "============================================================================="
echo ""
echo "Framework RAG Audit & Conformité installé dans:"
echo "  → $(pwd)"
echo ""
echo "Environnement virtuel géré par rye:"
echo "  → $(rye show --path 2>/dev/null || echo 'Utiliser: rye show --path')"
echo ""
echo "Prochaines étapes:"
echo ""
echo "1. Configurer vos clés API (si nécessaire):"
echo "   → Éditer le fichier .env avec vos clés OpenAI, Anthropic, etc."
echo ""
echo "2. Ajuster la configuration (optionnel):"
echo "   → config/global.yaml           (activation des étapes, providers LLM)"
echo "   → config/02_preprocessing.yaml (profil d'extraction, mode VLM)"
echo "   → config/06_embedding.yaml     (modèle d'embeddings)"
echo ""
echo "3. Démarrer le pipeline:"
echo "   → ./start.sh"
echo ""
if [[ "$DEV_MODE" == true ]]; then
echo "4. Développement (mode --dev activé):"
echo "   → rye run ruff format .        (Formater le code)"
echo "   → rye run ruff check .         (Vérifier le linting)"
echo "   → rye run mypy .               (Vérifier le typage)"
echo "   → rye run pytest               (Lancer les tests)"
echo ""
fi
echo "Documentation:"
echo "   → README.md"
echo "   → config/README_EXTENSIONS_SUPPORTEES.md"
echo "   → GEMINI.md (charte qualité)"
echo ""
echo "============================================================================="
