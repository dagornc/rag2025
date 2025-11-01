"""Chargement dynamique des modèles d'embeddings depuis les providers.

Ce module est maintenant un WRAPPER autour du ModelLoader unifié.
Il est conservé pour compatibilité avec le code existant.

IMPORTANT: Préférez utiliser `rag_framework.models.loader.load_model()`
directement pour tout nouveau code.

Auteur: RAG Framework Team
Version: 2.0.0 (refactorisé vers ModelLoader unifié)
"""

from pathlib import Path
from typing import Callable

from rag_framework.models.loader import ModelLoader
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingLoader:
    """WRAPPER de compatibilité autour du ModelLoader unifié.

    Cette classe délègue maintenant au ModelLoader pour charger les embeddings.
    Elle est conservée pour compatibilité avec le code existant.

    DEPRECATED: Utilisez directement `rag_framework.models.loader.load_model()`
    pour tout nouveau code.

    Attributes:
        model_loader: Instance du ModelLoader unifié.
    """

    def __init__(self, global_config_path: str | Path = "config/global.yaml") -> None:
        """Initialise le loader.

        Args:
            global_config_path: Chemin vers global.yaml.
        """
        logger.warning(
            "EmbeddingLoader est déprécié. "
            "Utilisez rag_framework.models.loader.load_model() directement."
        )
        self.model_loader = ModelLoader(global_config_path)

    def load_model(
        self, provider: str, model_name: str
    ) -> Callable[[list[str]], list[list[float]]]:
        """Charge un modèle d'embeddings selon le provider.

        Args:
            provider: Nom du provider (ex: "sentence_transformers").
            model_name: Nom du modèle (ex: "paraphrase-multilingual-MiniLM").

        Returns:
            Fonction d'embedding qui prend une liste de textes et retourne
            une liste de vecteurs d'embeddings.

        Raises:
            ValueError: Si le provider ou le modèle est inconnu.
            ImportError: Si la librairie requise n'est pas installée.
        """
        # Déléguer au ModelLoader unifié
        result = self.model_loader.load_model(
            provider, model_name, model_type="embedding"
        )

        # Le ModelLoader retourne soit EmbeddingFunction soit LLMModel
        # Pour les embeddings, c'est toujours EmbeddingFunction
        if not callable(result):
            raise TypeError(
                f"Le modèle '{model_name}' n'est pas une fonction d'embedding valide"
            )

        return result  # type: ignore[return-value]


def load_embedding_model(
    provider: str,
    model_name: str,
    global_config_path: str | Path = "config/global.yaml",
) -> Callable[[list[str]], list[list[float]]]:
    """Fonction helper pour charger un modèle d'embeddings.

    DEPRECATED: Utilisez `rag_framework.models.loader.load_model()` directement.

    Args:
        provider: Nom du provider (ex: "sentence_transformers").
        model_name: Nom du modèle.
        global_config_path: Chemin vers global.yaml.

    Returns:
        Fonction d'embedding.

    Example:
        >>> embed_fn = load_embedding_model("sentence_transformers", "all-MiniLM-L6-v2")
        >>> vectors = embed_fn(["Bonjour", "Hello"])
        >>> print(len(vectors))  # 2
        >>> print(len(vectors[0]))  # 384 (dimensions)
    """
    loader = EmbeddingLoader(global_config_path)
    return loader.load_model(provider, model_name)
