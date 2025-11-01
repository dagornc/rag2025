"""Extracteur basé sur PyTesseract (OCR pour images et PDF scannés)."""

from pathlib import Path
from typing import Any, ClassVar

from rag_framework.extractors.base import BaseExtractor, ExtractionResult
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class OCRExtractor(BaseExtractor):
    """Extracteur utilisant PyTesseract (Tesseract OCR) pour extraire du texte.

    PyTesseract est l'interface Python pour Tesseract OCR, l'un des
    meilleurs moteurs OCR open-source en 2025. Idéal pour:
    - Images contenant du texte (photos de documents, captures d'écran)
    - PDF scannés (images de documents sans couche texte)
    - Documents manuscrits (avec modèles appropriés)

    Avantages:
    - Gratuit et open-source
    - Support de 100+ langues
    - Bonne précision pour texte imprimé
    - Détection automatique d'orientation
    - Support de multiples formats d'image

    Limitations:
    - Nécessite installation de Tesseract (binaire système)
    - Lent pour grandes images (utiliser redimensionnement)
    - Mauvais avec texte manuscrit non entraîné
    - Sensible à la qualité de l'image (résolution, contraste)

    Parameters
    ----------
    config : dict[str, Any]
        Configuration de l'extracteur.
        Clés supportées:
        - lang : str (défaut: "fra+eng") - Langues Tesseract (ex: "fra", "eng+fra")
        - psm : int (défaut: 3) - Page Segmentation Mode (0-13)
        - oem : int (défaut: 3) - OCR Engine Mode (0-3, 3=défaut+LSTM)
        - preprocess : bool (défaut: True) - Prétraitement d'image
        - dpi : int (défaut: 300) - DPI pour PDF conversion
        - min_confidence : float (défaut: 0.4) - Confiance minimale
        - min_text_length : int (défaut: 10)

    Notes
    -----
    PSM (Page Segmentation Mode) important:
    - 3: Automatic (défaut) - détection auto de layout
    - 6: Assume uniform block of text
    - 11: Sparse text (texte dispersé)
    - 12: Sparse text with OSD (Orientation and Script Detection)

    OEM (OCR Engine Mode):
    - 0: Legacy engine only
    - 1: Neural nets LSTM only
    - 2: Legacy + LSTM
    - 3: Default (basé sur disponibilité)
    """

    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {
        # Images
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".gif",
        ".tiff",
        ".tif",
        ".webp",
        # PDF (sera converti en images)
        ".pdf",
    }

    def can_extract(self, file_path: Path) -> bool:
        """Vérifie si le fichier est une image ou PDF supporté.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier.

        Returns
        -------
        bool
            True si le fichier a une extension supportée.

        Examples
        --------
        >>> extractor = OCRExtractor(config={})
        >>> extractor.can_extract(Path("scan.png"))
        True
        >>> extractor.can_extract(Path("document.pdf"))
        True
        >>> extractor.can_extract(Path("document.docx"))
        False
        """
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def extract(self, file_path: Path) -> ExtractionResult:
        """Extrait le texte d'une image ou PDF scanné avec OCR.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier.

        Returns
        -------
        ExtractionResult
            Résultat de l'extraction.

        Notes
        -----
        Pour les PDF, chaque page est convertie en image puis traitée par OCR.
        Pour les grandes images, un prétraitement est appliqué pour améliorer
        la qualité OCR.
        """
        try:
            # Import tardif pour éviter erreur si librairie non installée
            import pytesseract
            from PIL import Image

            # Options OCR
            lang = self.config.get("lang", "fra+eng")
            psm = self.config.get("psm", 3)  # Automatic page segmentation
            oem = self.config.get("oem", 3)  # Default OCR Engine Mode
            preprocess = self.config.get("preprocess", True)
            min_confidence = self.config.get("min_confidence", 0.4)

            # Configuration Tesseract
            custom_config = f"--oem {oem} --psm {psm}"

            # Traitement selon le type de fichier
            file_extension = file_path.suffix.lower()

            if file_extension == ".pdf":
                # PDF: conversion en images puis OCR
                return self._extract_from_pdf(
                    file_path, lang, custom_config, preprocess, min_confidence
                )
            else:
                # Image: OCR direct
                return self._extract_from_image(
                    file_path, lang, custom_config, preprocess, min_confidence
                )

        except ImportError as e:
            error_msg = f"Dépendance manquante: {e}. "
            if "pytesseract" in str(e):
                error_msg += "Installez avec: pip install pytesseract"
            elif "PIL" in str(e):
                error_msg += "Installez avec: pip install Pillow"
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
            error_msg = f"Erreur OCR extraction: {e}"
            logger.warning(error_msg)
            return ExtractionResult(
                text="",
                success=False,
                extractor_name=self.name,
                metadata={},
                error=error_msg,
                confidence_score=0.0,
            )

    def _extract_from_image(
        self,
        file_path: Path,
        lang: str,
        custom_config: str,
        preprocess: bool,
        min_confidence: float,
    ) -> ExtractionResult:
        """Extrait le texte d'une image avec OCR.

        Parameters
        ----------
        file_path : Path
            Chemin vers l'image.
        lang : str
            Langues Tesseract.
        custom_config : str
            Configuration Tesseract.
        preprocess : bool
            Appliquer le prétraitement.
        min_confidence : float
            Confiance minimale.

        Returns
        -------
        ExtractionResult
            Résultat de l'extraction.
        """
        import pytesseract
        from PIL import Image

        # Ouverture de l'image
        image = Image.open(str(file_path))

        # Prétraitement si activé
        if preprocess:
            image = self._preprocess_image(image)

        # Extraction OCR avec données détaillées
        data = pytesseract.image_to_data(
            image, lang=lang, config=custom_config, output_type=pytesseract.Output.DICT
        )

        # Filtrage par confiance et reconstruction du texte
        filtered_text = []
        confidences = []

        for i, conf in enumerate(data["conf"]):
            # Confiance -1 signifie pas de texte détecté
            if conf != -1:
                text = data["text"][i].strip()
                if text and int(conf) >= (min_confidence * 100):
                    filtered_text.append(text)
                    confidences.append(int(conf))

        full_text = " ".join(filtered_text)

        # Calcul de la confiance moyenne
        avg_confidence = (
            sum(confidences) / len(confidences) / 100 if confidences else 0.0
        )

        # Métadonnées
        metadata: dict[str, Any] = {
            "file_size": file_path.stat().st_size,
            "file_name": file_path.name,
            "extractor": "pytesseract",
            "image_size": f"{image.width}x{image.height}",
            "image_mode": image.mode,
            "words_detected": len(filtered_text),
            "avg_confidence": round(avg_confidence, 2),
            "lang": lang,
        }

        # Fermeture de l'image
        image.close()

        # Vérification de la longueur minimale
        min_length = self.config.get("min_text_length", 10)
        if len(full_text.strip()) < min_length:
            return ExtractionResult(
                text=full_text,
                success=False,
                extractor_name=self.name,
                metadata=metadata,
                error=f"Texte extrait trop court ({len(full_text)} < {min_length})",
                confidence_score=avg_confidence,
            )

        logger.debug(
            f"OCR: Extrait {len(full_text)} caractères "
            f"({len(filtered_text)} mots) "
            f"(confidence={avg_confidence:.2f})"
        )

        return ExtractionResult(
            text=full_text,
            success=True,
            extractor_name=self.name,
            metadata=metadata,
            confidence_score=avg_confidence,
        )

    def _extract_from_pdf(
        self,
        file_path: Path,
        lang: str,
        custom_config: str,
        preprocess: bool,
        min_confidence: float,
    ) -> ExtractionResult:
        """Extrait le texte d'un PDF scanné (conversion en images + OCR).

        Parameters
        ----------
        file_path : Path
            Chemin vers le PDF.
        lang : str
            Langues Tesseract.
        custom_config : str
            Configuration Tesseract.
        preprocess : bool
            Appliquer le prétraitement.
        min_confidence : float
            Confiance minimale.

        Returns
        -------
        ExtractionResult
            Résultat de l'extraction.
        """
        import pytesseract
        from pdf2image import convert_from_path

        # DPI pour conversion
        dpi = self.config.get("dpi", 300)

        # Conversion PDF en images
        images = convert_from_path(str(file_path), dpi=dpi)

        # OCR sur chaque page
        text_pages = []
        all_confidences = []

        for page_num, image in enumerate(images):
            # Prétraitement si activé
            if preprocess:
                image = self._preprocess_image(image)

            # Extraction OCR avec données détaillées
            data = pytesseract.image_to_data(
                image,
                lang=lang,
                config=custom_config,
                output_type=pytesseract.Output.DICT,
            )

            # Filtrage par confiance
            page_text = []
            for i, conf in enumerate(data["conf"]):
                if conf != -1:
                    text = data["text"][i].strip()
                    if text and int(conf) >= (min_confidence * 100):
                        page_text.append(text)
                        all_confidences.append(int(conf))

            if page_text:
                text_pages.append(
                    f"=== Page {page_num + 1} ===\n" + " ".join(page_text)
                )

        # Concaténation
        full_text = "\n\n".join(text_pages)

        # Calcul de la confiance moyenne
        avg_confidence = (
            sum(all_confidences) / len(all_confidences) / 100
            if all_confidences
            else 0.0
        )

        # Métadonnées
        metadata: dict[str, Any] = {
            "file_size": file_path.stat().st_size,
            "file_name": file_path.name,
            "extractor": "pytesseract",
            "num_pages": len(images),
            "words_detected": len(all_confidences),
            "avg_confidence": round(avg_confidence, 2),
            "lang": lang,
            "dpi": dpi,
        }

        # Vérification de la longueur minimale
        min_length = self.config.get("min_text_length", 10)
        if len(full_text.strip()) < min_length:
            return ExtractionResult(
                text=full_text,
                success=False,
                extractor_name=self.name,
                metadata=metadata,
                error=f"Texte extrait trop court ({len(full_text)} < {min_length})",
                confidence_score=avg_confidence,
            )

        logger.debug(
            f"OCR: Extrait {len(full_text)} caractères "
            f"depuis {len(images)} pages PDF "
            f"(confidence={avg_confidence:.2f})"
        )

        return ExtractionResult(
            text=full_text,
            success=True,
            extractor_name=self.name,
            metadata=metadata,
            confidence_score=avg_confidence,
        )

    def _preprocess_image(self, image: Any) -> Any:
        """Prétraite une image pour améliorer la qualité OCR.

        Parameters
        ----------
        image : PIL.Image
            Image à prétraiter.

        Returns
        -------
        PIL.Image
            Image prétraitée.

        Notes
        -----
        Applique:
        - Conversion en niveaux de gris
        - Augmentation du contraste
        - Réduction du bruit (optionnel)
        """
        from PIL import ImageEnhance

        # Conversion en niveaux de gris
        if image.mode != "L":
            image = image.convert("L")

        # Augmentation du contraste
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)

        # Augmentation de la netteté
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.3)

        return image
