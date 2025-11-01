"""Étape 6 : Génération d'embeddings vectoriels."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
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
        self.embedding_model: Optional[Any] = None

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
                    logger.info(f"Embedding client initialisé: {provider}/{model}")

                # Sentence Transformers (local)
                elif provider == "sentence-transformers":
                    self._initialize_sentence_transformers(model)

                else:
                    logger.warning(f"Provider d'embeddings non supporté: {provider}")

            except Exception as e:
                logger.warning(
                    f"Erreur lors de l'initialisation du client d'embeddings: {e}. "
                    "Fallback vers embeddings simulés."
                )
                self.embedding_client = None

        # Configuration du cache d'embeddings (Feature #8)
        caching_config = self.config.get("caching", {})
        self.cache_enabled = caching_config.get("enabled", False)
        self.cache_dir = Path(caching_config.get("cache_dir", ".cache/embeddings"))
        self.cache_ttl_days = caching_config.get("ttl_days", 30)

        if self.cache_enabled:
            # Création du répertoire de cache s'il n'existe pas
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(
                f"Cache embeddings activé: {self.cache_dir} "
                f"(TTL: {self.cache_ttl_days} jours)"
            )
            # Nettoyage des entrées expirées au démarrage
            self._cleanup_expired_cache()

    def _get_cache_key(self, text: str) -> str:
        """Génère une clé de cache unique pour un texte.

        Utilise SHA256 sur texte + provider + model pour garantir l'unicité.

        Parameters
        ----------
        text : str
            Texte à hasher.

        Returns:
        -------
        str
            Clé de cache (hash SHA256).
        """
        provider = self.config.get("provider", "unknown")
        model = self.config.get("model", "unknown")
        # Création d'une chaîne unique: texte + provider + model
        unique_string = f"{text}|{provider}|{model}"
        # Hash SHA256 pour clé courte et unique
        return hashlib.sha256(unique_string.encode("utf-8")).hexdigest()

    def _load_from_cache(self, cache_key: str) -> Optional[list[float]]:
        """Charge un embedding depuis le cache disque.

        Vérifie l'expiration (TTL) et retourne None si expiré.

        Parameters
        ----------
        cache_key : str
            Clé de cache (hash).

        Returns:
        -------
        Optional[list[float]]
            Embedding si trouvé et valide, None sinon.
        """
        if not self.cache_enabled:
            return None

        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, encoding="utf-8") as f:
                cached_data = json.load(f)

            # Vérification de l'expiration
            cached_timestamp = datetime.fromisoformat(cached_data["timestamp"])
            expiration_date = cached_timestamp + timedelta(days=self.cache_ttl_days)

            if datetime.now(timezone.utc) > expiration_date:
                # Cache expiré, suppression
                cache_file.unlink()
                return None

            # Type cast pour mypy : on sait que embedding est list[float]
            embedding: list[float] = cached_data["embedding"]
            return embedding

        except Exception as e:
            logger.warning(f"Erreur lecture cache {cache_key}: {e}")
            return None

    def _save_to_cache(self, cache_key: str, embedding: list[float]) -> None:
        """Sauvegarde un embedding dans le cache disque.

        Parameters
        ----------
        cache_key : str
            Clé de cache (hash).
        embedding : list[float]
            Vecteur d'embedding à sauvegarder.
        """
        if not self.cache_enabled:
            return

        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            cache_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "embedding": embedding,
                "provider": self.config.get("provider"),
                "model": self.config.get("model"),
            }

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False)

        except Exception as e:
            logger.warning(f"Erreur sauvegarde cache {cache_key}: {e}")

    def _cleanup_expired_cache(self) -> None:
        """Supprime les entrées de cache expirées (TTL dépassé)."""
        if not self.cache_enabled or not self.cache_dir.exists():
            return

        try:
            expired_count = 0
            current_time = datetime.now(timezone.utc)

            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, encoding="utf-8") as f:
                        cached_data = json.load(f)

                    cached_timestamp = datetime.fromisoformat(cached_data["timestamp"])
                    expiration_date = cached_timestamp + timedelta(
                        days=self.cache_ttl_days
                    )

                    if current_time > expiration_date:
                        cache_file.unlink()
                        expired_count += 1

                except Exception as e:
                    logger.warning(f"Erreur traitement cache {cache_file.name}: {e}")

            if expired_count > 0:
                logger.info(
                    f"Cache cleanup: {expired_count} entrées expirées supprimées"
                )

        except Exception as e:
            logger.warning(f"Erreur nettoyage cache: {e}")

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
            # Priorité: config locale > config globale performance > défaut
            batch_size = self.config.get("processing", {}).get(
                "batch_size", self.global_config.performance.batch_size
            )

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

        Utilise le cache disque si activé pour éviter les regénérations.

        Parameters
        ----------
        texts : list[str]
            Liste de textes à vectoriser.

        Returns:
        -------
        list[list[float]]
            Liste d'embeddings (un par texte).
        """
        provider = self.config["provider"]

        # Truncate si nécessaire
        max_length = self.config.get("processing", {}).get("max_text_length", 8192)
        texts = [text[:max_length] for text in texts]

        # Gestion du cache (Feature #8)
        embeddings_result: list[Optional[list[float]]] = [None] * len(texts)
        texts_to_generate: list[tuple[int, str]] = []  # (index, text)
        cache_hits = 0

        if self.cache_enabled:
            # Tentative de chargement depuis le cache pour chaque texte
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                cached_embedding = self._load_from_cache(cache_key)

                if cached_embedding is not None:
                    embeddings_result[i] = cached_embedding
                    cache_hits += 1
                else:
                    texts_to_generate.append((i, text))
        else:
            # Pas de cache, générer tous les embeddings
            texts_to_generate = list(enumerate(texts))

        # Log du taux de cache hit
        if self.cache_enabled and len(texts) > 0:
            hit_rate = (cache_hits / len(texts)) * 100
            logger.info(
                f"Cache embeddings: {cache_hits}/{len(texts)} hits ({hit_rate:.1f}%)"
            )

        # Si tous les embeddings sont en cache, retour immédiat
        if len(texts_to_generate) == 0:
            return embeddings_result  # type: ignore[return-value]

        # Génération des embeddings manquants
        texts_only = [text for _, text in texts_to_generate]
        generated_embeddings: list[list[float]] = []

        try:
            # Provider API (OpenAI-compatible)
            if self.embedding_client is not None and provider in [
                "openai",
                "mistral_ai",
                "ollama",
                "lm_studio",
            ]:
                generated_embeddings = self._generate_embeddings_api(texts_only)

            # Sentence Transformers (local)
            elif self.embedding_model is not None:
                generated_embeddings = self._generate_embeddings_sentence_transformers(
                    texts_only
                )

            # Fallback : embeddings simulés
            else:
                logger.warning(
                    f"Aucun client d'embeddings disponible. "
                    f"Génération d'embeddings simulés pour {len(texts_only)} textes."
                )
                generated_embeddings = self._generate_embeddings_simulated(texts_only)

        except Exception as e:
            logger.error(f"Erreur génération embeddings: {e}")
            logger.warning("Fallback vers embeddings simulés")
            generated_embeddings = self._generate_embeddings_simulated(texts_only)

        # Insertion des embeddings générés dans le résultat + sauvegarde cache
        for (idx, text), embedding in zip(texts_to_generate, generated_embeddings):
            embeddings_result[idx] = embedding

            # Sauvegarde dans le cache si activé
            if self.cache_enabled:
                cache_key = self._get_cache_key(text)
                self._save_to_cache(cache_key, embedding)

        return embeddings_result  # type: ignore[return-value]

    def _generate_embeddings_api(self, texts: list[str]) -> list[list[float]]:
        """Génère des embeddings via une API OpenAI-compatible.

        Parameters
        ----------
        texts : list[str]
            Liste de textes à vectoriser.

        Returns:
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

        Returns:
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

        Returns:
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
