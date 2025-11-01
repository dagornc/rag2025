"""Tests pour la gestion d'erreur OSD dans l'extracteur Docling.

Ce module teste la robustesse de l'extracteur Docling face aux erreurs
OSD (Orientation and Script Detection) de Tesseract.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rag_framework.extractors.docling_extractor import DoclingExtractor


class TestDoclingOSDError:
    """Tests de gestion d'erreur OSD pour l'extracteur Docling."""

    def test_osd_error_with_skip_enabled(self) -> None:
        """Teste que l'extracteur réessaie sans OSD si erreur OSD et skip activé.

        Vérifie que :
        1. L'erreur OSD est détectée
        2. Un retry sans OSD est tenté
        3. L'extraction réussit au second essai
        """
        # Arrange
        config = {
            "ocr_enabled": True,
            "ocr_lang": ["fra"],
            "ocr_skip_osd": True,  # Skip OSD activé
            "ocr_psm": 3,
        }
        extractor = DoclingExtractor(config)

        # Créer un fichier temporaire pour le test
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")  # Header PDF minimal
            test_file = Path(tmp.name)

        try:
            # Mock du DocumentConverter (patché au niveau de docling, pas de l'extracteur)
            with patch(
                "docling.document_converter.DocumentConverter"
            ) as mock_converter_class:
                # Premier appel : lever une erreur OSD
                mock_converter_first = MagicMock()
                mock_converter_first.convert.side_effect = Exception(
                    "OSD failed (doc test_document.pdf, page: 1): Too few characters"
                )

                # Second appel : réussir
                mock_converter_second = MagicMock()
                mock_result = MagicMock()
                # Texte >= 50 chars pour passer la validation min_text_length
                mock_result.document.export_to_markdown.return_value = (
                    "Texte extrait avec succès " + "x" * 50
                )
                mock_converter_second.convert.return_value = mock_result

                # Configurer le mock pour retourner les deux convertisseurs
                mock_converter_class.side_effect = [
                    mock_converter_first,
                    mock_converter_second,
                ]

                # Act
                result = extractor.extract(test_file)

                # Assert
                assert result.success is True
                assert "Texte extrait avec succès" in result.text
                assert len(result.text) >= 50  # Validation min_text_length
                assert result.extractor_name == "docling"
                assert mock_converter_class.call_count == 2  # 2 tentatives
        finally:
            # Cleanup : supprimer le fichier temporaire
            test_file.unlink(missing_ok=True)

    def test_osd_error_with_skip_disabled(self) -> None:
        """Teste que l'erreur OSD est propagée si skip désactivé.

        Vérifie que :
        1. L'erreur OSD est détectée
        2. Aucun retry n'est tenté
        3. L'exception est propagée
        """
        # Arrange
        config = {
            "ocr_enabled": True,
            "ocr_lang": ["fra"],
            "ocr_skip_osd": False,  # Skip OSD désactivé
            "ocr_psm": 3,
        }
        extractor = DoclingExtractor(config)
        test_file = Path("test_document.pdf")

        # Mock du DocumentConverter (patché au niveau de docling, pas de l'extracteur)
        with patch(
            "docling.document_converter.DocumentConverter"
        ) as mock_converter_class:
            mock_converter = MagicMock()
            mock_converter.convert.side_effect = Exception(
                "OSD failed: Too few characters"
            )
            mock_converter_class.return_value = mock_converter

            # Act
            result = extractor.extract(test_file)

            # Assert
            assert result.success is False
            assert "OSD failed" in (result.error or "")
            assert mock_converter_class.call_count == 1  # 1 seule tentative

    def test_non_osd_error_propagation(self) -> None:
        """Teste que les erreurs non-OSD sont propagées normalement.

        Vérifie que :
        1. Les erreurs non liées à OSD ne déclenchent pas de retry
        2. L'erreur originale est préservée
        """
        # Arrange
        config = {
            "ocr_enabled": True,
            "ocr_lang": ["fra"],
            "ocr_skip_osd": True,
            "ocr_psm": 3,
        }
        extractor = DoclingExtractor(config)
        test_file = Path("test_document.pdf")

        # Mock du DocumentConverter (patché au niveau de docling, pas de l'extracteur)
        with patch(
            "docling.document_converter.DocumentConverter"
        ) as mock_converter_class:
            mock_converter = MagicMock()
            mock_converter.convert.side_effect = Exception(
                "File not found: test_document.pdf"
            )
            mock_converter_class.return_value = mock_converter

            # Act
            result = extractor.extract(test_file)

            # Assert
            assert result.success is False
            assert "File not found" in (result.error or "")
            assert mock_converter_class.call_count == 1  # Pas de retry

    def test_osd_error_detection_variants(self) -> None:
        """Teste la détection de différentes variantes d'erreur OSD.

        Vérifie que toutes les formes d'erreur OSD sont détectées :
        - "OSD failed"
        - "too few characters"
        - "orientation"
        """
        config = {
            "ocr_enabled": True,
            "ocr_lang": ["fra"],
            "ocr_skip_osd": True,
            "ocr_psm": 3,
        }
        extractor = DoclingExtractor(config)

        # Créer un fichier temporaire pour le test
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")  # Header PDF minimal
            test_file = Path(tmp.name)

        osd_error_variants = [
            "OSD failed (doc test.pdf, page: 1)",
            "Warning: Too few characters. Skipping this page",
            "Error: orientation detection failed",
            "OSD FAILED: orientation and script detection failed",
        ]

        try:
            for error_msg in osd_error_variants:
                with patch(
                    "docling.document_converter.DocumentConverter"
                ) as mock_converter_class:
                    # Premier appel : lever erreur OSD
                    mock_converter_first = MagicMock()
                    mock_converter_first.convert.side_effect = Exception(error_msg)

                    # Second appel : réussir
                    mock_converter_second = MagicMock()
                    mock_result = MagicMock()
                    # Texte >= 50 chars pour passer la validation min_text_length
                    mock_result.document.export_to_markdown.return_value = (
                        "Texte OK " + "y" * 50
                    )
                    mock_converter_second.convert.return_value = mock_result

                    mock_converter_class.side_effect = [
                        mock_converter_first,
                        mock_converter_second,
                    ]

                    # Act
                    result = extractor.extract(test_file)

                    # Assert
                    assert result.success is True, (
                        f"Échec détection erreur OSD: {error_msg}"
                    )
                    assert mock_converter_class.call_count == 2, (
                        f"Pas de retry pour: {error_msg}"
                    )
        finally:
            # Cleanup : supprimer le fichier temporaire
            test_file.unlink(missing_ok=True)


# =============================================================================
# BLOC 2 : EXEMPLE D'EXÉCUTION
# =============================================================================

if __name__ == "__main__":
    """Exécution des tests avec pytest."""
    import sys

    # Exécuter les tests
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


# =============================================================================
# BLOC 4 : SUGGESTIONS LEAN V2
# =============================================================================

"""
Axes d'amélioration continue possibles :

1. **Tests d'intégration réels**
   - Ajouter tests avec vrais PDFs problématiques
   - Mesurer le temps d'exécution avec/sans OSD
   - Comparer qualité d'extraction avec/sans OSD

2. **Métriques de performance**
   - Tracer le nombre d'erreurs OSD par batch
   - Monitorer le taux de succès du fallback
   - Alerter si taux d'échec > seuil

3. **Configuration dynamique**
   - Désactiver auto OSD si échec répété (>3 fois)
   - Ajuster PSM selon le type de document
   - Learning : mémoriser quel extracteur fonctionne par format

4. **Logging enrichi**
   - Ajouter structured logging (JSON)
   - Tracer la chaîne de fallback complète
   - Exporter métriques vers Prometheus/Grafana

5. **Resilience avancée**
   - Circuit breaker sur extracteur Docling
   - Backoff exponentiel sur retry
   - Health check pré-extraction (test Tesseract disponible)
"""
