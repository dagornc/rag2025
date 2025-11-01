"""Chargement unifié des modèles (LLM + Embeddings) depuis model_providers.

Ce module permet de charger n'importe quel type de modèle (LLM, embedding)
en fonction des providers définis dans global.yaml.

Architecture unifiée : un seul loader pour tous les types de modèles.

Auteur: RAG Framework Team
Version: 1.0.0
"""

import importlib.util
import os
from pathlib import Path
from typing import Any, Callable, Literal

import yaml

from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)

# Types pour les modèles chargés
EmbeddingFunction = Callable[[list[str]], list[list[float]]]
LLMModel = dict[str, Any]  # TODO: Remplacer par type LangChain/OpenAI client
ModelResult = EmbeddingFunction | LLMModel


class ModelLoader:
    """Chargeur unifié de modèles (LLM + Embeddings) depuis model_providers.

    Cette classe lit la configuration global.yaml et charge le modèle approprié
    selon le provider, le nom du modèle, et le type (llm ou embedding).

    Attributes:
        global_config_path: Chemin vers global.yaml.
        providers_config: Configuration des model providers.
    """

    def __init__(self, global_config_path: str | Path = "config/global.yaml") -> None:
        """Initialise le loader.

        Args:
            global_config_path: Chemin vers global.yaml.
        """
        self.global_config_path = Path(global_config_path)
        self.providers_config = self._load_global_config()

    def _load_global_config(self) -> dict[str, Any]:
        """Charge global.yaml et extrait model_providers.

        Returns:
            Configuration des model providers.

        Raises:
            FileNotFoundError: Si global.yaml n'existe pas.
            ValueError: Si model_providers est absent.
        """
        if not self.global_config_path.exists():
            raise FileNotFoundError(
                f"Fichier global.yaml introuvable : {self.global_config_path}"
            )

        with open(self.global_config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if "model_providers" not in config:
            raise ValueError("Section 'model_providers' absente dans global.yaml")

        logger.info(
            f"Configuration des model providers chargée "
            f"depuis {self.global_config_path}"
        )
        return config["model_providers"]

    def get_model_info(
        self, provider: str, model_name: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Récupère les informations sur un modèle.

        Args:
            provider: Nom du provider (ex: "openai", "sentence_transformers").
            model_name: Nom du modèle (ex: "gpt-4", "all-MiniLM-L6-v2").

        Returns:
            Tuple (provider_config, model_config).

        Raises:
            ValueError: Si le provider ou le modèle est inconnu.
        """
        if provider not in self.providers_config:
            available = ", ".join(self.providers_config.keys())
            raise ValueError(
                f"Provider inconnu : '{provider}'. Disponibles : {available}"
            )

        provider_config = self.providers_config[provider]

        # Chercher le modèle dans la liste
        model_config = None
        for model in provider_config.get("models", []):
            if model["name"] == model_name:
                model_config = model
                break

        if model_config is None:
            available_models = [m["name"] for m in provider_config.get("models", [])]
            raise ValueError(
                f"Modèle '{model_name}' introuvable dans provider '{provider}'. "
                f"Disponibles : {', '.join(available_models)}"
            )

        return provider_config, model_config

    def load_model(
        self,
        provider: str,
        model_name: str,
        model_type: Literal["llm", "embedding"] | None = None,
    ) -> ModelResult:
        """Charge un modèle selon le provider et le type.

        Args:
            provider: Nom du provider (ex: "openai").
            model_name: Nom du modèle (ex: "gpt-4").
            model_type: Type de modèle ("llm" ou "embedding"). Si None, détecté auto.

        Returns:
            Pour LLM : objet callable ou client LLM.
            Pour embeddings : fonction list[str] -> list[list[float]].

        Raises:
            ValueError: Si le provider, modèle ou type est invalide.
        """
        provider_config, model_config = self.get_model_info(provider, model_name)

        # Détecter le type automatiquement si non spécifié
        if model_type is None:
            model_type = model_config.get("type", "llm")

        # Vérifier que le type correspond
        actual_type = model_config.get("type")
        if actual_type != model_type:
            raise ValueError(
                f"Le modèle '{model_name}' est de type '{actual_type}', "
                f"pas '{model_type}'"
            )

        logger.info(
            f"Chargement du modèle '{model_name}' "
            f"(type: {model_type}, provider: {provider})"
        )

        if model_type == "embedding":
            return self._load_embedding_model(
                provider, model_name, provider_config, model_config
            )
        elif model_type == "llm":
            return self._load_llm_model(
                provider, model_name, provider_config, model_config
            )
        else:
            raise ValueError(f"Type de modèle non supporté : {model_type}")

    def _load_embedding_model(
        self,
        provider: str,
        model_name: str,
        provider_config: dict[str, Any],
        model_config: dict[str, Any],
    ) -> Callable[[list[str]], list[list[float]]]:
        """Charge un modèle d'embeddings.

        Args:
            provider: Nom du provider.
            model_name: Nom du modèle.
            provider_config: Configuration du provider.
            model_config: Configuration du modèle.

        Returns:
            Fonction d'embedding.
        """
        access_method = provider_config.get("access_method")

        if provider == "sentence_transformers" or access_method == "local":
            return self._load_sentence_transformers(model_name)
        elif provider == "openai" or "openai" in provider.lower():
            return self._load_openai_embeddings(model_name, provider_config)
        elif provider == "ollama" or access_method == "ollama":
            return self._load_ollama_embeddings(model_name, provider_config)
        elif provider == "huggingface" or access_method == "huggingface_inference_api":
            return self._load_huggingface_embeddings(model_name, provider_config)
        else:
            raise ValueError(
                f"Provider '{provider}' non supporté pour embeddings. "
                f"Méthode d'accès : {access_method}"
            )

    def _load_llm_model(
        self,
        provider: str,
        model_name: str,
        provider_config: dict[str, Any],
        model_config: dict[str, Any],
    ) -> LLMModel:
        """Charge un modèle LLM.

        Args:
            provider: Nom du provider.
            model_name: Nom du modèle.
            provider_config: Configuration du provider.
            model_config: Configuration du modèle.

        Returns:
            Client LLM ou fonction callable.

        Note:
            Pour l'instant, retourne simplement un dict avec les infos.
            À étendre avec l'intégration LangChain/OpenAI client.
        """
        # Pour l'instant, retourner un objet avec les informations
        # TODO: Intégrer avec LangChain ou OpenAI client
        return {
            "provider": provider,
            "model_name": model_name,
            "api_key": provider_config.get("api_key"),
            "base_url": provider_config.get("base_url"),
            "access_method": provider_config.get("access_method"),
            "context_window": model_config.get("context_window"),
            "max_output_tokens": model_config.get("max_output_tokens"),
        }

    def _load_sentence_transformers(
        self, model_name: str
    ) -> Callable[[list[str]], list[list[float]]]:
        """Charge un modèle sentence-transformers local."""
        if not importlib.util.find_spec("sentence_transformers"):
            raise ImportError(
                "sentence-transformers non installé. "
                "Installez avec : rye add sentence-transformers"
            )

        from sentence_transformers import SentenceTransformer

        logger.info(f"Chargement du modèle local sentence-transformers : {model_name}")
        model = SentenceTransformer(model_name)

        def embed_fn(texts: list[str]) -> list[list[float]]:
            """Encode les textes en embeddings."""
            embeddings = model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()

        return embed_fn

    def _load_openai_embeddings(
        self, model_name: str, provider_config: dict[str, Any]
    ) -> Callable[[list[str]], list[list[float]]]:
        """Charge un modèle OpenAI Embeddings (API)."""
        if not importlib.util.find_spec("openai"):
            raise ImportError("openai non installé. Installez avec : rye add openai")

        from openai import OpenAI

        api_key = provider_config.get("api_key", os.getenv("OPENAI_API_KEY"))
        if not api_key or api_key == "${OPENAI_API_KEY}":
            raise ValueError(
                "Clé API OpenAI manquante. "
                "Définissez OPENAI_API_KEY dans l'environnement."
            )

        client = OpenAI(api_key=api_key)
        logger.info(f"Chargement du modèle OpenAI Embeddings : {model_name}")

        def embed_fn(texts: list[str]) -> list[list[float]]:
            """Encode les textes avec l'API OpenAI."""
            response = client.embeddings.create(input=texts, model=model_name)
            return [data.embedding for data in response.data]

        return embed_fn

    def _load_ollama_embeddings(
        self, model_name: str, provider_config: dict[str, Any]
    ) -> Callable[[list[str]], list[list[float]]]:
        """Charge un modèle Ollama local."""
        if not importlib.util.find_spec("requests"):
            raise ImportError(
                "requests non installé. Installez avec : rye add requests"
            )

        import requests

        base_url = provider_config.get("base_url", "http://127.0.0.1:11434")
        # Ollama utilise /api/embeddings sans /v1
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
        embed_url = f"{base_url}/api/embeddings"
        logger.info(f"Chargement du modèle Ollama : {model_name} ({base_url})")

        def embed_fn(texts: list[str]) -> list[list[float]]:
            """Encode les textes via Ollama API."""
            embeddings = []
            for text in texts:
                response = requests.post(
                    embed_url, json={"model": model_name, "prompt": text}, timeout=30
                )
                response.raise_for_status()
                embeddings.append(response.json()["embedding"])
            return embeddings

        return embed_fn

    def _load_huggingface_embeddings(
        self, model_name: str, provider_config: dict[str, Any]
    ) -> Callable[[list[str]], list[list[float]]]:
        """Charge un modèle Hugging Face Inference API."""
        if not importlib.util.find_spec("requests"):
            raise ImportError(
                "requests non installé. Installez avec : rye add requests"
            )

        import requests

        api_key = provider_config.get("api_key", os.getenv("HUGGINGFACE_API_KEY"))
        if not api_key or api_key == "${HUGGINGFACE_API_KEY}":
            raise ValueError(
                "Clé API Hugging Face manquante. "
                "Définissez HUGGINGFACE_API_KEY dans l'environnement."
            )

        api_url = (
            f"https://api-inference.huggingface.co/pipeline/"
            f"feature-extraction/{model_name}"
        )
        headers = {"Authorization": f"Bearer {api_key}"}
        logger.info(f"Chargement du modèle Hugging Face Inference : {model_name}")

        def embed_fn(texts: list[str]) -> list[list[float]]:
            """Encode les textes avec l'API Hugging Face."""
            response = requests.post(
                api_url, headers=headers, json={"inputs": texts}, timeout=30
            )
            response.raise_for_status()
            return response.json()

        return embed_fn


def load_model(
    provider: str,
    model_name: str,
    model_type: Literal["llm", "embedding"] | None = None,
    global_config_path: str | Path = "config/global.yaml",
) -> ModelResult:
    """Fonction helper pour charger un modèle.

    Args:
        provider: Nom du provider (ex: "openai", "sentence_transformers").
        model_name: Nom du modèle (ex: "gpt-4", "all-MiniLM-L6-v2").
        model_type: Type de modèle ("llm" ou "embedding"). Détecté auto si None.
        global_config_path: Chemin vers global.yaml.

    Returns:
        Modèle chargé (LLM ou embedding).

    Example:
        >>> # Charger un embedding
        >>> embed_fn = load_model("openai", "text-embedding-3-large", "embedding")
        >>> vectors = embed_fn(["Bonjour", "Hello"])
        >>>
        >>> # Charger un LLM
        >>> llm = load_model("openai", "gpt-4", "llm")
    """
    loader = ModelLoader(global_config_path)
    return loader.load_model(provider, model_name, model_type)
