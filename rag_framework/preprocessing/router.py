"""Routage des documents vers les adapters appropriés selon le type de fichier.

Auteur: RAG Framework Team
Version: 1.0.0
"""

from pathlib import Path
from typing import Any

from rag_framework.preprocessing.config import PreprocessingConfig
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentRouter:
    """Route les documents vers la catégorie appropriée.

    Attributes:
        config: Configuration du preprocessing.
        extension_map: Mapping extension -> catégorie.
    """

    def __init__(self, config: PreprocessingConfig) -> None:
        """Initialise le router.

        Args:
            config: Configuration validée du preprocessing.
        """
        self.config = config
        self.extension_map = self._build_extension_map()

    def _build_extension_map(self) -> dict[str, str]:
        """Construit le mapping extension -> catégorie.

        Returns:
            Dictionnaire {extension: category_name}.
        """
        ext_map = {}
        for category_name, category_config in self.config.file_categories.items():
            if not category_config.enabled:
                continue

            extensions = category_config.extensions or []
            for ext in extensions:
                # Normaliser l'extension (lowercase, avec point)
                normalized_ext = (
                    ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                )
                ext_map[normalized_ext] = category_name

        return ext_map

    def route(self, file_path: str) -> str:
        """Détermine la catégorie d'un fichier.

        Args:
            file_path: Chemin vers le fichier.

        Returns:
            Nom de la catégorie (ex: "pdf", "office").

        Raises:
            ValueError: Si l'extension n'est pas supportée.
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        category = self.extension_map.get(ext)
        if category is None:
            raise ValueError(
                f"Extension non supportée : {ext}. "
                f"Extensions disponibles : {list(self.extension_map.keys())}"
            )

        logger.debug(
            f"Fichier routé vers catégorie '{category}'",
            extra={"file_path": file_path, "extension": ext, "category": category},
        )

        return category

    def get_category_config(self, file_path: str) -> dict[str, Any]:
        """Récupère la configuration de la catégorie d'un fichier.

        Args:
            file_path: Chemin vers le fichier.

        Returns:
            Configuration de la catégorie.
        """
        category = self.route(file_path)
        return self.config.file_categories[category].model_dump()
