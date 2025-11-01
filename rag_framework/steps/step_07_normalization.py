"""Étape 7 : Normalisation des données."""

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

            for chunk in chunks:
                normalized_chunk = chunk.copy()

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
