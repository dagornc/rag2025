"""Optimiseur mémoire pour le preprocessing.

Auteur: RAG Framework Team
Version: 1.0.0
"""

import gc
from typing import Any

from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryOptimizer:
    """Gestionnaire d'optimisation mémoire pour le preprocessing.

    Attributes:
        config: Configuration de l'optimisation mémoire.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise l'optimiseur.

        Args:
            config: Configuration memory_optimization depuis parser.yaml.
        """
        self.config = config
        self.enabled = config.get("enabled", True)
        self.strategies = config.get("strategies", {})

    def force_gc(self) -> None:
        """Force le garbage collection."""
        if not self.enabled:
            return

        gc_config = self.strategies.get("garbage_collection", {})
        if gc_config.get("enabled", True):
            gc.collect()
            logger.debug("Garbage collection forcé")

    def should_use_streaming(self, file_size_mb: float) -> bool:
        """Détermine si le streaming doit être utilisé.

        Args:
            file_size_mb: Taille du fichier en MB.

        Returns:
            True si le streaming est recommandé.
        """
        if not self.enabled:
            return False

        streaming_config = self.strategies.get("streaming", {})
        if not streaming_config.get("enabled", True):
            return False

        # Utiliser streaming pour fichiers > 10MB par défaut
        threshold = streaming_config.get("buffer_size_mb", 10)
        return file_size_mb > threshold

    def should_use_mmap(self, file_size_mb: float) -> bool:
        """Détermine si memory mapping doit être utilisé.

        Args:
            file_size_mb: Taille du fichier en MB.

        Returns:
            True si mmap est recommandé.
        """
        if not self.enabled:
            return False

        mmap_config = self.strategies.get("memory_mapping", {})
        if not mmap_config.get("enabled", True):
            return False

        threshold = mmap_config.get("threshold_mb", 50)
        return file_size_mb > threshold
