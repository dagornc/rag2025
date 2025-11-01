#!/usr/bin/env python3
"""Script de vérification des dépendances des extracteurs de fallback.

Ce script vérifie que toutes les dépendances nécessaires pour les extracteurs
du système de fallback sont installées et fonctionnelles.

Usage:
    python check_dependencies.py
    # ou
    rye run python check_dependencies.py
"""

import sys
from typing import Any


def check_import(module_name: str, package_name: str | None = None) -> bool:
    """Vérifie si un module peut être importé.

    Args:
        module_name: Nom du module à importer (ex: "PyPDF2")
        package_name: Nom du package pip (ex: "pypdf2") si différent du module

    Returns:
        True si le module est importable, False sinon
    """
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def get_version(module_name: str) -> str:
    """Récupère la version d'un module.

    Args:
        module_name: Nom du module

    Returns:
        Version du module ou "unknown"
    """
    try:
        module = __import__(module_name)
        return getattr(module, "__version__", "unknown")
    except Exception:
        return "unknown"


def main() -> None:
    """Point d'entrée principal."""
    print("=" * 80)
    print("VÉRIFICATION DES DÉPENDANCES - Extracteurs de Fallback")
    print("=" * 80)
    print()

    # Définition des dépendances par extracteur (meilleures pratiques 2025)
    dependencies: dict[str, list[tuple[str, str | None, str]]] = {
        "TextExtractor": [
            ("Python standard library", None, "Aucune dépendance externe"),
        ],
        "PandasExtractor": [
            ("pandas", "pandas", "Traitement de données CSV/Excel"),
            ("openpyxl", "openpyxl", "Support Excel (.xlsx)"),
        ],
        "HTMLExtractor": [
            ("bs4", "beautifulsoup4", "Parsing HTML/XML"),
            ("lxml", "lxml", "Parser XML rapide (optionnel mais recommandé)"),
        ],
        "DocxExtractor": [
            ("docx", "python-docx", "Extraction Word (.docx)"),
        ],
        "PptxExtractor": [
            ("pptx", "python-pptx", "Extraction PowerPoint (.pptx)"),
        ],
        "PyMuPDFExtractor": [
            ("fitz", "pymupdf", "Extraction PDF rapide"),
        ],
        "PdfPlumberExtractor": [
            ("pdfplumber", "pdfplumber", "Extraction PDF avec tableaux avancés"),
        ],
        "PyPDF2Extractor": [
            ("pypdf", "pypdf", "Extraction de PDF simples"),
        ],
        "DoclingExtractor": [
            ("docling", "docling", "Extraction avancée (OCR, tableaux)"),
        ],
        "MarkerExtractor": [
            ("marker_pdf", "marker-pdf", "Extraction ML haute qualité"),
        ],
        "OCRExtractor": [
            (
                "pytesseract",
                "pytesseract",
                "OCR Tesseract (nécessite tesseract binaire)",
            ),
            ("PIL", "Pillow", "Traitement d'images"),
            ("pdf2image", "pdf2image", "Conversion PDF → images"),
        ],
        "ImageExtractor (VLM)": [
            ("PIL", "Pillow", "Lecture et manipulation d'images"),
            ("openai", "openai", "API OpenAI pour VLM (optionnel)"),
        ],
        "VLMExtractor": [
            ("PIL", "Pillow", "Conversion PDF → images"),
            ("pdf2image", "pdf2image", "Conversion PDF → images"),
            ("openai", "openai", "API OpenAI pour VLM (optionnel)"),
        ],
    }

    results: dict[str, dict[str, Any]] = {}
    total_deps = 0
    installed_deps = 0

    # Vérification de chaque extracteur
    for extractor_name, deps in dependencies.items():
        print(f"📦 {extractor_name}")
        print("-" * 80)

        extractor_status = {"total": len(deps), "installed": 0, "missing": []}

        for module_name, package_name, description in deps:
            total_deps += 1

            # Skip pour Python standard library
            if module_name == "Python standard library":
                print(f"  ✅ {description}")
                extractor_status["installed"] += 1
                installed_deps += 1
                continue

            # Vérification du module
            is_installed = check_import(module_name)

            if is_installed:
                version = get_version(module_name)
                print(f"  ✅ {module_name} ({version}) - {description}")
                extractor_status["installed"] += 1
                installed_deps += 1
            else:
                pkg_name = package_name or module_name
                print(f"  ❌ {module_name} MANQUANT - {description}")
                print(f"     → Installation: pip install {pkg_name}")
                extractor_status["missing"].append(pkg_name)

        results[extractor_name] = extractor_status
        print()

    # Résumé global
    print("=" * 80)
    print("RÉSUMÉ")
    print("=" * 80)
    print(f"Total de dépendances vérifiées: {total_deps}")
    print(f"Dépendances installées: {installed_deps}/{total_deps}")
    print()

    # Résumé par extracteur
    for extractor_name, status in results.items():
        icon = "✅" if status["installed"] == status["total"] else "⚠️"
        print(
            f"{icon} {extractor_name}: "
            f"{status['installed']}/{status['total']} dépendances"
        )

    print()

    # Liste des dépendances manquantes
    all_missing = []
    for status in results.values():
        all_missing.extend(status["missing"])

    if all_missing:
        print("=" * 80)
        print("⚠️  DÉPENDANCES MANQUANTES")
        print("=" * 80)
        print()
        print("Les dépendances suivantes sont manquantes:")
        for pkg in sorted(set(all_missing)):
            print(f"  • {pkg}")
        print()
        print("Pour installer toutes les dépendances manquantes:")
        print(f"  rye add {' '.join(sorted(set(all_missing)))}")
        print()
        print("Ou avec pip:")
        print(f"  pip install {' '.join(sorted(set(all_missing)))}")
        print()
        sys.exit(1)
    else:
        print("=" * 80)
        print("✅ TOUTES LES DÉPENDANCES SONT INSTALLÉES")
        print("=" * 80)
        print()
        print("Tous les extracteurs de fallback sont opérationnels!")
        print()
        sys.exit(0)


if __name__ == "__main__":
    main()
