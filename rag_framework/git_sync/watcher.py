"""Point d'entrée CLI pour la synchronisation Git automatique.

Ce module lance la surveillance watchdog et synchronise automatiquement
les modifications vers GitHub selon la configuration.

Usage:
    python -m rag_framework.git_sync.watcher \
        --config config/synchrogithub.yaml \
        --log-file logs/git_sync.log

Auteur: RAG Framework Team
Version: 1.0.0
"""

import argparse
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any

import yaml
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

# Import du GitSyncManager depuis le module parent
# Note: GitSyncManager est défini dans rag_framework/git_sync.py (module)
# pas dans rag_framework/git_sync/ (package git_sync/)
from rag_framework import git_sync as git_sync_module

GitSyncManager = git_sync_module.GitSyncManager


def load_config(config_path: str) -> dict[str, Any]:
    """Charge la configuration depuis synchrogithub.yaml.

    Args:
        config_path: Chemin vers le fichier de configuration.

    Returns:
        Configuration chargée.

    Raises:
        FileNotFoundError: Si le fichier n'existe pas.
        yaml.YAMLError: Si le fichier n'est pas un YAML valide.
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Fichier de configuration introuvable: {config_path}")

    with open(config_file, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


def setup_logging(log_file: str, config: dict[str, Any]) -> logging.Logger:
    """Configure le logging pour git_sync.

    Args:
        log_file: Chemin vers le fichier de log.
        config: Configuration git_sync.

    Returns:
        Logger configuré.
    """
    # Créer le répertoire de logs si nécessaire
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configuration du logger
    log_level = config["git_sync"]["logging"]["level"]
    structured = config["git_sync"]["logging"]["structured"]

    logger = logging.getLogger("git_sync")
    logger.setLevel(log_level)

    # Handler fichier
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(log_level)

    # Handler console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Format
    if structured:
        log_format = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(message)s - %(pathname)s:%(lineno)d"
        )
    else:
        log_format = "%(asctime)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


class GitSyncHandler(FileSystemEventHandler):
    """Handler watchdog pour détecter les modifications de fichiers.

    Attributes:
        config: Configuration git_sync.
        sync_manager: Instance de GitSyncManager.
        pending_changes: Ensemble des fichiers modifiés en attente.
        last_change_time: Timestamp de la dernière modification.
        logger: Logger pour traçabilité.
    """

    def __init__(
        self,
        config: dict[str, Any],
        sync_manager: GitSyncManager,
        logger: logging.Logger,
    ) -> None:
        """Initialise le handler.

        Args:
            config: Configuration git_sync.
            sync_manager: Instance de GitSyncManager.
            logger: Logger configuré.
        """
        super().__init__()
        self.config = config["git_sync"]
        self.sync_manager = sync_manager
        self.logger = logger
        self.pending_changes: set[str] = set()
        self.last_change_time: float | None = None

        # Compilation des patterns regex
        self.exclude_patterns = [
            re.compile(pattern) for pattern in self.config["exclude_patterns"]
        ]
        self.include_patterns = [
            re.compile(pattern) for pattern in self.config["include_patterns"]
        ]

    def on_modified(self, event: FileSystemEvent) -> None:
        """Appelé quand un fichier est modifié."""
        if not event.is_directory and self._should_sync(event.src_path):
            self._add_change(event.src_path)

    def on_created(self, event: FileSystemEvent) -> None:
        """Appelé quand un fichier est créé."""
        if not event.is_directory and self._should_sync(event.src_path):
            self._add_change(event.src_path)

    def _should_sync(self, file_path: str) -> bool:
        """Vérifie si un fichier doit déclencher une synchronisation.

        Args:
            file_path: Chemin absolu du fichier.

        Returns:
            True si le fichier doit être synchronisé.
        """
        # Convertir en chemin relatif depuis la racine du projet
        try:
            rel_path = Path(file_path).relative_to(Path.cwd())
            rel_path_str = str(rel_path)
        except ValueError:
            # Fichier en dehors du projet
            return False

        # Vérifier les patterns d'exclusion
        for pattern in self.exclude_patterns:
            if pattern.match(rel_path_str):
                self.logger.debug(f"Fichier exclu: {rel_path_str}")
                return False

        # Vérifier les patterns d'inclusion
        for pattern in self.include_patterns:
            if pattern.match(rel_path_str):
                self.logger.debug(f"Fichier inclus: {rel_path_str}")
                return True

        # Par défaut, ne pas synchroniser
        self.logger.debug(f"Fichier ignoré (pas de pattern match): {rel_path_str}")
        return False

    def _add_change(self, file_path: str) -> None:
        """Ajoute un fichier à la liste des changements en attente.

        Args:
            file_path: Chemin absolu du fichier.
        """
        rel_path = str(Path(file_path).relative_to(Path.cwd()))
        self.pending_changes.add(rel_path)
        self.last_change_time = time.time()
        self.logger.info(f"Changement détecté: {rel_path}")

    def has_changes(self) -> bool:
        """Vérifie si des changements sont en attente."""
        return len(self.pending_changes) > 0

    def check_debounce(self) -> bool:
        """Vérifie si le délai de debounce est écoulé.

        Returns:
            True si le debounce est écoulé et qu'il y a des changements.
        """
        if not self.last_change_time or not self.pending_changes:
            return False

        debounce_seconds = self.config["frequency"]["debounce_seconds"]
        elapsed = time.time() - self.last_change_time
        return elapsed >= debounce_seconds

    def clear_changes(self) -> None:
        """Vide la liste des changements en attente."""
        self.pending_changes.clear()
        self.last_change_time = None

    def get_changes(self) -> list[str]:
        """Récupère la liste des changements en attente."""
        return list(self.pending_changes)


def main() -> int:
    """Point d'entrée principal du watcher.

    Returns:
        Code de retour (0 = succès, 1 = erreur).
    """
    # Parse des arguments
    parser = argparse.ArgumentParser(
        description="Synchronisation Git automatique pour RAG Framework"
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Chemin vers synchrogithub.yaml",
    )
    parser.add_argument(
        "--log-file",
        required=True,
        help="Chemin vers le fichier de log",
    )
    args = parser.parse_args()

    try:
        # Charger configuration
        config = load_config(args.config)
        logger = setup_logging(args.log_file, config)

        logger.info("=" * 70)
        logger.info("Démarrage de la synchronisation Git automatique")
        logger.info("=" * 70)
        logger.info(f"Configuration: {args.config}")
        logger.info(f"Mode: {config['git_sync']['mode']}")
        logger.info(f"Type: {config['git_sync']['frequency']['type']}")
        logger.info("=" * 70)

        # Créer le gestionnaire de synchronisation
        repo_path = Path.cwd()
        sync_manager = GitSyncManager(str(repo_path), config["git_sync"])

        # Créer les fichiers .gitkeep si configuré
        sync_manager.create_gitkeep_files()

        # Créer le handler watchdog
        handler = GitSyncHandler(config, sync_manager, logger)

        # Configurer l'observer
        observer = Observer()
        watch_path = config["git_sync"]["watch_paths"][0]
        observer.schedule(handler, path=watch_path, recursive=True)
        observer.start()

        logger.info(f"Surveillance active sur: {Path(watch_path).resolve()}")

        # Boucle principale selon le type de synchronisation
        sync_type = config["git_sync"]["frequency"]["type"]

        if sync_type == "periodic":
            interval_minutes = config["git_sync"]["frequency"][
                "periodic_interval_minutes"
            ]
            logger.info(f"Mode periodic: commit toutes les {interval_minutes} minutes")

            try:
                while True:
                    time.sleep(interval_minutes * 60)
                    if handler.has_changes():
                        changes = handler.get_changes()
                        logger.info(
                            f"Synchronisation périodique ({len(changes)} fichiers)"
                        )
                        sync_manager.sync_changes(changes)
                        handler.clear_changes()
                    else:
                        logger.debug("Aucun changement à synchroniser")

            except KeyboardInterrupt:
                logger.info("Interruption reçue (Ctrl+C)")

        elif sync_type == "debounce":
            debounce_seconds = config["git_sync"]["frequency"]["debounce_seconds"]
            logger.info(f"Mode debounce: commit après {debounce_seconds}s d'inactivité")

            try:
                while True:
                    time.sleep(1)
                    if handler.check_debounce():
                        changes = handler.get_changes()
                        logger.info(
                            f"Debounce écoulé, synchronisation "
                            f"({len(changes)} fichiers)"
                        )
                        sync_manager.sync_changes(changes)
                        handler.clear_changes()

            except KeyboardInterrupt:
                logger.info("Interruption reçue (Ctrl+C)")

        elif sync_type == "immediate":
            logger.info("Mode immediate: commit à chaque modification")
            logger.warning("Mode immediate non recommandé (génère beaucoup de commits)")

            try:
                last_sync = 0.0
                min_delay = 5.0  # Délai minimum entre 2 commits (secondes)

                while True:
                    time.sleep(1)
                    if handler.has_changes():
                        elapsed = time.time() - last_sync
                        if elapsed >= min_delay:
                            changes = handler.get_changes()
                            logger.info(
                                f"Synchronisation immédiate ({len(changes)} fichiers)"
                            )
                            sync_manager.sync_changes(changes)
                            handler.clear_changes()
                            last_sync = time.time()

            except KeyboardInterrupt:
                logger.info("Interruption reçue (Ctrl+C)")

        else:
            logger.error(f"Type de synchronisation inconnu: {sync_type}")
            return 1

        # Arrêt propre
        observer.stop()
        observer.join()
        logger.info("Synchronisation arrêtée proprement")
        return 0

    except FileNotFoundError as e:
        print(f"Erreur: {e}", file=sys.stderr)
        return 1
    except yaml.YAMLError as e:
        print(f"Erreur de parsing YAML: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Erreur inattendue: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
