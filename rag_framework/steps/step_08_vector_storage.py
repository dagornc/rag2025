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
        valid_providers = ["chromadb", "qdrant", "pgvector", "milvus", "weaviate"]
        if provider not in valid_providers:
            raise ValidationError(
                f"Provider inconnu: {provider}. Providers valides: {valid_providers}",
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
            elif provider == "pgvector":
                result = self._store_pgvector(chunks)
            elif provider == "milvus":
                result = self._store_milvus(chunks)
            elif provider == "weaviate":
                result = self._store_weaviate(chunks)
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

            # Suppression des chunks existants pour les mêmes fichiers (si activé)
            delete_existing = self.config.get("indexing", {}).get(
                "delete_existing_by_filename", False
            )

            if delete_existing:
                # Extraction des noms de fichiers uniques depuis les métadonnées
                unique_filenames = set()
                for metadata in metadatas:
                    filename = (
                        metadata.get("file_name")
                        or metadata.get("source_file")
                        or metadata.get("filename")
                    )
                    if filename:
                        unique_filenames.add(filename)

                if unique_filenames:
                    logger.info(
                        f"Suppression des chunks existants pour "
                        f"{len(unique_filenames)} fichiers: {list(unique_filenames)}"
                    )

                    # Suppression par filename
                    deleted_count = 0
                    for filename in unique_filenames:
                        try:
                            # Recherche des IDs à supprimer via where filter
                            results = collection.get(
                                where={
                                    "$or": [
                                        {"file_name": filename},
                                        {"source_file": filename},
                                        {"filename": filename},
                                    ]
                                }
                            )

                            if results and results.get("ids"):
                                ids_to_delete = results["ids"]
                                collection.delete(ids=ids_to_delete)
                                deleted_count += len(ids_to_delete)
                                logger.info(
                                    f"  ✓ Supprimé {len(ids_to_delete)} chunks "
                                    f"pour '{filename}'"
                                )
                        except Exception as e:
                            logger.warning(
                                f"  ✗ Erreur suppression pour '{filename}': {e}"
                            )

                    logger.info(
                        f"✓ Total supprimé: {deleted_count} chunks "
                        f"pour {len(unique_filenames)} fichiers"
                    )

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

    def _store_pgvector(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        """Stocke dans pgvector (PostgreSQL).

        Args:
            chunks: Chunks à stocker avec embeddings et métadonnées.

        Returns:
            Résultat du stockage avec statistiques.

        Raises:
            StepExecutionError: En cas d'erreur durant le stockage.
        """
        try:
            import psycopg2  # type: ignore[import-untyped]
            from psycopg2.extras import execute_values  # type: ignore[import-untyped]
        except ImportError:
            error_msg = (
                "psycopg2 non installé. Installez avec: pip install psycopg2-binary"
            )
            logger.error(error_msg)
            raise StepExecutionError(
                step_name="VectorStorageStep",
                message=error_msg,
                details={"provider": "pgvector"},
            )

        pgvector_config = self.config.get("pgvector", {})

        # Connexion à PostgreSQL
        conn_string = pgvector_config.get("connection_string")
        if not conn_string:
            # Construction depuis paramètres individuels
            host = pgvector_config.get("host", "localhost")
            port = pgvector_config.get("port", 5432)
            database = pgvector_config.get("database", "vectordb")
            user = pgvector_config.get("user", "postgres")
            password = pgvector_config.get("password", "")
            conn_string = f"host={host} port={port} dbname={database} user={user} password={password}"

        table_name = pgvector_config.get("table_name", "compliance_docs")
        vector_dim = pgvector_config.get("vector_dimension", 3072)
        distance_metric = pgvector_config.get("distance_metric", "cosine")
        create_table = pgvector_config.get("create_table_if_not_exists", True)
        delete_existing = self.config.get("indexing", {}).get(
            "delete_existing_by_filename", False
        )

        try:
            logger.info(f"Connexion à PostgreSQL/pgvector: {database}@{host}")
            conn = psycopg2.connect(conn_string)
            cur = conn.cursor()

            # Activation de l'extension pgvector
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # Création de la table si nécessaire
            if create_table:
                operator_map = {
                    "cosine": "<=>",
                    "l2": "<->",
                    "inner_product": "<#>",
                }

                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id TEXT PRIMARY KEY,
                        embedding vector({vector_dim}),
                        content TEXT,
                        metadata JSONB,
                        file_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Index pour recherche rapide
                index_type = pgvector_config.get("index_type", "ivfflat")
                if index_type == "ivfflat":
                    lists = pgvector_config.get("index_lists", 100)
                    op = operator_map.get(distance_metric, "<=>")
                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS {table_name}_embedding_idx
                        ON {table_name} USING ivfflat (embedding {op})
                        WITH (lists = {lists})
                    """)

                conn.commit()
                logger.info(f"Table '{table_name}' créée/vérifiée")

            # Suppression des chunks existants (si activé)
            deleted_count = 0
            if delete_existing:
                unique_filenames = set()
                for chunk in chunks:
                    metadata = chunk.get("metadata", {})
                    filename = (
                        metadata.get("file_name")
                        or metadata.get("source_file")
                        or metadata.get("filename")
                    )
                    if filename:
                        unique_filenames.add(filename)

                if unique_filenames:
                    logger.info(
                        f"Suppression des chunks existants pour "
                        f"{len(unique_filenames)} fichiers"
                    )
                    for filename in unique_filenames:
                        cur.execute(
                            f"DELETE FROM {table_name} WHERE file_name = %s",
                            (filename,),
                        )
                        deleted_count += cur.rowcount
                    conn.commit()
                    logger.info(f"✓ {deleted_count} chunks supprimés")

            # Insertion des chunks
            batch_size = self.config.get("indexing", {}).get("batch_size", 100)
            total_stored = 0

            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]

                values = []
                for chunk in batch:
                    chunk_id = chunk.get("content_hash", str(uuid.uuid4()))
                    embedding = chunk["embedding"]
                    content = chunk.get("text", chunk.get("content", ""))
                    metadata = chunk.get("metadata", {})
                    filename = (
                        metadata.get("file_name")
                        or metadata.get("source_file")
                        or metadata.get("filename")
                        or ""
                    )

                    # Conversion metadata en JSONB
                    import json

                    metadata_json = json.dumps(metadata)

                    values.append(
                        (chunk_id, embedding, content, metadata_json, filename)
                    )

                execute_values(
                    cur,
                    f"""INSERT INTO {table_name} (id, embedding, content, metadata, file_name)
                        VALUES %s ON CONFLICT (id) DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        content = EXCLUDED.content,
                        metadata = EXCLUDED.metadata,
                        file_name = EXCLUDED.file_name""",
                    values,
                )
                total_stored += len(batch)
                logger.info(f"  Batch: {total_stored}/{len(chunks)} chunks stockés")

            conn.commit()
            cur.close()
            conn.close()

            logger.info(f"✓ pgvector: {total_stored} chunks stockés avec succès")

            return {
                "provider": "pgvector",
                "stored_count": total_stored,
                "deleted_count": deleted_count,
                "table_name": table_name,
                "database": database,
                "distance_metric": distance_metric,
            }

        except Exception as e:
            logger.error(f"Erreur lors du stockage pgvector: {e}", exc_info=True)
            raise StepExecutionError(
                step_name="VectorStorageStep",
                message=f"Erreur stockage pgvector: {e}",
                details={"table_name": table_name},
            ) from e

    def _store_milvus(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        """Stocke dans Milvus.

        Args:
            chunks: Chunks à stocker avec embeddings et métadonnées.

        Returns:
            Résultat du stockage avec statistiques.

        Raises:
            StepExecutionError: En cas d'erreur durant le stockage.
        """
        try:
            from pymilvus import (  # type: ignore[import-untyped]
                Collection,
                CollectionSchema,
                DataType,
                FieldSchema,
                connections,
                utility,
            )
        except ImportError:
            error_msg = "pymilvus non installé. Installez avec: pip install pymilvus"
            logger.error(error_msg)
            raise StepExecutionError(
                step_name="VectorStorageStep",
                message=error_msg,
                details={"provider": "milvus"},
            )

        milvus_config = self.config.get("milvus", {})
        host = milvus_config.get("host", "localhost")
        port = milvus_config.get("port", 19530)
        collection_name = milvus_config.get("collection_name", "compliance_docs")
        vector_dim = milvus_config.get("vector_dimension", 3072)
        metric_type = milvus_config.get("metric_type", "COSINE")
        index_type = milvus_config.get("index_type", "IVF_FLAT")
        consistency_level = milvus_config.get("consistency_level", "Strong")
        create_collection = milvus_config.get("create_collection_if_not_exists", True)
        delete_existing = self.config.get("indexing", {}).get(
            "delete_existing_by_filename", False
        )

        try:
            logger.info(f"Connexion à Milvus: {host}:{port}")
            connections.connect("default", host=host, port=port)

            # Création de la collection si nécessaire
            if create_collection and not utility.has_collection(collection_name):
                fields = [
                    FieldSchema(
                        name="id",
                        dtype=DataType.VARCHAR,
                        is_primary=True,
                        max_length=100,
                    ),
                    FieldSchema(
                        name="embedding", dtype=DataType.FLOAT_VECTOR, dim=vector_dim
                    ),
                    FieldSchema(
                        name="content", dtype=DataType.VARCHAR, max_length=65535
                    ),
                    FieldSchema(
                        name="file_name", dtype=DataType.VARCHAR, max_length=500
                    ),
                ]
                schema = CollectionSchema(fields, description="Compliance documents")
                collection = Collection(
                    collection_name, schema, consistency_level=consistency_level
                )

                # Création de l'index
                index_params = milvus_config.get("index_params", {"nlist": 128})
                collection.create_index(
                    "embedding",
                    {
                        "index_type": index_type,
                        "metric_type": metric_type,
                        "params": index_params,
                    },
                )
                logger.info(f"Collection '{collection_name}' créée")
            else:
                collection = Collection(
                    collection_name, consistency_level=consistency_level
                )

            # Suppression des chunks existants (si activé)
            deleted_count = 0
            if delete_existing:
                unique_filenames = set()
                for chunk in chunks:
                    metadata = chunk.get("metadata", {})
                    filename = (
                        metadata.get("file_name")
                        or metadata.get("source_file")
                        or metadata.get("filename")
                    )
                    if filename:
                        unique_filenames.add(filename)

                if unique_filenames:
                    logger.info(
                        f"Suppression des chunks existants pour "
                        f"{len(unique_filenames)} fichiers"
                    )
                    for filename in unique_filenames:
                        expr = f'file_name == "{filename}"'
                        collection.delete(expr)
                        deleted_count += 1  # Milvus ne retourne pas le nombre exact
                    logger.info(
                        f"✓ Chunks supprimés pour {len(unique_filenames)} fichiers"
                    )

            # Préparation des données
            ids = []
            embeddings = []
            contents = []
            filenames = []

            for chunk in chunks:
                chunk_id = chunk.get("content_hash", str(uuid.uuid4()))[:100]
                ids.append(chunk_id)
                embeddings.append(chunk["embedding"])
                contents.append(chunk.get("text", chunk.get("content", ""))[:65535])

                metadata = chunk.get("metadata", {})
                filename = (
                    metadata.get("file_name")
                    or metadata.get("source_file")
                    or metadata.get("filename")
                    or ""
                )[:500]
                filenames.append(filename)

            # Insertion
            data = [ids, embeddings, contents, filenames]
            collection.insert(data)
            collection.flush()

            logger.info(f"✓ Milvus: {len(chunks)} chunks stockés avec succès")

            return {
                "provider": "milvus",
                "stored_count": len(chunks),
                "deleted_count": deleted_count,
                "collection_name": collection_name,
                "metric_type": metric_type,
                "index_type": index_type,
            }

        except Exception as e:
            logger.error(f"Erreur lors du stockage Milvus: {e}", exc_info=True)
            raise StepExecutionError(
                step_name="VectorStorageStep",
                message=f"Erreur stockage Milvus: {e}",
                details={"collection_name": collection_name},
            ) from e

    def _store_weaviate(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        """Stocke dans Weaviate.

        Args:
            chunks: Chunks à stocker avec embeddings et métadonnées.

        Returns:
            Résultat du stockage avec statistiques.

        Raises:
            StepExecutionError: En cas d'erreur durant le stockage.
        """
        try:
            import weaviate  # type: ignore[import-untyped]
        except ImportError:
            error_msg = "weaviate-client non installé. Installez avec: pip install weaviate-client"
            logger.error(error_msg)
            raise StepExecutionError(
                step_name="VectorStorageStep",
                message=error_msg,
                details={"provider": "weaviate"},
            )

        weaviate_config = self.config.get("weaviate", {})
        url = weaviate_config.get("url", "http://localhost:8080")
        api_key = weaviate_config.get("api_key")
        class_name = weaviate_config.get("class_name", "ComplianceDocs")
        distance_metric = weaviate_config.get("distance_metric", "cosine")
        delete_existing = self.config.get("indexing", {}).get(
            "delete_existing_by_filename", False
        )

        try:
            logger.info(f"Connexion à Weaviate: {url}")

            # Connexion (avec ou sans API key)
            if api_key and api_key != "WEAVIATE_API_KEY_NOT_SET":
                client = weaviate.Client(
                    url=url, auth_client_secret=weaviate.AuthApiKey(api_key=api_key)
                )
            else:
                client = weaviate.Client(url=url)

            # Création de la classe si nécessaire
            if not client.schema.exists(class_name):
                vector_config = weaviate_config.get("vector_index_config", {})
                class_obj = {
                    "class": class_name,
                    "vectorizer": weaviate_config.get("vectorizer", "none"),
                    "vectorIndexType": weaviate_config.get("vector_index_type", "hnsw"),
                    "vectorIndexConfig": {
                        "distance": distance_metric,
                        "efConstruction": vector_config.get("ef_construction", 128),
                        "maxConnections": vector_config.get("max_connections", 64),
                        "ef": vector_config.get("ef", -1),
                    },
                    "properties": [
                        {"name": "content", "dataType": ["text"]},
                        {"name": "fileName", "dataType": ["string"]},
                        {"name": "metadata", "dataType": ["text"]},
                    ],
                }
                client.schema.create_class(class_obj)
                logger.info(f"Classe '{class_name}' créée")

            # Suppression des chunks existants (si activé)
            deleted_count = 0
            if delete_existing:
                unique_filenames = set()
                for chunk in chunks:
                    metadata = chunk.get("metadata", {})
                    filename = (
                        metadata.get("file_name")
                        or metadata.get("source_file")
                        or metadata.get("filename")
                    )
                    if filename:
                        unique_filenames.add(filename)

                if unique_filenames:
                    logger.info(
                        f"Suppression des chunks existants pour "
                        f"{len(unique_filenames)} fichiers"
                    )
                    for filename in unique_filenames:
                        where_filter = {
                            "path": ["fileName"],
                            "operator": "Equal",
                            "valueString": filename,
                        }
                        result = client.batch.delete_objects(
                            class_name=class_name, where=where_filter
                        )
                        deleted_count += result.get("successful", 0)
                    logger.info(f"✓ {deleted_count} chunks supprimés")

            # Insertion par batch
            batch_size = self.config.get("indexing", {}).get("batch_size", 100)
            total_stored = 0

            with client.batch as batch:
                batch.batch_size = batch_size

                for chunk in chunks:
                    properties = {
                        "content": chunk.get("text", chunk.get("content", "")),
                        "fileName": chunk.get("metadata", {}).get(
                            "file_name",
                            chunk.get("metadata", {}).get("source_file", ""),
                        ),
                        "metadata": str(chunk.get("metadata", {})),
                    }

                    batch.add_data_object(
                        properties, class_name, vector=chunk["embedding"]
                    )
                    total_stored += 1

            logger.info(f"✓ Weaviate: {total_stored} chunks stockés avec succès")

            return {
                "provider": "weaviate",
                "stored_count": total_stored,
                "deleted_count": deleted_count,
                "class_name": class_name,
                "url": url,
                "distance_metric": distance_metric,
            }

        except Exception as e:
            logger.error(f"Erreur lors du stockage Weaviate: {e}", exc_info=True)
            raise StepExecutionError(
                step_name="VectorStorageStep",
                message=f"Erreur stockage Weaviate: {e}",
                details={"class_name": class_name},
            ) from e
