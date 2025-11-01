"""Exceptions spécifiques au framework RAG."""

from typing import Any, Optional


class RAGFrameworkError(Exception):
    """Classe de base pour toutes les exceptions du framework."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        """Initialize the exception.

        Parameters
        ----------
        message : str
            Message d'erreur descriptif.
        details : Optional[dict[str, Any]], optional
            Détails additionnels sur l'erreur (default: None).
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(RAGFrameworkError):
    """Exception levée lors d'erreurs de configuration."""

    pass


class ValidationError(RAGFrameworkError):
    """Exception levée lors d'erreurs de validation."""

    pass


class StepExecutionError(RAGFrameworkError):
    """Exception levée lors d'erreurs d'exécution d'une étape."""

    def __init__(
        self,
        step_name: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize the exception.

        Parameters
        ----------
        step_name : str
            Nom de l'étape en erreur.
        message : str
            Message d'erreur descriptif.
        details : Optional[dict[str, Any]], optional
            Détails additionnels sur l'erreur (default: None).
        """
        super().__init__(message, details)
        self.step_name = step_name


class FileProcessingError(RAGFrameworkError):
    """Exception levée lors d'erreurs de traitement de fichiers."""

    pass


class EmbeddingError(RAGFrameworkError):
    """Exception levée lors d'erreurs de génération d'embeddings."""

    pass


class VectorStoreError(RAGFrameworkError):
    """Exception levée lors d'erreurs avec le vector store."""

    pass
