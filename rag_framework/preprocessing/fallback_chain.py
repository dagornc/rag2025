"""Gestionnaire de la chaîne de fallback pour le parsing.

Ce module implémente le pattern Chain of Responsibility pour essayer
séquentiellement différents parsers jusqu'à ce qu'un réussisse.

Auteur: RAG Framework Team
Version: 1.0.0
"""

from typing import Any

from rag_framework.preprocessing.adapters.base import LibraryAdapter, ParsingError
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class FallbackChainManager:
    """Gère l'exécution séquentielle des adapters avec fallback.

    Cette classe implémente le pattern Chain of Responsibility :
    elle essaie chaque adapter dans l'ordre de priorité jusqu'à
    ce qu'un réussisse.

    Attributes:
        adapters: Liste des adapters disponibles, triés par priorité.
        config: Configuration globale.
    """

    def __init__(self, adapters: list[LibraryAdapter], config: dict[str, Any]) -> None:
        """Initialise le gestionnaire de fallback.

        Args:
            adapters: Liste des adapters à utiliser.
            config: Configuration globale (error_handling, etc.).
        """
        # Trier par priorité (1 = plus haute priorité)
        self.adapters = sorted(adapters, key=lambda a: a.priority)
        self.config = config

        # Filtrer les adapters non disponibles
        self.available_adapters = [a for a in self.adapters if a.is_available()]

        logger.info(
            f"FallbackChainManager initialisé : {len(self.available_adapters)}"
            f"/{len(self.adapters)} adapters disponibles",
            extra={
                "total": len(self.adapters),
                "available": len(self.available_adapters),
            },
        )

    def execute_chain(self, file_path: str) -> dict[str, Any] | None:
        """Exécute la chaîne de fallback jusqu'au succès.

        Args:
            file_path: Chemin vers le fichier à parser.

        Returns:
            Résultat du parsing (dict avec "text", "metadata", etc.)
            ou None si tous les adapters échouent.
        """
        if not self.available_adapters:
            logger.error("Aucun adapter disponible pour la chaîne de fallback")
            return None

        for adapter in self.available_adapters:
            try:
                logger.info(
                    f"Tentative de parsing avec {adapter.__class__.__name__}",
                    extra={
                        "adapter": adapter.__class__.__name__,
                        "priority": adapter.priority,
                    },
                )

                # Essayer de parser
                result = adapter.parse_with_timeout(file_path)

                # Vérifier que le résultat est valide
                if self._is_valid_result(result):
                    logger.info(
                        f"Parsing réussi avec {adapter.__class__.__name__}",
                        extra={
                            "adapter": adapter.__class__.__name__,
                            "text_length": len(result.get("text", "")),
                        },
                    )
                    return result
                else:
                    logger.warning(
                        f"{adapter.__class__.__name__} a retourné un résultat invalide"
                    )

            except ParsingError as e:
                logger.warning(
                    f"{adapter.__class__.__name__} a échoué : {e}",
                    extra={"adapter": adapter.__class__.__name__, "error": str(e)},
                )
                # Continuer avec le prochain adapter
                continue

            except Exception as e:
                logger.error(
                    f"Erreur inattendue avec {adapter.__class__.__name__} : {e}",
                    extra={"adapter": adapter.__class__.__name__, "error": str(e)},
                )
                continue

        # Si tous les adapters ont échoué
        logger.error(
            "Échec de tous les adapters dans la chaîne de fallback",
            extra={
                "file_path": file_path,
                "adapters_tried": len(self.available_adapters),
            },
        )
        return None

    def _is_valid_result(self, result: dict[str, Any] | None) -> bool:
        """Vérifie qu'un résultat de parsing est valide.

        Args:
            result: Résultat retourné par un adapter.

        Returns:
            True si le résultat est valide (contient du texte).
        """
        if result is None:
            return False

        text = result.get("text", "")
        if not text or not text.strip():
            return False

        # Le texte doit avoir une longueur minimale
        min_length = 10
        if len(text.strip()) < min_length:
            return False

        return True

    def trigger_ocr_fallback(
        self, file_path: str, ocr_engines: list[Any]
    ) -> dict[str, Any] | None:
        """Déclenche le fallback OCR si les parsers classiques échouent.

        Args:
            file_path: Chemin vers le fichier.
            ocr_engines: Liste des moteurs OCR à utiliser.

        Returns:
            Résultat de l'OCR ou None si échec.
        """
        logger.info(
            f"Déclenchement du fallback OCR ({len(ocr_engines)} moteurs)",
            extra={"file_path": file_path, "ocr_count": len(ocr_engines)},
        )

        for engine in ocr_engines:
            try:
                result = engine.extract_text(file_path)
                if self._is_valid_result(result):
                    logger.info(
                        f"OCR réussi avec {engine.__class__.__name__}",
                        extra={"engine": engine.__class__.__name__},
                    )
                    return result
            except Exception as e:
                logger.warning(f"OCR échoué avec {engine.__class__.__name__} : {e}")
                continue

        logger.error("Échec de tous les moteurs OCR")
        return None
