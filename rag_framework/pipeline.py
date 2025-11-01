"""Orchestrateur principal du pipeline RAG."""

from pathlib import Path
from typing import Any, Optional

from rag_framework.config import load_config, load_step_config
from rag_framework.exceptions import RAGFrameworkError
from rag_framework.steps import (
    AuditStep,
    ChunkingStep,
    EmbeddingStep,
    EnrichmentStep,
    MonitoringStep,
    NormalizationStep,
    PreprocessingStep,
    VectorStorageStep,
)
from rag_framework.steps.base_step import BaseStep
from rag_framework.types import StepData
from rag_framework.utils.logger import get_logger, setup_logger
from rag_framework.validation import validate_dependencies

logger = get_logger(__name__)


class RAGPipeline:
    """Orchestrateur principal du pipeline RAG."""

    def __init__(self, config_dir: Path = Path("config")) -> None:
        """Initialize the RAG pipeline.

        Parameters
        ----------
        config_dir : Path, optional
            Répertoire contenant les fichiers de configuration.
            (default: Path("config"))
        """
        # Stockage du répertoire de configuration pour accès ultérieur
        self.config_dir = config_dir

        # Chargement de la configuration globale depuis config/global.yaml
        # Cette config contient les paramètres transversaux (VLM, logging, etc.)
        self.global_config = load_config(config_dir)

        # VALIDATION DES DÉPENDANCES ET PRÉREQUIS (fail-fast)
        # Vérifie dès le démarrage que toutes les dépendances sont disponibles
        # et que l'accès aux LLM providers est possible
        # Si échec → le processus s'arrête immédiatement (ConfigurationError)
        validate_dependencies(self.global_config)

        # Configuration du système de logging
        # Le logger est configuré AVANT l'initialisation des étapes pour
        # capturer tous les événements dès le début
        log_config = self.global_config.logging
        setup_logger(
            name="rag_framework",  # Nom du logger racine
            level=log_config.get("level", "INFO"),  # Niveau de log (INFO par défaut)
            log_file=log_config.get("log_file"),  # Fichier de destination
            log_format=log_config.get("format"),  # Format des messages
        )

        # Initialisation séquentielle des 8 étapes du pipeline
        # Chaque étape charge sa propre configuration YAML
        self.steps: list[BaseStep] = self._initialize_steps()

        # Log de confirmation avec comptage des étapes actives
        logger.info(
            f"Pipeline initialisé avec {len(self.steps)} étapes "
            f"({sum(1 for s in self.steps if s.enabled)} activées)"
        )

    def _initialize_steps(self) -> list[BaseStep]:
        """Initialise toutes les étapes du pipeline.

        Returns:
        -------
        list[BaseStep]
            Liste des étapes du pipeline.
        """
        # Liste pour accumuler les instances d'étapes
        steps: list[BaseStep] = []

        # Définition des 8 étapes du pipeline dans l'ordre d'exécution
        # Format: (Classe Python, Fichier de config YAML, Clé d'activation globale)
        # L'ordre est CRITIQUE : chaque étape dépend des sorties des précédentes
        step_classes = [
            (MonitoringStep, "01_monitoring.yaml", "monitoring_enabled"),
            (PreprocessingStep, "parser.yaml", "preprocessing_enabled"),
            (ChunkingStep, "03_chunking.yaml", "chunking_enabled"),
            (EnrichmentStep, "04_enrichment.yaml", "enrichment_enabled"),
            (AuditStep, "05_audit.yaml", "audit_enabled"),
            (EmbeddingStep, "06_embedding.yaml", "embedding_enabled"),
            (NormalizationStep, "07_normalization.yaml", "normalization_enabled"),
            (VectorStorageStep, "08_vector_storage.yaml", "vector_storage_enabled"),
        ]

        # Récupération des flags d'activation globaux depuis global.yaml
        global_steps_config = self.global_config.steps

        # Variable pour stocker la config monitoring (utilisée par preprocessing)
        monitoring_config: dict[str, Any] = {}

        # Boucle d'initialisation avec gestion d'erreur
        for step_class, config_file, global_enabled_key in step_classes:
            try:
                # Vérification de l'activation de l'étape dans global.yaml
                # C'est le SEUL endroit où l'activation est contrôlée.
                # Les fichiers de config individuels (01_*.yaml à 08_*.yaml)
                # ne contiennent AUCUN paramètre d'activation.
                global_enabled = global_steps_config.get(global_enabled_key, True)

                if not global_enabled:
                    logger.info(
                        f"Étape {step_class.__name__} désactivée globalement "
                        f"({global_enabled_key}=false dans global.yaml)"
                    )
                    continue  # Passer à l'étape suivante sans initialiser

                # Chargement de la configuration spécifique à cette étape
                step_config = load_step_config(config_file, self.config_dir)

                # Cas spécial: MonitoringStep - sauvegarder la config pour preprocessing
                if step_class.__name__ == "MonitoringStep":
                    monitoring_config = step_config

                # Cas spécial: PreprocessingStep - transférer file_management et output du monitoring
                if step_class.__name__ == "PreprocessingStep" and monitoring_config:
                    # Transfert de la configuration file_management depuis monitoring
                    if "file_management" in monitoring_config:
                        step_config["file_management"] = monitoring_config[
                            "file_management"
                        ]
                        logger.debug(
                            "Configuration file_management transférée de monitoring vers preprocessing"
                        )

                    # Transfert de la configuration output depuis monitoring
                    if "output" in monitoring_config:
                        step_config["output"] = monitoring_config["output"]
                        logger.debug(
                            "Configuration output transférée de monitoring vers preprocessing"
                        )

                # Instanciation de l'étape avec sa config
                # Le constructeur appelle automatiquement validate_config()
                step = step_class(step_config)

                # Ajout à la liste des étapes
                steps.append(step)

                # Log de confirmation (niveau DEBUG pour éviter verbosité)
                logger.debug(f"Étape initialisée: {step_class.__name__}")

            except Exception as e:
                # En cas d'erreur, logger et propager l'exception
                # Le pipeline ne peut pas démarrer avec une étape défaillante
                logger.error(f"Erreur initialisation {step_class.__name__}: {e}")
                raise  # Re-raise pour arrêter le pipeline

        return steps

    def execute(self, input_data: Optional[StepData] = None) -> StepData:
        """Exécute séquentiellement toutes les étapes du pipeline.

        Parameters
        ----------
        input_data : Optional[StepData], optional
            Données d'entrée optionnelles (default: None).

        Returns:
        -------
        StepData
            Données de sortie après toutes les étapes.

        Raises:
        ------
        RAGFrameworkError
            En cas d'erreur durant l'exécution.
        """
        # Initialisation du dictionnaire de données si non fourni
        # Ce dictionnaire est passé et enrichi à chaque étape
        data = input_data or {}

        # En-tête visuel pour les logs (facilite le suivi dans les fichiers de log)
        logger.info("=" * 60)
        logger.info("DÉMARRAGE DU PIPELINE RAG")
        logger.info("=" * 60)

        # Exécution séquentielle de chaque étape
        # enumerate(..., 1) pour numérotation à partir de 1 (plus lisible)
        for idx, step in enumerate(self.steps, 1):
            # Vérification du flag enabled : skip si désactivée
            if not step.enabled:
                logger.info(f"[{idx}/8] {step.__class__.__name__}: DÉSACTIVÉE")
                continue  # Passe à l'étape suivante sans exécution

            try:
                # Log de début d'étape avec indicateur de progression [X/8]
                logger.info(f"[{idx}/8] {step.__class__.__name__}: DÉBUT")

                # Exécution de l'étape avec les données courantes
                # La méthode execute() DOIT retourner un dict enrichi
                # Les données en sortie deviennent l'entrée de l'étape suivante
                data = step.execute(data)
                logger.info(f"[{idx}/8] {step.__class__.__name__}: TERMINÉE ✓")

            except Exception as e:
                logger.error(
                    f"[{idx}/8] {step.__class__.__name__}: ERREUR",
                    exc_info=True,
                )
                raise RAGFrameworkError(
                    f"Erreur à l'étape {step.__class__.__name__}",
                    details={"step": step.__class__.__name__, "error": str(e)},
                ) from e

        logger.info("=" * 60)
        logger.info("PIPELINE TERMINÉ AVEC SUCCÈS")
        logger.info("=" * 60)

        return data

    def execute_step(self, step_name: str, input_data: StepData) -> StepData:
        """Exécute une étape spécifique du pipeline.

        Args:
            step_name: Nom de l'étape à exécuter.
            input_data: Données d'entrée.

        Returns:
            Données de sortie de l'étape.

        Raises:
            ValueError: Si l'étape n'existe pas.
        """
        for step in self.steps:
            if step.__class__.__name__ == step_name:
                return step.execute(input_data)

        raise ValueError(f"Étape introuvable: {step_name}")

    def get_step(self, step_name: str) -> BaseStep:
        """Récupère une étape spécifique du pipeline.

        Args:
            step_name: Nom de l'étape.

        Returns:
            Instance de l'étape.

        Raises:
            ValueError: Si l'étape n'existe pas.
        """
        for step in self.steps:
            if step.__class__.__name__ == step_name:
                return step

        raise ValueError(f"Étape introuvable: {step_name}")

    def get_status(self) -> dict[str, Any]:
        """Récupère le statut du pipeline.

        Returns:
            Dictionnaire contenant le statut de toutes les étapes.
        """
        return {
            "total_steps": len(self.steps),
            "enabled_steps": sum(1 for s in self.steps if s.enabled),
            "steps": [
                {
                    "name": step.__class__.__name__,
                    "enabled": step.enabled,
                }
                for step in self.steps
            ],
        }
