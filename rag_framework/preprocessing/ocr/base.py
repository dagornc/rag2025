"""Classe de base abstraite pour tous les moteurs OCR.

Auteur: RAG Framework Team
Version: 1.0.0
"""

import importlib.util
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from rag_framework.exceptions import RAGFrameworkError
from rag_framework.utils.logger import get_logger


class OCRError(RAGFrameworkError):
    """Exception levée lors d'erreurs OCR."""

    pass


class OCREngine(ABC):
    """Classe de base abstraite pour tous les moteurs OCR.

    Attributes:
        config: Configuration spécifique du moteur OCR.
        priority: Priorité dans la chaîne de fallback.
        timeout: Timeout en secondes pour l'OCR.
        logger: Logger structuré.
    """

    REQUIRED_MODULES: list[str] = []

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise le moteur OCR.

        Args:
            config: Configuration du moteur.
        """
        self.config = config
        self.priority = config.get("priority", 99)
        self.timeout = config.get("timeout_seconds", 60)
        self.logger = get_logger(self.__class__.__name__)
        self._available = self._check_dependencies()

    def _check_dependencies(self) -> bool:
        """Vérifie les dépendances."""
        missing = []
        for module_name in self.REQUIRED_MODULES:
            if importlib.util.find_spec(module_name) is None:
                missing.append(module_name)

        if missing:
            self.logger.warning(
                f"{self.__class__.__name__} désactivé : modules manquants: {', '.join(missing)}"
            )
            return False
        return True

    def is_available(self) -> bool:
        """Indique si le moteur OCR est utilisable."""
        return self._available

    def extract_text(self, file_path: str) -> dict[str, Any]:
        """Extrait le texte d'une image ou PDF via OCR.

        Args:
            file_path: Chemin vers le fichier.

        Returns:
            Dictionnaire avec text et metadata.

        Raises:
            OCRError: Si l'OCR échoue.
        """
        if not self.is_available():
            raise OCRError(f"{self.__class__.__name__} non disponible")

        if not Path(file_path).exists():
            raise OCRError(f"Fichier introuvable : {file_path}")

        return self.perform_ocr(file_path)

    @abstractmethod
    def perform_ocr(self, file_path: str) -> dict[str, Any]:
        """Effectue l'OCR sur le fichier.

        Args:
            file_path: Chemin vers le fichier.

        Returns:
            Dictionnaire avec text et metadata.
        """
        pass
