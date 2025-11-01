"""Gestionnaire principal du système de prétraitement avec fallback.

Ce module orchestre le routing, le fallback, le chunking et la collecte
de métriques pour le preprocessing des documents.

Auteur: RAG Framework Team
Version: 1.0.0
"""

from pathlib import Path
from typing import Any

from rag_framework.preprocessing.config import load_parser_config
from rag_framework.preprocessing.fallback_chain import FallbackChainManager
from rag_framework.preprocessing.router import DocumentRouter
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class RAGPreprocessingManager:
    """Orchestrateur principal du système de prétraitement.

    Cette classe coordonne:
    - Le routing des documents vers les bonnes catégories
    - L'exécution des chaînes de fallback
    - Le chunking selon la stratégie configurée
    - La collecte de métriques

    Attributes:
        config: Configuration validée du preprocessing.
        router: Router pour déterminer la catégorie des fichiers.
    """

    def __init__(self, config_path: str | Path) -> None:
        """Initialise le manager avec la configuration parser.yaml.

        Args:
            config_path: Chemin vers le fichier parser.yaml.
        """
        self.config = load_parser_config(config_path)
        self.router = DocumentRouter(self.config)
        self.adapter_registry = self._initialize_adapters()

        logger.info(
            "RAGPreprocessingManager initialisé",
            extra={
                "optimization_mode": self.config.optimization_mode,
                "categories": len(self.config.file_categories),
            },
        )

    def _initialize_adapters(self) -> dict[str, list[Any]]:
        """Initialise tous les adapters par catégorie.

        Returns:
            Dictionnaire {category_name: [adapters]}.
        """
        registry: dict[str, list[Any]] = {}

        for category_name, category_config in self.config.file_categories.items():
            if not category_config.enabled:
                continue

            adapters = []

            # Charger les adapters selon la catégorie
            if category_config.fallback_chain:
                for lib_config in category_config.fallback_chain:
                    adapter = self._create_adapter(
                        lib_config.library, lib_config.model_dump()
                    )
                    if adapter:
                        adapters.append(adapter)

            registry[category_name] = adapters

        logger.info(
            f"Adapters initialisés : {sum(len(v) for v in registry.values())} total"
        )
        return registry

    def _create_adapter(self, library_name: str, config: dict[str, Any]) -> Any | None:
        """Factory pour créer un adapter.

        Args:
            library_name: Nom de la librairie (ex: "pymupdf").
            config: Configuration de l'adapter.

        Returns:
            Instance de l'adapter ou None si indisponible.
        """
        # Import dynamique des adapters
        try:
            # ========== PDF Adapters ==========
            if library_name == "pymupdf":
                from rag_framework.preprocessing.adapters.pdf.pymupdf import (
                    PyMuPDFAdapter,
                )

                return PyMuPDFAdapter(config)

            elif library_name == "marker":
                from rag_framework.preprocessing.adapters.pdf.marker import (
                    MarkerAdapter,
                )

                return MarkerAdapter(config)

            # ========== Office Adapters ==========
            elif library_name == "python-docx":
                from rag_framework.preprocessing.adapters.office.docx import (
                    PythonDocxAdapter,
                )

                return PythonDocxAdapter(config)

            elif library_name == "python-pptx":
                from rag_framework.preprocessing.adapters.office.pptx import (
                    PythonPptxAdapter,
                )

                return PythonPptxAdapter(config)

            elif library_name == "openpyxl":
                from rag_framework.preprocessing.adapters.office.xlsx import (
                    OpenpyxlAdapter,
                )

                return OpenpyxlAdapter(config)

            elif library_name == "unstructured":
                from rag_framework.preprocessing.adapters.office.unstructured import (
                    UnstructuredAdapter,
                )

                return UnstructuredAdapter(config)

            # ========== HTML/Markdown Adapters ==========
            elif library_name == "beautifulsoup4":
                from rag_framework.preprocessing.adapters.html.beautifulsoup import (
                    BeautifulSoupAdapter,
                )

                return BeautifulSoupAdapter(config)

            elif library_name == "markdown":
                from rag_framework.preprocessing.adapters.markdown.markdown_parser import (
                    MarkdownAdapter,
                )

                return MarkdownAdapter(config)

            # ========== Text Adapters ==========
            elif library_name == "text":
                from rag_framework.preprocessing.adapters.text.txt import TextAdapter

                return TextAdapter(config)

            elif library_name == "pandas":
                from rag_framework.preprocessing.adapters.text.csv_parser import (
                    CSVAdapter,
                )

                return CSVAdapter(config)

            else:
                logger.warning(f"Adapter non implémenté : {library_name}")
                return None

        except ImportError as e:
            logger.warning(f"Impossible d'importer {library_name} : {e}")
            return None

    def process_document(self, file_path: str) -> dict[str, Any]:
        """Traite un document avec fallback automatique.

        Args:
            file_path: Chemin vers le fichier à traiter.

        Returns:
            Dictionnaire avec:
                - text: Texte extrait
                - metadata: Métadonnées
                - chunks: Liste de chunks si chunking activé
                - metrics: Métriques de traitement

        Raises:
            ValueError: Si le fichier n'est pas supporté.
        """
        logger.info(f"Traitement du document : {file_path}")

        # 1. Router vers la bonne catégorie
        category = self.router.route(file_path)
        logger.debug(f"Catégorie détectée : {category}")

        # 2. Récupérer les adapters pour cette catégorie
        adapters = self.adapter_registry.get(category, [])
        if not adapters:
            raise ValueError(f"Aucun adapter disponible pour catégorie {category}")

        # 3. Exécuter la chaîne de fallback
        fallback_manager = FallbackChainManager(
            adapters, self.config.error_handling.model_dump()
        )
        result = fallback_manager.execute_chain(file_path)

        if result is None:
            raise ValueError(f"Échec du parsing pour {file_path}")

        # 4. Chunking (si configuré)
        if self.config.chunking:
            chunks = self._chunk_text(result["text"])
            result["chunks"] = chunks

        # 5. Métriques
        result["metrics"] = {
            "file_path": file_path,
            "category": category,
            "text_length": len(result.get("text", "")),
            "chunk_count": len(result.get("chunks", [])),
        }

        logger.info(
            "Document traité avec succès",
            extra={
                "file_path": file_path,
                "text_length": len(result.get("text", "")),
            },
        )

        return result

    def _chunk_text(self, text: str) -> list[dict[str, Any]]:
        """Découpe le texte en chunks selon la stratégie configurée.

        Args:
            text: Texte à découper.

        Returns:
            Liste de chunks avec métadonnées.
        """
        strategy = self.config.chunking.strategy
        strategy_config = self.config.chunking.strategies.get(strategy)

        if not strategy_config:
            logger.warning(
                f"Stratégie de chunking {strategy} non trouvée, "
                f"utilisation de fixed par défaut"
            )
            strategy_config = self.config.chunking.strategies.get("fixed")

        # Implémentation simplifiée du chunking fixe
        if strategy == "fixed":
            chunk_size = strategy_config.chunk_size or 1000
            overlap = strategy_config.overlap or 200

            chunks = []
            start = 0
            while start < len(text):
                end = start + chunk_size
                chunk_text = text[start:end]
                chunks.append(
                    {
                        "text": chunk_text,
                        "start": start,
                        "end": end,
                        "index": len(chunks),
                    }
                )
                start = end - overlap

            return chunks

        # Autres stratégies à implémenter
        logger.warning(f"Stratégie {strategy} non implémentée, fallback vers fixed")
        return self._chunk_text(text)  # Récursion avec fixed par défaut
