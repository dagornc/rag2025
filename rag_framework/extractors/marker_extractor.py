"""Extracteur basé sur Marker (extraction haute qualité avec ML)."""

from pathlib import Path

from rag_framework.extractors.base import BaseExtractor, ExtractionResult
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class MarkerExtractor(BaseExtractor):
    """Extracteur utilisant Marker pour extraction ML de haute qualité.

    Marker utilise des modèles de machine learning pour extraire le texte
    avec une précision supérieure, en préservant la structure et le formatage.

    Avantages:
    - Qualité d'extraction supérieure (ML-based)
    - Excellente gestion des PDF complexes
    - Préserve la structure (titres, listes, etc.)
    - Bonne gestion des équations et formules

    Limitations:
    - Le plus lent des extracteurs
    - Nécessite beaucoup de ressources (GPU recommandé)
    - Dépendances lourdes (PyTorch, etc.)

    Parameters
    ----------
    config : dict[str, Any]
        Configuration de l'extracteur.
        Clés supportées:
        - use_gpu : bool (défaut: False)
        - batch_size : int (défaut: 1)
        - max_pages : int (défaut: None)

    Notes:
    -----
    Utilise marker-pdf v1.10+ avec la nouvelle API PdfConverter.
    Compatible avec marker >= 1.10.1
    """

    def can_extract(self, file_path: Path) -> bool:
        """Vérifie si Marker peut traiter ce fichier.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier.

        Returns:
        -------
        bool
            True si le fichier est un PDF.
        """
        # Marker se spécialise dans les PDF
        return file_path.suffix.lower() == ".pdf"

    def extract(self, file_path: Path) -> ExtractionResult:
        """Extrait le texte avec Marker (nouvelle API v1.10+).

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier PDF.

        Returns:
        -------
        ExtractionResult
            Résultat de l'extraction.

        Notes:
        -----
        Migration vers marker-pdf v1.10+ API:
        - Ancienne API: marker.convert.convert_single_pdf (obsolète)
        - Nouvelle API: marker.converters.pdf.PdfConverter (v1.10+)
        """
        try:
            # Import tardif pour éviter erreur si librairie non installée
            from marker.converters.pdf import (  # type: ignore[import-untyped]
                PdfConverter,
            )
            from marker.models import (  # type: ignore[import-untyped]
                create_model_dict,
            )

            # Création du dictionnaire de modèles (artifact_dict)
            # Note: Opération lente, pourrait être mise en cache
            logger.debug("Chargement des modèles Marker...")
            artifact_dict = create_model_dict()

            # Configuration du converter
            # processor_list: None = utilise les processeurs par défaut
            # renderer: None = utilise le renderer markdown par défaut
            # llm_service: None = pas de service LLM externe
            converter = PdfConverter(
                artifact_dict=artifact_dict,
                processor_list=None,  # Utilise processeurs par défaut
                renderer=None,  # Utilise renderer par défaut (markdown)
                llm_service=None,  # Pas de LLM externe
                config=None,  # Pas de config custom
            )

            # Conversion du PDF
            logger.debug(f"Extraction Marker de {file_path.name}...")
            rendered_output = converter(str(file_path))

            # Le résultat est un FullyRenderedDocument ou équivalent
            # Extraction du texte markdown
            if hasattr(rendered_output, "markdown"):
                full_text = rendered_output.markdown
            elif hasattr(rendered_output, "text"):
                full_text = rendered_output.text
            else:
                # Fallback: conversion string
                full_text = str(rendered_output)

            # Métadonnées
            metadata = {
                "file_size": file_path.stat().st_size,
                "file_name": file_path.name,
                "extractor": "marker",
                "marker_version": "1.10+",
            }

            # Extraction métadonnées supplémentaires si disponibles
            if hasattr(rendered_output, "metadata"):
                metadata.update(rendered_output.metadata)

            # Extraction images si disponibles
            if hasattr(rendered_output, "images") and rendered_output.images:
                metadata["images_extracted"] = len(rendered_output.images)

            # Marker a un score de confiance élevé (ML-based)
            confidence = 0.95 if full_text and len(full_text) > 100 else 0.6

            logger.debug(
                f"Marker: Extrait {len(full_text)} caractères "
                f"(confidence={confidence:.2f})"
            )

            return ExtractionResult(
                text=full_text,
                success=True,
                extractor_name=self.name,
                metadata=metadata,
                confidence_score=confidence,
            )

        except ImportError:
            error_msg = (
                "Marker n'est pas installé. "
                "Installez avec: pip install marker-pdf>=1.10.1"
            )
            logger.error(error_msg)
            return ExtractionResult(
                text="",
                success=False,
                extractor_name=self.name,
                metadata={},
                error=error_msg,
                confidence_score=0.0,
            )

        except Exception as e:
            error_msg = f"Erreur Marker extraction: {e}"
            logger.warning(error_msg)
            return ExtractionResult(
                text="",
                success=False,
                extractor_name=self.name,
                metadata={},
                error=error_msg,
                confidence_score=0.0,
            )
