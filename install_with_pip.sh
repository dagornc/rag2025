#!/usr/bin/env bash
# =============================================================================
# SCRIPT D'INSTALLATION ALTERNATIF - Utilisant pip au lieu de rye
# =============================================================================
# Pour les utilisateurs qui préfèrent utiliser pip directement.
#
# Usage:
#   ./install_with_pip.sh
#
# Auteur: RAG Team
# Version: 0.1.0
# =============================================================================

set -e
set -u
set -o pipefail

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
log_info "Installation du Framework RAG avec pip"
echo "============================================================================="
echo ""

# Vérification Python
log_info "Vérification de Python..."
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 n'est pas installé"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
log_info "Python version: ${PYTHON_VERSION}"
echo ""

# Vérification du venv
log_info "Vérification de l'environnement virtuel..."
if [[ ! -d ".venv" ]]; then
    log_info "Création de l'environnement virtuel..."
    python3 -m venv .venv
    log_success "Environnement virtuel créé"
else
    log_success "Environnement virtuel déjà existant"
fi
echo ""

# Activation de l'environnement virtuel
log_info "Activation de l'environnement virtuel..."
source .venv/bin/activate

# Mise à jour de pip
log_info "Mise à jour de pip..."
pip install --upgrade pip setuptools wheel

# Installation du framework
log_info "Installation du framework RAG..."
log_info "Cela peut prendre plusieurs minutes (téléchargement de modèles ML)..."
echo ""

if pip install -e .; then
    log_success "Framework RAG installé"
else
    log_error "Échec de l'installation"
    exit 1
fi
echo ""

# Création des répertoires
log_info "Création de l'arborescence..."

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
    mkdir -p "$dir"
    log_info "  ✓ $dir"
done

log_success "Arborescence créée"
echo ""

# Configuration .env
log_info "Configuration des variables d'environnement..."

if [[ ! -f ".env.example" ]]; then
    cat > .env.example << 'EOF'
# =============================================================================
# VARIABLES D'ENVIRONNEMENT - Framework RAG
# =============================================================================
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
HUGGINGFACE_API_KEY=hf_...
MISTRAL_API_KEY=...
EOF
    log_success ".env.example créé"
fi

if [[ ! -f ".env" ]]; then
    log_warning "Fichier .env introuvable"
    log_warning "Créez-le avec: cp .env.example .env && nano .env"
else
    log_success "Fichier .env détecté"
fi
echo ""

# Test d'import
log_info "Vérification de l'installation..."
if python -c "import rag_framework; print('OK')" &> /dev/null; then
    log_success "Package rag_framework importable"
else
    log_error "Impossible d'importer rag_framework"
    exit 1
fi
echo ""

# Résumé
echo "============================================================================="
log_success "INSTALLATION TERMINÉE"
echo "============================================================================="
echo ""
echo "Environnement virtuel:"
echo "  → $(pwd)/.venv"
echo ""
echo "Pour activer l'environnement:"
echo "  → source .venv/bin/activate"
echo ""
echo "Prochaines étapes:"
echo ""
echo "1. Configurer les clés API:"
echo "   → cp .env.example .env"
echo "   → nano .env"
echo ""
echo "2. Démarrer le pipeline:"
echo "   → source .venv/bin/activate"
echo "   → python -m rag_framework.cli"
echo "   → ou: ./start.sh"
echo ""
echo "3. Pour installer des bases vectorielles optionnelles:"
echo "   → pip install qdrant-client       # Qdrant"
echo "   → pip install psycopg2-binary     # pgvector"
echo "   → pip install pymilvus            # Milvus"
echo "   → pip install weaviate-client     # Weaviate"
echo ""
echo "============================================================================="
