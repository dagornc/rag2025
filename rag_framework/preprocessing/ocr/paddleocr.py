"""Wrapper pour PaddleOCR.

Auteur: RAG Framework Team
Version: 1.0.0
"""

from typing import Any, ClassVar

from rag_framework.preprocessing.ocr.base import OCREngine, OCRError


class PaddleOCRWrapper(OCREngine):
    """Wrapper pour le moteur OCR PaddleOCR.

    PaddleOCR est rapide et efficace pour le chinois et l'anglais.

    Attributes:
        REQUIRED_MODULES: Liste des modules requis.
    """

    REQUIRED_MODULES: ClassVar[list[str]] = ["paddleocr"]

    def perform_ocr(self, file_path: str) -> dict[str, Any]:
        """Effectue l'OCR avec PaddleOCR.

        Args:
            file_path: Chemin vers l'image ou PDF.

        Returns:
            Dictionnaire avec text et metadata.

        Raises:
            OCRError: Si l'OCR échoue.
        """
        try:
            from paddleocr import PaddleOCR

            # Configuration
            lang = self.config.get("lang", "fr")
            use_gpu = self.config.get("use_gpu", False)

            # Créer l'OCR
            ocr = PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=use_gpu)

            # Effectuer l'OCR
            results = ocr.ocr(file_path, cls=True)

            # Extraire le texte et la confiance
            text_parts = []
            confidences = []

            if results and results[0]:
                for line in results[0]:
                    if line:
                        bbox, (text, confidence) = line
                        text_parts.append(text)
                        confidences.append(confidence)

            full_text = "\n".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return {
                "text": full_text,
                "metadata": {
                    "ocr_engine": "paddleocr",
                    "language": lang,
                    "confidence": avg_confidence,
                    "detections": len(text_parts),
                },
            }

        except Exception as e:
            raise OCRError(f"Échec PaddleOCR : {e}") from e
