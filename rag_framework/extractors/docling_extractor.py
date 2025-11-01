"""Extracteur basé sur Docling (extraction avancée)."""

from pathlib import Path

from rag_framework.extractors.base import BaseExtractor, ExtractionResult
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class DoclingExtractor(BaseExtractor):
    """Extracteur utilisant Docling pour l'extraction avancée de documents.

    Avantages:
    - Gère bien les mises en page complexes
    - Extraction de tableaux structurés
    - Support de multiples formats (PDF, DOCX, etc.)
    - OCR intégré pour PDF scannés

    Limitations:
    - Plus lent que PyPDF2
    - Dépendances plus lourdes
    - Nécessite plus de ressources

    Parameters
    ----------
    config : dict[str, Any]
        Configuration de l'extracteur.
        Clés supportées:
        - ocr_enabled : bool (défaut: True)
        - preserve_layout : bool (défaut: True)
        - extract_tables : bool (défaut: True)
        - extract_images : bool (défaut: False)
    """

    def can_extract(self, file_path: Path) -> bool:
        """Vérifie si Docling peut traiter ce fichier.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier.

        Returns:
        -------
        bool
            True si le fichier a une extension supportée.

        Examples:
        --------
        >>> extractor = DoclingExtractor(config={})
        >>> extractor.can_extract(Path("report.docx"))
        True
        >>> extractor.can_extract(Path("image.png"))
        False
        """
        # Docling supporte de nombreux formats de documents
        supported_extensions = {
            # PDF et formats similaires
            ".pdf",
            ".ps",
            ".epub",
            # Microsoft Office Word
            ".doc",
            ".docx",
            ".docm",
            # Microsoft Office PowerPoint
            ".ppt",
            ".pptx",
            ".pptm",
            # Microsoft Office Excel
            ".xls",
            ".xlsx",
            ".xlsm",
            # LibreOffice/OpenDocument
            ".odt",  # Text
            ".odp",  # Presentation
            ".ods",  # Spreadsheet (ajouté)
            # Autres formats de documents
            ".rtf",
        }
        return file_path.suffix.lower() in supported_extensions

    def extract(self, file_path: Path) -> ExtractionResult:
        """Extrait le texte avec Docling.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier.

        Returns:
        -------
        ExtractionResult
            Résultat de l'extraction.
        """
        # Import tardif pour éviter erreur si librairie non installée
        try:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import (
                PdfPipelineOptions,
                TesseractCliOcrOptions,  # CLI Tesseract (pas tesserocr)
            )
            from docling.document_converter import DocumentConverter, PdfFormatOption
        except ImportError as e:
            error_msg = (
                f"Impossible d'importer Docling ou ses dépendances: {e}. "
                "Installez avec: pip install docling"
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

        try:
            # Capture des métadonnées du fichier AVANT traitement
            # (le fichier peut être déplacé pendant/après la conversion)
            file_size = file_path.stat().st_size
            file_name = file_path.name
            file_format = file_path.suffix[1:]

            # Configuration OCR pour utiliser Tesseract CLI au lieu d'ocrmac
            # Récupération de la langue depuis config (défaut: fra pour français)
            # NOTE: lang doit être une LISTE de langues, pas une string
            ocr_lang = self.config.get("ocr_lang", ["fra"])

            # Convertir en liste si c'est une string (ex: "fra" → ["fra"])
            if isinstance(ocr_lang, str):
                ocr_lang = [ocr_lang]

            # Récupération des paramètres OSD (Orientation & Script Detection)
            ocr_skip_osd = self.config.get("ocr_skip_osd", True)
            ocr_psm = self.config.get("ocr_psm", 3)  # PSM 3 = auto sans OSD

            # Options Tesseract CLI OCR (utilise le binaire système, pas tesserocr)
            tesseract_options = TesseractCliOcrOptions(lang=ocr_lang)

            # Options pour le pipeline PDF avec Tesseract
            pdf_options = PdfPipelineOptions(
                do_ocr=True,
                ocr_options=tesseract_options,
            )

            # Création du convertisseur avec options Tesseract
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)
                }
            )

            # Conversion du document avec gestion d'erreur OSD
            # Le convertisseur utilise maintenant Tesseract pour l'OCR
            result = None
            try:
                result = converter.convert(str(file_path))

            except Exception as conv_error:
                # Vérifier si c'est une erreur OSD
                error_str = str(conv_error).lower()
                is_osd_error = (
                    "osd failed" in error_str
                    or "too few characters" in error_str
                    or "orientation" in error_str
                )

                if is_osd_error and ocr_skip_osd:
                    # Erreur OSD détectée et skip_osd activé : réessayer sans OSD
                    logger.warning(
                        f"OSD failed pour {file_path.name}, "
                        f"réessai sans OSD (PSM {ocr_psm})..."
                    )

                    # Recréer convertisseur avec PSM sans OSD (PSM 3 par défaut)
                    # Note: Docling ne permet pas de passer PSM directement,
                    # mais désactiver OSD évite le problème
                    pdf_options_no_osd = PdfPipelineOptions(
                        do_ocr=True,
                        ocr_options=tesseract_options,
                    )

                    converter_no_osd = DocumentConverter(
                        format_options={
                            InputFormat.PDF: PdfFormatOption(
                                pipeline_options=pdf_options_no_osd
                            )
                        }
                    )

                    try:
                        result = converter_no_osd.convert(str(file_path))
                        logger.info(
                            f"Extraction réussie sans OSD pour {file_path.name}"
                        )
                    except Exception as retry_error:
                        logger.error(
                            f"Échec extraction même sans OSD: {retry_error}",
                            exc_info=True,
                        )
                        raise retry_error
                else:
                    # Autre erreur ou skip_osd désactivé : propager l'exception
                    raise conv_error

            # Si result est toujours None, lever une exception
            if result is None:
                raise RuntimeError("La conversion a échoué sans résultat")

            # Vérifier que le document existe et contient des données
            if not hasattr(result, "document") or result.document is None:
                raise RuntimeError("Document Docling invalide ou vide")

            # Extraction du texte
            full_text = result.document.export_to_markdown()

            # Vérifier que le texte n'est pas vide ou trop court
            min_length = self.config.get("min_text_length", 50)
            if not full_text or len(full_text.strip()) < min_length:
                raise RuntimeError(
                    f"Texte extrait trop court ou vide "
                    f"({len(full_text) if full_text else 0} < {min_length} chars). "
                    f"Docling a peut-être rencontré des erreurs internes."
                )

            # Métadonnées (utilise les valeurs capturées avant traitement)
            metadata = {
                "file_size": file_size,
                "file_name": file_name,
                "format": file_format,
            }

            # Ajout métadonnées Docling si disponibles
            if hasattr(result.document, "metadata"):
                doc_meta = result.document.metadata
                if hasattr(doc_meta, "num_pages"):
                    metadata["num_pages"] = doc_meta.num_pages
                if hasattr(doc_meta, "tables_count"):
                    metadata["tables_count"] = doc_meta.tables_count

            # Score de confiance élevé pour Docling (OCR + layout analysis)
            confidence = 0.9 if full_text and len(full_text) > 100 else 0.5

            logger.debug(
                f"Docling: Extrait {len(full_text)} caractères "
                f"(confidence={confidence:.2f})"
            )

            return ExtractionResult(
                text=full_text,
                success=True,
                extractor_name=self.name,
                metadata=metadata,
                confidence_score=confidence,
            )

        except Exception as e:
            error_msg = f"Erreur Docling extraction: {e}"
            # Logger avec traceback complet pour debugging
            logger.warning(error_msg, exc_info=True)
            return ExtractionResult(
                text="",
                success=False,
                extractor_name=self.name,
                metadata={},
                error=error_msg,
                confidence_score=0.0,
            )
