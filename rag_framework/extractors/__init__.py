"""Module d'extraction de texte avec support de fallback."""

from rag_framework.extractors.base import BaseExtractor, ExtractionResult
from rag_framework.extractors.docling_extractor import DoclingExtractor
from rag_framework.extractors.image_extractor import ImageExtractor
from rag_framework.extractors.marker_extractor import MarkerExtractor
from rag_framework.extractors.pypdf2_extractor import PyPDF2Extractor
from rag_framework.extractors.text_extractor import TextExtractor
from rag_framework.extractors.vlm_extractor import VLMExtractor

__all__ = [
    "BaseExtractor",
    "DoclingExtractor",
    "ExtractionResult",
    "ImageExtractor",
    "MarkerExtractor",
    "PyPDF2Extractor",
    "TextExtractor",
    "VLMExtractor",
]
