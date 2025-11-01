"""Wrapper pour EasyOCR.

Auteur: RAG Framework Team
Version: 1.0.0
"""

from typing import Any, ClassVar

from rag_framework.preprocessing.ocr.base import OCREngine, OCRError


class EasyOCRWrapper(OCREngine):
    """Wrapper pour le moteur OCR EasyOCR.

    EasyOCR est précis et supporte de nombreuses langues.

    Attributes:
        REQUIRED_MODULES: Liste des modules requis.
    """

    REQUIRED_MODULES: ClassVar[list[str]] = ["easyocr"]

    def perform_ocr(self, file_path: str) -> dict[str, Any]:
        """Effectue l'OCR avec EasyOCR.

        Args:
            file_path: Chemin vers l'image ou PDF.

        Returns:
            Dictionnaire avec text et metadata.

        Raises:
            OCRError: Si l'OCR échoue.
        """
        try:
            import easyocr

            # Configuration
            languages = self.config.get("languages", ["fr", "en"])
            gpu = self.config.get("gpu", False)

            # Créer le reader
            reader = easyocr.Reader(languages, gpu=gpu)

            # Effectuer l'OCR
            results = reader.readtext(file_path)

            # Extraire le texte et la confiance
            text_parts = []
            confidences = []

            for bbox, text, confidence in results:
                text_parts.append(text)
                confidences.append(confidence)

            full_text = "\n".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return {
                "text": full_text,
                "metadata": {
                    "ocr_engine": "easyocr",
                    "languages": languages,
                    "confidence": avg_confidence,
                    "detections": len(results),
                },
            }

        except Exception as e:
            raise OCRError(f"Échec EasyOCR : {e}") from e
