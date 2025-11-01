#!/usr/bin/env bash

# =============================================================================
# SCRIPT DE NETTOYAGE DU CACHE PYTHON
# =============================================================================
# Supprime tous les fichiers cache Python pour forcer le rechargement du code.
# Utile après modification du code source pour s'assurer que les changements
# sont bien pris en compte.
#
# Usage:
#   ./clean_cache.sh
#
# Auteur: RAG Framework
# Version: 1.0.0
# =============================================================================

set -e

echo "🧹 Nettoyage du cache Python..."

# Supprimer les répertoires __pycache__
echo "  → Suppression des répertoires __pycache__..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Supprimer les fichiers .pyc
echo "  → Suppression des fichiers .pyc..."
find . -name "*.pyc" -delete 2>/dev/null || true

# Supprimer les fichiers .pyo
echo "  → Suppression des fichiers .pyo..."
find . -name "*.pyo" -delete 2>/dev/null || true

# Supprimer les caches de ruff, mypy, pytest
echo "  → Suppression des caches d'outils..."
rm -rf .ruff_cache .mypy_cache .pytest_cache 2>/dev/null || true

echo "✅ Cache Python nettoyé avec succès !"
echo ""
echo "Note: Relancez vos scripts pour charger le code à jour."
