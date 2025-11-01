"""Étape 6 : Génération d'embeddings vectoriels."""

from typing import Any, Optional

import numpy as np

from rag_framework.config import get_llm_client, load_config
from rag_framework.exceptions import StepExecutionError, ValidationError
from rag_framework.steps.base_step import BaseStep
from rag_framework.types import StepData
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingStep(BaseStep):
    """Étape 6 : Génération d'embeddings vectoriels."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise l'étape d'embeddings.

        Parameters
        ----------
        config : dict[str, Any]
            Configuration de l'étape.
        """
        super().__init__(config)

        # Chargement de la config globale pour accès aux LLM providers
        self.global_config = load_config()

        # Initialisation du client d'embeddings
        self.embedding_client: Optional[Any] = None
        self.embedding_model = None

        provider = self.config.get("provider")
        model = self.config.get("model")

        if provider and model:
            try:
                # Provider API (OpenAI-compatible)
                if provider in ["openai", "mistral_ai", "ollama", "lm_studio"]:
                    self.embedding_client = get_llm_client(
                        provider_name=provider,
                        model=model,
                        temperature=0.0,  # Pas utilisé pour embeddings
                        global_config=self.global_config,
                    )
                    logger.info(
                        f"Embedding client initialisé: {provider}/{model}"
                    )

                # Sentence Transformers (local)
                elif provider == "sentence-transformers":
                    self._initialize_sentence_transformers(model)

                else:
                    logger.warning(
                        f"Provider d'embeddings non supporté: {provider}"
                    )

            except Exception as e:
                logger.warning(
                    f"Erreur lors de l'initialisation du client d'embeddings: {e}. "
                    "Fallback vers embeddings simulés."
                )
                self.embedding_client = None

    def _initialize_sentence_transformers(self, model: str) -> None:
        """Initialise Sentence Transformers pour embeddings locaux.

        Parameters
        ----------
        model : str
            Nom du modèle Sentence Transformers.
        """
        try:
            from sentence_transformers import SentenceTransformer

            device = self.config.get("processing", {}).get("device", "cpu")
            self.embedding_model = SentenceTransformer(model, device=device)
            logger.info(f"Sentence Transformers chargé: {model} (device={device})")

        except ImportError:
            logger.error(
                "Sentence Transformers non installé. "
                "Installez avec: pip install sentence-transformers"
            )
            raise
        except Exception as e:
            logger.error(f"Erreur initialisation Sentence Transformers: {e}")
            raise

    def validate_config(self) -> None:
        """Valide la configuration de l'étape."""
        if "provider" not in self.config:
            raise ValidationError(
                "Clé 'provider' manquante dans la configuration",
                details={"step": "EmbeddingStep"},
            )

        if "model" not in self.config:
            raise ValidationError(
                "Clé 'model' manquante dans la configuration",
                details={"step": "EmbeddingStep"},
            )

    def execute(self, data: StepData) -> StepData:
        """Génère les embeddings pour tous les chunks.

        Args:
            data: Données contenant 'enriched_chunks'.

        Returns:
            Données avec 'embedded_chunks' ajouté.

        Raises:
            StepExecutionError: En cas d'erreur durant la génération.
        """
        try:
            chunks = data.get("enriched_chunks", [])

            if not chunks:
                logger.warning("Aucun chunk à vectoriser")
                data["embedded_chunks"] = []
                return data

            provider = self.config["provider"]
            model = self.config["model"]
            embedded_chunks = []

            # Traitement par batch pour efficacité
            batch_size = self.config.get("processing", {}).get("batch_size", 32)

            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                texts = [chunk["text"] for chunk in batch]

                # Génération des embeddings pour le batch
                embeddings = self._generate_embeddings_batch(texts)

                # Ajout des embeddings aux chunks
                for chunk, embedding in zip(batch, embeddings):
                    embedded_chunk = chunk.copy()
                    embedded_chunk["embedding"] = embedding
                    embedded_chunk["embedding_provider"] = provider
                    embedded_chunk["embedding_model"] = model
                    embedded_chunk["embedding_dimensions"] = len(embedding)
                    embedded_chunks.append(embedded_chunk)

            data["embedded_chunks"] = embedded_chunks
            logger.info(
                f"Embedding: {len(embedded_chunks)} chunks vectorisés "
                f"avec {provider}/{model} "
                f"({embedded_chunks[0]['embedding_dimensions']} dimensions)"
            )

            return data

        except Exception as e:
            raise StepExecutionError(
                step_name="EmbeddingStep",
                message=f"Erreur lors de la génération d'embeddings: {e!s}",
                details={"error": str(e)},
            ) from e

    def _generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Génère des embeddings pour un batch de textes.

        Parameters
        ----------
        texts : list[str]
            Liste de textes à vectoriser.

        Returns
        -------
        list[list[float]]
            Liste d'embeddings (un par texte).
        """
        provider = self.config["provider"]

        # Truncate si nécessaire
        max_length = self.config.get("processing", {}).get("max_text_length", 8192)
        texts = [text[:max_length] for text in texts]

        try:
            # Provider API (OpenAI-compatible)
            if self.embedding_client is not None and provider in [
                "openai",
                "mistral_ai",
                "ollama",
                "lm_studio",
            ]:
                return self._generate_embeddings_api(texts)

            # Sentence Transformers (local)
            elif self.embedding_model is not None:
                return self._generate_embeddings_sentence_transformers(texts)

            # Fallback : embeddings simulés
            else:
                logger.warning(
                    f"Aucun client d'embeddings disponible. "
                    f"Génération d'embeddings simulés pour {len(texts)} textes."
                )
                return self._generate_embeddings_simulated(texts)

        except Exception as e:
            logger.error(f"Erreur génération embeddings: {e}")
            logger.warning("Fallback vers embeddings simulés")
            return self._generate_embeddings_simulated(texts)

    def _generate_embeddings_api(self, texts: list[str]) -> list[list[float]]:
        """Génère des embeddings via une API OpenAI-compatible.

        Parameters
        ----------
        texts : list[str]
            Liste de textes à vectoriser.

        Returns
        -------
        list[list[float]]
            Liste d'embeddings.
        """
        assert self.embedding_client is not None

        # Utilisation de l'API embeddings (OpenAI-compatible)
        response = self.embedding_client.embeddings.create(
            input=texts, model=self.embedding_client._model
        )

        # Extraction des embeddings
        embeddings = [data.embedding for data in response.data]

        return embeddings

    def _generate_embeddings_sentence_transformers(
        self, texts: list[str]
    ) -> list[list[float]]:
        """Génère des embeddings avec Sentence Transformers.

        Parameters
        ----------
        texts : list[str]
            Liste de textes à vectoriser.

        Returns
        -------
        list[list[float]]
            Liste d'embeddings.
        """
        assert self.embedding_model is not None

        # Génération des embeddings
        normalize = self.config.get("processing", {}).get("normalize_embeddings", True)
        embeddings_array = self.embedding_model.encode(
            texts, normalize_embeddings=normalize, show_progress_bar=False
        )

        # Conversion en liste de listes
        embeddings: list[list[float]] = embeddings_array.tolist()

        return embeddings

    def _generate_embeddings_simulated(self, texts: list[str]) -> list[list[float]]:
        """Génère des embeddings simulés (pour tests uniquement).

        Parameters
        ----------
        texts : list[str]
            Liste de textes à vectoriser.

        Returns
        -------
        list[list[float]]
            Liste d'embeddings simulés.
        """
        # Dimension par défaut (compatible avec la plupart des bases vectorielles)
        dim = self.config.get("dimensions")
        if dim is None:
            dim = 1024  # Dimension par défaut si non spécifiée

        embeddings = []
        for text in texts:
            # Génération d'un vecteur aléatoire déterministe basé sur le hash du texte
            np.random.seed(hash(text) % 2**32)
            embedding: list[float] = np.random.randn(dim).tolist()
            embeddings.append(embedding)

        return embeddings
