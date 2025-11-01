"""Module unifié de chargement des modèles (LLM + Embeddings).

Ce module gère le chargement dynamique des modèles depuis les providers
définis dans global.yaml. Architecture unifiée pour tous types de modèles.

Auteur: RAG Framework Team
Version: 1.0.0
"""

from rag_framework.models.loader import ModelLoader, load_model

__all__ = ["ModelLoader", "load_model"]
