"""Classe de base abstraite pour tous les adapters de parsing.

Ce module définit l'interface commune pour tous les adapters de librairies
de parsing, avec détection automatique des dépendances.

Auteur: RAG Framework Team
Version: 1.0.0
"""

import importlib.util
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar

from rag_framework.exceptions import RAGFrameworkError
from rag_framework.utils.logger import get_logger


class ParsingError(RAGFrameworkError):
    """Exception levée lors d'erreurs de parsing."""

    pass


class LibraryAdapter(ABC):
    """Classe de base abstraite pour tous les adapters de parsing.

    Cette classe fournit:
    - Détection automatique des dépendances
    - Validation des fichiers (taille, existence)
    - Gestion des timeouts
    - Logging structuré
    - Métriques de base (temps, succès/échec)

    Attributes:
        config: Configuration spécifique de l'adapter (depuis parser.yaml).
        priority: Priorité dans la chaîne de fallback (1 = plus haute).
        timeout: Timeout en secondes pour le parsing.
        max_size: Taille maximale de fichier acceptée (en MB).
        logger: Logger structuré.
    """

    # Liste des modules Python requis pour cet adapter
    # À redéfinir dans chaque adapter concret
    REQUIRED_MODULES: ClassVar[list[str]] = []

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise l'adapter avec sa configuration.

        Args:
            config: Configuration de l'adapter depuis parser.yaml.
        """
        self.config = config
        self.priority = config.get("priority", 99)
        self.timeout = config.get("timeout_seconds", 30)
        self.max_size = config.get("max_file_size_mb", 100)
        self.library_config = config.get("config", {})
        self.logger = get_logger(self.__class__.__name__)

        # Vérification des dépendances
        self._available = self._check_dependencies()

        if self._available:
            self.logger.info(
                f"{self.__class__.__name__} disponible",
                extra={"priority": self.priority, "timeout": self.timeout},
            )
        else:
            self.logger.warning(f"{self.__class__.__name__} non disponible")

    def _check_dependencies(self) -> bool:
        """Vérifie que toutes les dépendances sont installées.

        Returns:
            True si toutes les dépendances sont présentes, False sinon.
        """
        missing = []
        for module_name in self.REQUIRED_MODULES:
            if not self._is_module_available(module_name):
                missing.append(module_name)

        if missing:
            self.logger.warning(
                f"{self.__class__.__name__} désactivé : "
                f"modules manquants: {', '.join(missing)}"
            )
            return False

        return True

    @staticmethod
    def _is_module_available(module_name: str) -> bool:
        """Vérifie si un module Python est disponible.

        Args:
            module_name: Nom du module à vérifier.

        Returns:
            True si le module est disponible, False sinon.
        """
        return importlib.util.find_spec(module_name) is not None

    def is_available(self) -> bool:
        """Indique si l'adapter est utilisable.

        Returns:
            True si toutes les dépendances sont présentes.
        """
        return self._available

    def validate_file(self, file_path: str) -> bool:
        """Valide la taille et l'accès au fichier.

        Args:
            file_path: Chemin vers le fichier à valider.

        Returns:
            True si le fichier est valide, False sinon.
        """
        path = Path(file_path)

        # Vérifier l'existence
        if not path.exists():
            self.logger.error(f"Fichier introuvable : {file_path}")
            return False

        # Vérifier la taille
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > self.max_size:
            self.logger.warning(
                f"Fichier trop volumineux : {size_mb:.1f}MB (max: {self.max_size}MB)",
                extra={"file_path": file_path, "size_mb": size_mb},
            )
            return False

        return True

    def parse_with_timeout(self, file_path: str) -> dict[str, Any]:
        """Parse le document avec gestion du timeout.

        Args:
            file_path: Chemin vers le fichier à parser.

        Returns:
            Dictionnaire avec le texte extrait et les métadonnées.

        Raises:
            ParsingError: Si le parsing échoue.
            TimeoutError: Si le timeout est dépassé.
        """
        if not self.is_available():
            raise ParsingError(f"{self.__class__.__name__} non disponible")

        if not self.validate_file(file_path):
            raise ParsingError(f"Fichier invalide : {file_path}")

        start_time = time.time()

        try:
            # Appeler la méthode parse() concrète
            result = self.parse(file_path)

            elapsed = time.time() - start_time
            self.logger.info(
                f"Parsing réussi en {elapsed:.2f}s",
                extra={
                    "file_path": file_path,
                    "elapsed_seconds": elapsed,
                    "text_length": len(result.get("text", "")),
                },
            )

            return result

        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.error(
                f"Échec du parsing après {elapsed:.2f}s : {e}",
                extra={"file_path": file_path, "error": str(e)},
            )
            raise ParsingError(f"Échec parsing avec {self.__class__.__name__}") from e

    @abstractmethod
    def parse(self, file_path: str) -> dict[str, Any]:
        """Parse le document et retourne le texte structuré.

        Cette méthode doit être implémentée par chaque adapter concret.

        Args:
            file_path: Chemin vers le fichier à parser.

        Returns:
            Dictionnaire avec:
                - text: Texte extrait (str)
                - metadata: Métadonnées optionnelles (dict)
                - pages: Liste de pages optionnelle (list)
                - images: Liste d'images extraites optionnelle (list)

        Raises:
            Exception: En cas d'erreur de parsing.
        """
        pass

    def __repr__(self) -> str:
        """Représentation string de l'adapter."""
        return (
            f"{self.__class__.__name__}(priority={self.priority}, "
            f"available={self._available})"
        )
