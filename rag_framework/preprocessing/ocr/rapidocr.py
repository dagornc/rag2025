"""Wrapper pour RapidOCR.

Auteur: RAG Framework Team
Version: 1.0.0
"""

from typing import Any, ClassVar

from rag_framework.preprocessing.ocr.base import OCREngine, OCRError


class RapidOCRWrapper(OCREngine):
    """Wrapper pour le moteur OCR RapidOCR.

    RapidOCR est ultra rapide avec ONNX Runtime.

    Attributes:
        REQUIRED_MODULES: Liste des modules requis.
    """

    REQUIRED_MODULES: ClassVar[list[str]] = ["rapidocr_onnxruntime"]

    def perform_ocr(self, file_path: str) -> dict[str, Any]:
        """Effectue l'OCR avec RapidOCR.

        Args:
            file_path: Chemin vers l'image ou PDF.

        Returns:
            Dictionnaire avec text et metadata.

        Raises:
            OCRError: Si l'OCR échoue.
        """
        try:
            from rapidocr_onnxruntime import RapidOCR

            # Créer l'OCR
            ocr = RapidOCR()

            # Effectuer l'OCR
            result, elapse = ocr(file_path)

            # Extraire le texte et la confiance
            text_parts = []
            confidences = []

            if result:
                for item in result:
                    # Format: [bbox, text, confidence]
                    if len(item) >= 3:
                        bbox, text, confidence = item[0], item[1], item[2]
                        text_parts.append(text)
                        confidences.append(confidence)

            full_text = "\n".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return {
                "text": full_text,
                "metadata": {
                    "ocr_engine": "rapidocr",
                    "confidence": avg_confidence,
                    "detections": len(text_parts),
                    "processing_time_ms": elapse,
                },
            }

        except Exception as e:
            raise OCRError(f"Échec RapidOCR : {e}") from e
