"""Étape 7 : Normalisation des données."""

import re
import unicodedata
from typing import Any

import numpy as np
from numpy.typing import NDArray

from rag_framework.exceptions import StepExecutionError
from rag_framework.steps.base_step import BaseStep
from rag_framework.types import StepData
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class NormalizationStep(BaseStep):
    """Étape 7 : Normalisation des données."""

    def validate_config(self) -> None:
        """Valide la configuration de l'étape."""
        pass  # Configuration optionnelle

    def execute(self, data: StepData) -> StepData:
        """Normalise les embeddings et les métadonnées.

        Args:
            data: Données contenant 'embedded_chunks'.

        Returns:
            Données avec 'normalized_chunks' ajouté.

        Raises:
            StepExecutionError: En cas d'erreur durant la normalisation.
        """
        try:
            chunks = data.get("embedded_chunks", [])

            if not chunks:
                logger.warning("Aucun chunk à normaliser")
                data["normalized_chunks"] = []
                return data

            normalized_chunks = []

            validation_config = self.config.get("validation", {})
            validation_errors = []

            for chunk in chunks:
                normalized_chunk = chunk.copy()

                # Validation des embeddings
                if validation_config.get("validate_embeddings", True):
                    embedding = chunk.get("embedding")
                    is_valid, error_msg = self._validate_embedding(embedding)
                    if not is_valid:
                        validation_errors.append(
                            f"Chunk {chunk.get('chunk_index', '?')}: {error_msg}"
                        )
                        if validation_config.get("reject_invalid", False):
                            continue  # Skip invalid chunk

                # Validation des métadonnées
                if validation_config.get("validate_metadata", True):
                    is_valid, error_msg = self._validate_metadata_fields(chunk)
                    if not is_valid:
                        validation_errors.append(
                            f"Chunk {chunk.get('chunk_index', '?')}: {error_msg}"
                        )
                        if validation_config.get("reject_invalid", False):
                            continue  # Skip invalid chunk

                # Normalisation du texte
                if "text" in chunk:
                    normalized_chunk["text"] = self._normalize_text(chunk["text"])

                # Normalisation L2 des embeddings
                if self.config.get("vector_normalization", {}).get(
                    "normalize_l2", True
                ):
                    embedding = np.array(chunk["embedding"])
                    normalized_embedding = self._normalize_l2(embedding)
                    normalized_chunk["embedding"] = normalized_embedding.tolist()

                # Normalisation des métadonnées
                normalized_chunk["metadata"] = self._normalize_metadata(chunk)

                normalized_chunks.append(normalized_chunk)

            # Log des erreurs de validation si demandé
            log_errors = validation_config.get("log_validation_errors", True)
            if validation_errors and log_errors:
                error_count = len(validation_errors)
                logger.warning(
                    f"Normalization: {error_count} erreurs de validation"
                )
                for error in validation_errors[:5]:  # Log max 5 erreurs
                    logger.warning(f"  - {error}")

            data["normalized_chunks"] = normalized_chunks
            logger.info(f"Normalization: {len(normalized_chunks)} chunks normalisés")

            return data

        except Exception as e:
            raise StepExecutionError(
                step_name="NormalizationStep",
                message=f"Erreur lors de la normalisation: {e!s}",
                details={"error": str(e)},
            ) from e

    def _normalize_l2(self, vector: NDArray[np.float64]) -> NDArray[np.float64]:
        """Normalisation L2 d'un vecteur.

        Args:
            vector: Vecteur à normaliser.

        Returns:
            Vecteur normalisé.
        """
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm

    def _normalize_metadata(self, chunk: dict[str, Any]) -> dict[str, Any]:
        """Normalise les métadonnées d'un chunk.

        Args:
            chunk: Chunk avec métadonnées.

        Returns:
            Métadonnées normalisées.
        """
        metadata = {
            "source_file": chunk.get("source_file", ""),
            "chunk_index": chunk.get("chunk_index", 0),
            "content_hash": chunk.get("content_hash", ""),
            "sensitivity": chunk.get("sensitivity", "interne"),
            "document_type": chunk.get("document_type", "autre"),
            "regulatory_tags": chunk.get("regulatory_tags", []),
            "processed_at": chunk.get("processed_at", ""),
        }

        # Suppression valeurs nulles si configuré
        if self.config.get("metadata_normalization", {}).get(
            "remove_null_values", True
        ):
            metadata = {k: v for k, v in metadata.items() if v}

        return metadata

    def _normalize_text(self, text: str) -> str:
        """Normalise le texte selon la configuration.

        Parameters
        ----------
        text : str
            Texte à normaliser.

        Returns:
        -------
        str
            Texte normalisé.
        """
        text_config = self.config.get("text_normalization", {})

        # Normalisation Unicode (NFC, NFKC, NFD, NFKD)
        unicode_form = text_config.get("unicode_normalization", "NFC")
        if unicode_form in ("NFC", "NFKC", "NFD", "NFKD"):
            text = unicodedata.normalize(unicode_form, text)

        # Suppression des accents
        if text_config.get("remove_accents", False):
            # Décompose les caractères accentués puis supprime les marques diacritiques
            text = "".join(
                char
                for char in unicodedata.normalize("NFD", text)
                if unicodedata.category(char) != "Mn"
            )

        # Standardisation des guillemets
        if text_config.get("standardize_quotes", False):
            # Remplace tous les types de guillemets par des guillemets simples
            text = re.sub(r"[""«»'']", '"', text)
            text = re.sub(r"['']", "'", text)

        return text

    def _validate_embedding(self, embedding: object) -> tuple[bool, str]:
        """Valide un embedding vectoriel.

        Parameters
        ----------
        embedding : Any
            Embedding à valider.

        Returns:
        -------
        tuple[bool, str]
            (is_valid, error_message)
        """
        if embedding is None:
            return False, "Embedding manquant"

        if not isinstance(embedding, list):
            return False, f"Embedding doit être une liste, reçu {type(embedding)}"

        if len(embedding) == 0:
            return False, "Embedding vide"

        # Vérifier que tous les éléments sont des nombres
        try:
            arr = np.array(embedding, dtype=np.float64)
        except (ValueError, TypeError) as e:
            return False, f"Embedding contient des valeurs non numériques: {e}"

        # Vérifier NaN/Inf
        if np.any(np.isnan(arr)):
            return False, "Embedding contient des NaN"

        if np.any(np.isinf(arr)):
            return False, "Embedding contient des valeurs infinies"

        # Vérifier la norme (ne doit pas être nulle)
        norm = np.linalg.norm(arr)
        if norm == 0:
            return False, "Embedding a une norme nulle"

        return True, ""

    def _validate_metadata_fields(self, chunk: dict[str, Any]) -> tuple[bool, str]:
        """Valide les champs de métadonnées d'un chunk.

        Parameters
        ----------
        chunk : dict[str, Any]
            Chunk avec métadonnées.

        Returns:
        -------
        tuple[bool, str]
            (is_valid, error_message)
        """
        # Vérification des champs obligatoires
        required_fields = ["text", "source_file"]
        for field in required_fields:
            if field not in chunk or not chunk[field]:
                return False, f"Champ obligatoire manquant: {field}"

        # Vérification du type de texte
        if not isinstance(chunk["text"], str):
            text_type = type(chunk["text"])
            return False, f"Le champ 'text' doit être str, reçu {text_type}"

        # Vérification de la longueur du texte
        if len(chunk["text"].strip()) == 0:
            return False, "Le champ 'text' est vide"

        return True, ""
