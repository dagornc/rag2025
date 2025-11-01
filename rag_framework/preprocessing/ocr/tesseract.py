"""Wrapper pour Tesseract OCR.

Auteur: RAG Framework Team
Version: 1.0.0
"""

from typing import Any

from rag_framework.preprocessing.ocr.base import OCREngine, OCRError


class TesseractOCRWrapper(OCREngine):
    """Wrapper pour le moteur OCR Tesseract.

    Tesseract est le moteur OCR open source standard.

    Attributes:
        REQUIRED_MODULES: Liste des modules requis.
    """

    REQUIRED_MODULES = ["pytesseract", "PIL"]

    def perform_ocr(self, file_path: str) -> dict[str, Any]:
        """Effectue l'OCR avec Tesseract.

        Args:
            file_path: Chemin vers l'image ou PDF.

        Returns:
            Dictionnaire avec text et metadata.

        Raises:
            OCRError: Si l'OCR échoue.
        """
        try:
            import pytesseract
            from PIL import Image

            # Configuration Tesseract
            lang = self.config.get("language", "fra+eng")
            config_str = self.config.get("config", "--psm 3 --oem 3")

            # Ouvrir l'image
            image = Image.open(file_path)

            # Effectuer l'OCR
            text = pytesseract.image_to_string(image, lang=lang, config=config_str)

            return {
                "text": text,
                "metadata": {
                    "ocr_engine": "tesseract",
                    "language": lang,
                    "confidence": None,  # Tesseract ne fournit pas facilement la confidence
                },
            }

        except Exception as e:
            raise OCRError(f"Échec Tesseract OCR : {e}") from e
