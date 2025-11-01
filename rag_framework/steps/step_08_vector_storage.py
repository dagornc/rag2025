"""Étape 8 : Stockage vectoriel."""

import hashlib
import uuid
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from rag_framework.exceptions import StepExecutionError, ValidationError
from rag_framework.steps.base_step import BaseStep
from rag_framework.types import StepData
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class VectorStorageStep(BaseStep):
    """Étape 8 : Stockage vectoriel."""

    def validate_config(self) -> None:
        """Valide la configuration de l'étape."""
        if "provider" not in self.config:
            raise ValidationError(
                "Clé 'provider' manquante dans la configuration",
                details={"step": "VectorStorageStep"},
            )

        provider = self.config["provider"]
        if provider not in ["chromadb", "qdrant"]:
            raise ValidationError(
                f"Provider inconnu: {provider}",
                details={"step": "VectorStorageStep", "provider": provider},
            )

    def execute(self, data: StepData) -> StepData:
        """Stocke les chunks vectorisés dans le vector store.

        Args:
            data: Données contenant 'normalized_chunks'.

        Returns:
            Données avec 'storage_result' ajouté.

        Raises:
            StepExecutionError: En cas d'erreur durant le stockage.
        """
        try:
            chunks = data.get("normalized_chunks", [])

            if not chunks:
                logger.warning("Aucun chunk à stocker")
                data["storage_result"] = {"stored_count": 0}
                return data

            provider = self.config["provider"]

            if provider == "chromadb":
                result = self._store_chromadb(chunks)
            elif provider == "qdrant":
                result = self._store_qdrant(chunks)
            else:
                raise StepExecutionError(
                    step_name="VectorStorageStep",
                    message=f"Provider non supporté: {provider}",
                    details={"provider": provider},
                )

            data["storage_result"] = result
            logger.info(
                f"Vector Storage: {result['stored_count']} chunks stockés "
                f"dans {provider}"
            )

            return data

        except Exception as e:
            raise StepExecutionError(
                step_name="VectorStorageStep",
                message=f"Erreur lors du stockage vectoriel: {e!s}",
                details={"error": str(e)},
            ) from e

    def _store_chromadb(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        """Stocke dans ChromaDB.

        Args:
            chunks: Chunks à stocker avec embeddings et métadonnées.

        Returns:
            Résultat du stockage avec statistiques.

        Raises:
            StepExecutionError: En cas d'erreur durant le stockage.
        """
        chroma_config = self.config.get("chromadb", {})
        persist_dir = chroma_config.get("persist_directory", "./chroma_db")
        collection_name = chroma_config.get("collection_name", "compliance_docs")
        distance_metric = chroma_config.get("distance_metric", "cosine")

        # Création du répertoire de persistance
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        try:
            # Initialisation du client ChromaDB persistant
            logger.info(f"Initialisation ChromaDB dans: {persist_dir}")

            client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(
                    anonymized_telemetry=chroma_config.get(
                        "anonymized_telemetry", False
                    ),
                    allow_reset=False,
                ),
            )

            # Récupération ou création de la collection
            # NOTE: ChromaDB 1.x utilise get_or_create_collection
            collection_metadata = chroma_config.get("collection_metadata", {})
            collection_metadata["distance_metric"] = distance_metric

            try:
                collection = client.get_or_create_collection(
                    name=collection_name,
                    metadata=collection_metadata,
                )
                logger.info(
                    f"Collection '{collection_name}' récupérée/créée "
                    f"(distance: {distance_metric})"
                )
            except Exception as e:
                raise StepExecutionError(
                    step_name="VectorStorageStep",
                    message=f"Erreur création collection ChromaDB: {e}",
                    details={"collection_name": collection_name},
                ) from e

            # Préparation des données pour ChromaDB
            ids: list[str] = []
            embeddings: list[list[float]] = []
            documents: list[str] = []
            metadatas: list[dict[str, Any]] = []

            for chunk in chunks:
                # Génération d'un ID unique pour le chunk
                # Utilise content_hash si disponible, sinon génère UUID
                chunk_id = chunk.get("content_hash")
                if not chunk_id:
                    # Génération ID basé sur le contenu
                    content = chunk.get("text", chunk.get("content", ""))
                    chunk_id = hashlib.sha256(content.encode()).hexdigest()[:16]

                # Vérification que l'ID est unique (ChromaDB n'accepte pas les doublons)
                if chunk_id in ids:
                    chunk_id = f"{chunk_id}_{uuid.uuid4().hex[:8]}"

                ids.append(chunk_id)

                # Embedding (déjà normalisé par étape 7)
                embeddings.append(chunk["embedding"])

                # Document (texte du chunk)
                documents.append(chunk.get("text", chunk.get("content", "")))

                # Métadonnées (nettoyées pour ChromaDB)
                metadata = chunk.get("metadata", {}).copy()

                # ChromaDB n'accepte que certains types dans les métadonnées
                # Conversion des listes en strings si nécessaire
                cleaned_metadata: dict[str, Any] = {}
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        cleaned_metadata[key] = value
                    elif isinstance(value, list):
                        # Conversion liste → string JSON ou string séparé par virgules
                        cleaned_metadata[key] = ", ".join(map(str, value))
                    else:
                        # Autres types → conversion en string
                        cleaned_metadata[key] = str(value)

                metadatas.append(cleaned_metadata)

            # Configuration du batch
            batch_size = self.config.get("indexing", {}).get("batch_size", 100)
            show_progress = self.config.get("indexing", {}).get("show_progress", True)

            # Stockage par batch
            total_stored = 0
            failed_chunks = 0

            logger.info(
                f"Stockage de {len(chunks)} chunks dans ChromaDB "
                f"(batch_size={batch_size})"
            )

            for i in range(0, len(ids), batch_size):
                batch_end = min(i + batch_size, len(ids))

                try:
                    collection.add(
                        ids=ids[i:batch_end],
                        embeddings=embeddings[i:batch_end],
                        documents=documents[i:batch_end],
                        metadatas=metadatas[i:batch_end],
                    )
                    total_stored += batch_end - i

                    if show_progress:
                        logger.info(
                            f"  Batch {i // batch_size + 1}: "
                            f"{total_stored}/{len(ids)} chunks stockés"
                        )

                except Exception as e:
                    logger.error(
                        f"Erreur stockage batch {i // batch_size + 1}: {e}",
                        exc_info=True,
                    )
                    failed_chunks += batch_end - i

            # Vérification du nombre de documents dans la collection
            collection_count = collection.count()

            logger.info(
                f"✓ ChromaDB: {total_stored} chunks stockés avec succès "
                f"(échecs: {failed_chunks}, total collection: {collection_count})"
            )

            return {
                "provider": "chromadb",
                "stored_count": total_stored,
                "failed_count": failed_chunks,
                "collection_name": collection_name,
                "collection_count": collection_count,
                "persist_directory": str(persist_dir),
                "distance_metric": distance_metric,
            }

        except Exception as e:
            logger.error(f"Erreur lors du stockage ChromaDB: {e}", exc_info=True)
            raise StepExecutionError(
                step_name="VectorStorageStep",
                message=f"Erreur stockage ChromaDB: {e}",
                details={"persist_directory": persist_dir},
            ) from e

    def _store_qdrant(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        """Stocke dans Qdrant.

        Args:
            chunks: Chunks à stocker.

        Returns:
            Résultat du stockage.
        """
        # MVP: simulation du stockage
        # En production, utiliser qdrant-client
        logger.warning("Stockage Qdrant simulé (implémentation requise)")

        return {
            "provider": "qdrant",
            "stored_count": len(chunks),
            "collection_name": self.config.get("qdrant", {}).get(
                "collection_name", "compliance_docs"
            ),
            "url": self.config.get("qdrant", {}).get("url", "http://localhost:6333"),
        }
