"""Module de chargement des modèles d'embeddings.

Ce module gère le chargement dynamique des modèles d'embeddings
depuis les providers définis dans global.yaml.

Auteur: RAG Framework Team
Version: 1.0.0
"""

from rag_framework.preprocessing.embeddings.loader import EmbeddingLoader

__all__ = ["EmbeddingLoader"]
