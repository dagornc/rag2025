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
        """Extrait le texte avec Marker.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier PDF.

        Returns:
        -------
        ExtractionResult
            Résultat de l'extraction.
        """
        try:
            # Import tardif pour éviter erreur si librairie non installée
            from marker.convert import (  # type: ignore[import-untyped]
                convert_single_pdf,
            )
            from marker.models import load_all_models  # type: ignore[import-untyped]

            # Chargement des modèles ML de Marker
            # Note: Opération lente, pourrait être mise en cache
            logger.debug("Chargement des modèles Marker...")
            models = load_all_models()

            # Configuration Marker
            max_pages = self.config.get("max_pages", None)

            # Conversion du PDF
            logger.debug(f"Extraction Marker de {file_path.name}...")
            full_text, images, metadata_marker = convert_single_pdf(
                str(file_path),
                models,
                max_pages=max_pages,
            )

            # Métadonnées
            metadata = {
                "file_size": file_path.stat().st_size,
                "file_name": file_path.name,
                "extractor": "marker",
            }

            # Ajout métadonnées Marker
            if metadata_marker:
                metadata.update(metadata_marker)

            if images:
                metadata["images_extracted"] = len(images)

            # Marker a un score de confiance élevé (ML-based)
            confidence = 0.95 if full_text and len(full_text) > 100 else 0.6

            logger.debug(
                f"Marker: Extrait {len(full_text)} caractères "
                f"({len(images)} images) "
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
                "Marker n'est pas installé. Installez avec: pip install marker-pdf"
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
