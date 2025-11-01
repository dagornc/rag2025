"""Étape 1 : Surveillance de fichiers sources."""

import json
import shutil
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

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
            file_path = Path(str(event.src_path))
            if self._match_pattern(file_path):
                logger.info(f"Fichier détecté: {file_path}")
                self.detected_files.append(file_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if not event.is_directory:
            file_path = Path(str(event.src_path))
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
            exclude_patterns = self.config.get("exclude_patterns", [])

            # Scan initial des fichiers existants
            detected_files: list[Path] = []
            for watch_path in watch_paths:
                path_obj = Path(watch_path)
                if path_obj.exists():
                    for pattern in file_patterns:
                        for file_path in path_obj.rglob(pattern):
                            # Filtrer les fichiers exclus
                            if not self._is_excluded(file_path, exclude_patterns):
                                detected_files.append(file_path)

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

    def _is_excluded(self, file_path: Path, exclude_patterns: list[str]) -> bool:
        """Vérifie si un fichier correspond à un pattern d'exclusion.

        Parameters
        ----------
        file_path : Path
            Chemin du fichier à vérifier.
        exclude_patterns : list[str]
            Liste des patterns d'exclusion (glob).

        Returns:
        -------
        bool
            True si le fichier doit être exclu, False sinon.
        """
        for pattern in exclude_patterns:
            if file_path.match(pattern):
                return True
        return False

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
                observer.schedule(
                    event_handler,
                    str(path_obj),
                    recursive=self.config.get("recursive", True),
                )

        observer.start()
        logger.info(f"Surveillance active pour {duration_seconds} secondes...")

        try:
            time.sleep(duration_seconds)
        finally:
            observer.stop()
            observer.join()

        return event_handler.detected_files

    def move_processed_file(
        self, file_path: Path, success: bool = True
    ) -> Optional[Path]:
        """Déplace un fichier traité vers le répertoire approprié.

        Parameters
        ----------
        file_path : Path
            Chemin du fichier à déplacer.
        success : bool
            True si traitement réussi (→ processed), False si erreur (→ errors).

        Returns:
        -------
        Optional[Path]
            Chemin du fichier déplacé, None si désactivé ou erreur.
        """
        file_mgmt = self.config.get("file_management", {})

        if not file_mgmt.get("enabled", False):
            return None

        if success and not file_mgmt.get("move_processed", True):
            return None

        if not success and not file_mgmt.get("move_errors", True):
            return None

        try:
            # Déterminer le répertoire de destination
            target_dir_key = "processed_dir" if success else "errors_dir"
            target_dir = Path(file_mgmt.get(target_dir_key, ""))

            if not target_dir:
                return None

            # Créer le répertoire cible s'il n'existe pas
            target_dir.mkdir(parents=True, exist_ok=True)

            # Construire le nom du fichier cible
            target_name = file_path.name

            # Ajouter timestamp si demandé
            if file_mgmt.get("add_timestamp", False):
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                stem = file_path.stem
                suffix = file_path.suffix
                target_name = f"{stem}_{timestamp}{suffix}"

            target_path = target_dir / target_name

            # Déplacer le fichier
            shutil.move(str(file_path), str(target_path))

            status = "processed" if success else "error"
            logger.info(f"Fichier {status} déplacé: {file_path} → {target_path}")

            return target_path

        except Exception as e:
            logger.error(f"Erreur déplacement fichier {file_path}: {e}")
            return None

    def save_extracted_text(
        self,
        file_path: Path,
        extracted_text: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[Path]:
        """Sauvegarde le texte extrait dans un fichier JSON.

        Parameters
        ----------
        file_path : Path
            Chemin du fichier source.
        extracted_text : str
            Texte extrait du document.
        metadata : Optional[dict[str, Any]]
            Métadonnées additionnelles (méthode, confidence, etc.).

        Returns:
        -------
        Optional[Path]
            Chemin du fichier JSON créé, None si désactivé ou erreur.
        """
        output_config = self.config.get("output", {})

        if not output_config.get("save_extracted_text", False):
            return None

        try:
            # Répertoire de destination
            extracted_dir = Path(output_config.get("extracted_dir", ""))

            if not extracted_dir:
                return None

            # Créer le répertoire s'il n'existe pas
            extracted_dir.mkdir(parents=True, exist_ok=True)

            # Construire le nom du fichier JSON
            json_name = file_path.stem

            # Ajouter timestamp si demandé
            if output_config.get("add_timestamp", False):
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                json_name = f"{json_name}_{timestamp}"

            json_path = extracted_dir / f"{json_name}.json"

            # Construire le document JSON
            document = {
                "source_file": str(file_path),
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
                "extracted_text": extracted_text,
            }

            # Ajouter métadonnées si demandé
            if output_config.get("include_metadata", True) and metadata:
                document["metadata"] = metadata  # type: ignore[assignment]

            # Sauvegarder avec pretty print si demandé
            indent = 2 if output_config.get("pretty_print", True) else None

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(document, f, ensure_ascii=False, indent=indent)

            logger.info(f"Texte extrait sauvegardé: {json_path}")

            return json_path

        except Exception as e:
            logger.error(f"Erreur sauvegarde texte extrait {file_path}: {e}")
            return None
