"""Étape 1 : Surveillance de fichiers sources."""

import time
from collections.abc import Callable
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from rag_framework.exceptions import StepExecutionError, ValidationError
from rag_framework.steps.base_step import BaseStep
from rag_framework.types import StepData
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class FileEventHandler(FileSystemEventHandler):
    """Handler pour les événements de fichiers détectés par Watchdog."""

    def __init__(self, file_patterns: list[str]) -> None:
        """Initialize the handler.

        Args:
            file_patterns: Liste de patterns de fichiers à surveiller (ex: *.pdf).
        """
        super().__init__()
        self.file_patterns = file_patterns
        self.detected_files: list[Path] = []

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if self._match_pattern(file_path):
                logger.info(f"Fichier détecté: {file_path}")
                self.detected_files.append(file_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if self._match_pattern(file_path):
                logger.info(f"Fichier modifié: {file_path}")
                self.detected_files.append(file_path)

    def _match_pattern(self, file_path: Path) -> bool:
        """Check if file matches any of the configured patterns."""
        for pattern in self.file_patterns:
            if file_path.match(pattern):
                return True
        return False


class MonitoringStep(BaseStep):
    """Étape 1 : Surveillance de fichiers sources avec Watchdog."""

    def validate_config(self) -> None:
        """Valide la configuration de l'étape."""
        required_keys = ["watch_paths", "file_patterns"]
        for key in required_keys:
            if key not in self.config:
                raise ValidationError(
                    f"Clé manquante dans la configuration: {key}",
                    details={"step": "MonitoringStep", "missing_key": key},
                )

        # Validate watch paths exist
        for path in self.config["watch_paths"]:
            path_obj = Path(path)
            if not path_obj.exists():
                logger.warning(f"Chemin de surveillance inexistant: {path}")

    def execute(self, data: StepData) -> StepData:
        """Surveille les répertoires configurés et détecte les nouveaux fichiers.

        Args:
            data: Données d'entrée (peut être vide pour cette étape).

        Returns:
            Données avec la liste des fichiers détectés ajoutée.

        Raises:
            StepExecutionError: En cas d'erreur durant la surveillance.
        """
        try:
            watch_paths = self.config["watch_paths"]
            file_patterns = self.config["file_patterns"]

            # Scan initial des fichiers existants
            detected_files: list[Path] = []
            for watch_path in watch_paths:
                path_obj = Path(watch_path)
                if path_obj.exists():
                    for pattern in file_patterns:
                        detected_files.extend(path_obj.rglob(pattern))

            logger.info(
                f"Monitoring: {len(detected_files)} fichiers détectés "
                f"dans {len(watch_paths)} répertoires"
            )

            data["monitored_files"] = [str(f) for f in detected_files]
            data["monitoring_config"] = self.config

            return data

        except Exception as e:
            raise StepExecutionError(
                step_name="MonitoringStep",
                message=f"Erreur lors de la surveillance: {e!s}",
                details={"error": str(e)},
            ) from e

    def watch_continuously(
        self,
        callback: Optional[Callable[[Path], None]] = None,
        duration_seconds: int = 60,
    ) -> list[Path]:
        """Surveille en continu les répertoires (mode daemon).

        Args:
            callback: Fonction à appeler lors de la détection d'un fichier.
            duration_seconds: Durée de surveillance en secondes.

        Returns:
            Liste des fichiers détectés durant la surveillance.
        """
        watch_paths = self.config["watch_paths"]
        file_patterns = self.config["file_patterns"]

        event_handler = FileEventHandler(file_patterns)
        observer = Observer()

        for watch_path in watch_paths:
            path_obj = Path(watch_path)
            if path_obj.exists():
                observer.schedule(  # type: ignore[no-untyped-call]
                    event_handler,
                    str(path_obj),
                    recursive=self.config.get("recursive", True),
                )

        observer.start()  # type: ignore[no-untyped-call]
        logger.info(f"Surveillance active pour {duration_seconds} secondes...")

        try:
            time.sleep(duration_seconds)
        finally:
            observer.stop()  # type: ignore[no-untyped-call]
            observer.join()

        return event_handler.detected_files
