"""Classe abstraite de base pour toutes les étapes du pipeline RAG."""

from abc import ABC, abstractmethod
from typing import Any

from rag_framework.types import StepData


class BaseStep(ABC):
    """Classe de base pour toutes les étapes du pipeline RAG."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the step.

        Args:
            config: Configuration de l'étape chargée depuis YAML.

        Note:
            L'activation des étapes est contrôlée centralement dans
            config/global.yaml via la section 'steps'. Une étape n'est
            instanciée que si elle est activée globalement, donc self.enabled
            est toujours True pour les étapes instanciées.
        """
        self.config = config
        # L'étape est toujours enabled si elle est instanciée
        # (contrôle d'activation fait en amont par le pipeline)
        self.enabled = True
        self.validate_config()

    @abstractmethod
    def validate_config(self) -> None:
        """Valide la configuration de l'étape.

        Raises:
            ValidationError: Si la configuration est invalide.
        """
        pass

    @abstractmethod
    def execute(self, data: StepData) -> StepData:
        """Exécute la logique métier de l'étape.

        Args:
            data: Dictionnaire contenant les données à traiter.
                  Les clés attendues dépendent de l'étape.

        Returns:
            Dictionnaire avec les données transformées.

        Raises:
            StepExecutionError: En cas d'erreur durant l'exécution.
        """
        pass

    def __call__(self, data: StepData) -> StepData:
        """Permet d'appeler l'étape comme une fonction.

        Args:
            data: Données à traiter.

        Returns:
            Données transformées.
        """
        if not self.enabled:
            return data
        return self.execute(data)

    def __repr__(self) -> str:
        """Représentation textuelle de l'étape."""
        return f"{self.__class__.__name__}(enabled={self.enabled})"
