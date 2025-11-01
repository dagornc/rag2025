"""Extracteur basé sur PyMuPDF/fitz (extraction rapide et performante)."""

from pathlib import Path
from typing import Any, ClassVar

from rag_framework.extractors.base import BaseExtractor, ExtractionResult
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class PyMuPDFExtractor(BaseExtractor):
    """Extracteur utilisant PyMuPDF (fitz) pour l'extraction rapide de PDF.

    PyMuPDF (fitz) est l'un des extracteurs PDF les plus rapides et performants
    disponibles en 2025. Il est particulièrement adapté pour:
    - PDF textuels avec mise en page simple à modérée
    - Extraction rapide de grandes quantités de documents
    - Obtention de métadonnées détaillées

    Avantages:
    - Très rapide (10-100x plus rapide que pypdf)
    - Excellente gestion de l'encodage et des polices
    - Extraction de métadonnées riches
    - Support des annotations et formulaires
    - Faible consommation mémoire

    Limitations:
    - Pas d'OCR intégré (PDF scannés non supportés)
    - Extraction de tableaux basique (utiliser pdfplumber pour mieux)
    - Dépendance binaire (peut nécessiter compilation)

    Parameters
    ----------
    config : dict[str, Any]
        Configuration de l'extracteur.
        Clés supportées:
        - extract_images : bool (défaut: False)
        - extract_tables : bool (défaut: False)
        - preserve_layout : bool (défaut: True)
        - min_text_length : int (défaut: 10)
        - extract_metadata : bool (défaut: True)
    """

    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {".pdf"}

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

        Examples:
        --------
        >>> extractor = PyMuPDFExtractor(config={})
        >>> extractor.can_extract(Path("document.pdf"))
        True
        >>> extractor.can_extract(Path("document.docx"))
        False
        """
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def extract(self, file_path: Path) -> ExtractionResult:
        """Extrait le texte d'un PDF avec PyMuPDF.

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
        PyMuPDF extrait le texte page par page en préservant l'ordre
        de lecture naturel. Les options de configuration permettent
        d'ajuster le niveau de préservation de la mise en page.
        """
        try:
            # Import tardif pour éviter erreur si librairie non installée
            import fitz  # PyMuPDF

            # Ouverture du document PDF
            doc = fitz.open(str(file_path))

            # Options d'extraction
            preserve_layout = self.config.get("preserve_layout", True)

            # Extraction du texte de toutes les pages
            text_pages = []
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)

                # Extraction avec ou sans préservation de la mise en page
                if preserve_layout:
                    # "text" mode preserve layout mieux que "html" ou "dict"
                    page_text = page.get_text("text")
                else:
                    # Mode "blocks" pour extraction plus rapide sans layout
                    page_text = page.get_text("blocks")
                    # Extraction du texte de chaque bloc
                    page_text = "\n".join(
                        block[4] for block in page_text if isinstance(block[4], str)
                    )

                if page_text and page_text.strip():
                    text_pages.append(page_text)

            # Concaténation de toutes les pages
            full_text = "\n\n".join(text_pages)

            # Métadonnées du PDF
            metadata: dict[str, Any] = {
                "num_pages": len(doc),
                "file_size": file_path.stat().st_size,
                "file_name": file_path.name,
                "extractor": "pymupdf",
            }

            # Extraction des métadonnées PDF si demandé
            if self.config.get("extract_metadata", True):
                pdf_meta = doc.metadata
                if pdf_meta:
                    # PyMuPDF retourne un dict avec clés standard
                    if pdf_meta.get("title"):
                        metadata["title"] = pdf_meta["title"]
                    if pdf_meta.get("author"):
                        metadata["author"] = pdf_meta["author"]
                    if pdf_meta.get("subject"):
                        metadata["subject"] = pdf_meta["subject"]
                    if pdf_meta.get("creator"):
                        metadata["creator"] = pdf_meta["creator"]
                    if pdf_meta.get("producer"):
                        metadata["producer"] = pdf_meta["producer"]
                    if pdf_meta.get("creationDate"):
                        metadata["creation_date"] = pdf_meta["creationDate"]
                    if pdf_meta.get("modDate"):
                        metadata["modification_date"] = pdf_meta["modDate"]

            # Fermeture du document
            doc.close()

            # Vérification de la longueur minimale
            min_length = self.config.get("min_text_length", 10)
            if len(full_text.strip()) < min_length:
                return ExtractionResult(
                    text=full_text,
                    success=False,
                    extractor_name=self.name,
                    metadata=metadata,
                    error=f"Texte extrait trop court ({len(full_text)} < {min_length})",
                    confidence_score=0.1,
                )

            # Calcul du score de confiance basé sur la densité de texte
            # PyMuPDF est généralement très fiable pour les PDF textuels
            char_per_page = len(full_text) / len(doc) if len(doc) > 0 else 0  # type: ignore

            # Score élevé si bonne densité de texte (> 200 chars/page = 0.9)
            if char_per_page > 200:
                confidence = 0.95
            elif char_per_page > 100:
                confidence = 0.8
            elif char_per_page > 50:
                confidence = 0.6
            else:
                # Faible densité = potentiellement PDF scanné
                confidence = 0.3

            logger.debug(
                f"PyMuPDF: Extrait {len(full_text)} caractères "
                f"depuis {metadata['num_pages']} pages "
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
                "PyMuPDF n'est pas installé. Installez avec: pip install pymupdf"
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
            error_msg = f"Erreur PyMuPDF extraction: {e}"
            logger.warning(error_msg)
            return ExtractionResult(
                text="",
                success=False,
                extractor_name=self.name,
                metadata={},
                error=error_msg,
                confidence_score=0.0,
            )
