"""Extracteur basé sur PyPDF2 (simple et rapide)."""

from pathlib import Path

from rag_framework.extractors.base import BaseExtractor, ExtractionResult
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class PyPDF2Extractor(BaseExtractor):
    """Extracteur utilisant PyPDF2 pour l'extraction basique de PDF.

    Avantages:
    - Rapide et léger
    - Pas de dépendances externes
    - Fonctionne bien pour PDF textuels simples

    Limitations:
    - Ne gère pas les PDF scannés (images)
    - Mauvais avec les mises en page complexes
    - Pas d'extraction de tableaux ou images

    Parameters
    ----------
    config : dict[str, Any]
        Configuration de l'extracteur.
        Clés supportées :
        - min_text_length : int (défaut: 10)
        - extract_metadata : bool (défaut: True)
    """

    def can_extract(self, file_path: Path) -> bool:
        """Vérifie si le fichier est un PDF.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier.

        Returns:
        -------
        bool
            True si le fichier a l'extension .pdf.
        """
        return file_path.suffix.lower() == ".pdf"

    def extract(self, file_path: Path) -> ExtractionResult:
        """Extrait le texte d'un PDF avec PyPDF2.

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
            from pypdf import PdfReader

            # Ouverture du fichier PDF en mode binaire
            with open(file_path, "rb") as pdf_file:
                # Création du lecteur PDF
                pdf_reader = PdfReader(pdf_file)

                # Extraction du texte de toutes les pages
                text_pages = []
                for _page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_pages.append(page_text)

                # Concaténation de toutes les pages
                full_text = "\n\n".join(text_pages)

                # Métadonnées du PDF
                metadata = {
                    "num_pages": len(pdf_reader.pages),
                    "file_size": file_path.stat().st_size,
                    "file_name": file_path.name,
                }

                # Extraction des métadonnées PDF si disponibles
                if self.config.get("extract_metadata", True) and pdf_reader.metadata:
                    pdf_meta = pdf_reader.metadata
                    if pdf_meta.title:
                        metadata["title"] = pdf_meta.title
                    if pdf_meta.author:
                        metadata["author"] = pdf_meta.author
                    if pdf_meta.creation_date:
                        metadata["creation_date"] = str(pdf_meta.creation_date)

                # Calcul du score de confiance basé sur la densité de texte
                # Heuristique: plus de texte extrait = meilleure confiance
                char_per_page = (
                    len(full_text) / len(pdf_reader.pages)
                    if len(pdf_reader.pages) > 0
                    else 0
                )
                # Score entre 0.0 et 1.0 (100 chars/page = score 0.5)
                confidence = min(1.0, char_per_page / 200.0)

                logger.debug(
                    f"PyPDF2: Extrait {len(full_text)} caractères "
                    f"depuis {len(pdf_reader.pages)} pages "
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
            error_msg = "pypdf n'est pas installé. Installez avec: pip install pypdf"
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
            error_msg = f"Erreur PyPDF2 extraction: {e}"
            logger.warning(error_msg)
            return ExtractionResult(
                text="",
                success=False,
                extractor_name=self.name,
                metadata={},
                error=error_msg,
                confidence_score=0.0,
            )
