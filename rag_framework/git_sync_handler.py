"""Handler Watchdog pour la synchronisation Git automatique.

Ce module fournit GitSyncEventHandler qui surveille les modifications de fichiers
et déclenche la synchronisation Git avec un système de debounce intelligent.

Le debounce permet de regrouper les modifications successives et d'éviter
de créer un commit à chaque modification de fichier individuelle.

Exemple:
    >>> from rag_framework.git_sync_handler import GitSyncEventHandler
    >>> from rag_framework.git_sync import GitSyncManager
    >>> manager = GitSyncManager("/path/to/repo", config)
    >>> handler = GitSyncEventHandler(manager, config)
    >>> # Utilisé automatiquement par watchdog.observers.Observer

Auteur: RAG Framework Team
Version: 1.0.0
"""

import threading
from pathlib import Path
from typing import Any, Union

from watchdog.events import (
    FileSystemEvent,
    RegexMatchingEventHandler,
)

from rag_framework.git_sync import GitSyncManager
from rag_framework.utils.logger import get_logger


class GitSyncEventHandler(RegexMatchingEventHandler):
    """Handler pour les événements de fichiers avec debounce intelligent.

    Cette classe hérite de RegexMatchingEventHandler pour filtrer les événements
    selon des patterns d'inclusion/exclusion, et implémente un debounce pour
    regrouper les modifications successives.

    Attributes:
        git_manager: Instance de GitSyncManager pour effectuer les sync.
        config: Configuration git_sync depuis global.yaml.
        logger: Logger structuré.
        pending_files: Set des fichiers en attente de synchronisation.
        debounce_timer: Timer de debounce actif (ou None).
        lock: Lock pour protéger l'accès concurrent à pending_files.
    """

    def __init__(self, git_manager: GitSyncManager, config: dict[str, Any]) -> None:
        """Initialise le GitSyncEventHandler.

        Args:
            git_manager: Instance de GitSyncManager configurée.
            config: Configuration git_sync depuis global.yaml.
        """
        # Configuration des patterns pour RegexMatchingEventHandler
        regexes = config["include_patterns"]
        ignore_regexes = config["exclude_patterns"]
        ignore_directories = True  # Ignorer les événements de répertoires
        case_sensitive = True

        super().__init__(
            regexes=regexes,
            ignore_regexes=ignore_regexes,
            ignore_directories=ignore_directories,
            case_sensitive=case_sensitive,
        )

        self.git_manager = git_manager
        self.config = config
        self.logger = get_logger(__name__)

        # État interne
        self.pending_files: set[str] = set()
        self.debounce_timer: Union[threading.Timer, None] = None
        self.lock = threading.Lock()

        # Configuration du debounce
        self.debounce_seconds = config["frequency"]["debounce_seconds"]
        self.frequency_type = config["frequency"]["type"]

        self.logger.info(
            "GitSyncEventHandler initialisé",
            extra={
                "frequency_type": self.frequency_type,
                "debounce_seconds": self.debounce_seconds,
                "include_patterns_count": len(regexes),
                "exclude_patterns_count": len(ignore_regexes),
            },
        )

    def on_created(self, event: FileSystemEvent) -> None:
        """Appelé quand un fichier est créé.

        Args:
            event: Événement watchdog contenant le chemin du fichier.
        """
        if not event.is_directory:
            src = str(event.src_path)
            self.logger.debug(f"Fichier créé : {src}")
            self._handle_file_change(src)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Appelé quand un fichier est modifié.

        Args:
            event: Événement watchdog contenant le chemin du fichier.
        """
        if not event.is_directory:
            src = str(event.src_path)
            self.logger.debug(f"Fichier modifié : {src}")
            self._handle_file_change(src)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Appelé quand un fichier est supprimé.

        Args:
            event: Événement watchdog contenant le chemin du fichier.
        """
        if not event.is_directory:
            src = str(event.src_path)
            self.logger.debug(f"Fichier supprimé : {src}")
            self._handle_file_change(src)

    def on_moved(self, event: FileSystemEvent) -> None:
        """Appelé quand un fichier est déplacé/renommé.

        Args:
            event: Événement watchdog contenant src_path et dest_path.
        """
        if not event.is_directory:
            src = str(event.src_path)
            dest = str(event.dest_path) if hasattr(event, "dest_path") else ""
            self.logger.debug(f"Fichier déplacé : {src} -> {dest}")
            # Traiter à la fois la source (suppression) et la destination (création)
            self._handle_file_change(src)
            if dest:
                self._handle_file_change(dest)

    def _handle_file_change(self, file_path: str) -> None:
        """Gère un changement de fichier avec debounce.

        Args:
            file_path: Chemin absolu du fichier modifié.
        """
        # Convertir en chemin relatif au repository
        try:
            abs_path = Path(file_path).resolve()
            repo_path = self.git_manager.repo_path
            relative_path = abs_path.relative_to(repo_path)
            relative_path_str = str(relative_path)
        except ValueError:
            # Le fichier n'est pas dans le repository (ne devrait pas arriver)
            self.logger.warning(
                f"Fichier hors du repository ignoré : {file_path}",
                extra={"file_path": file_path, "repo_path": str(repo_path)},
            )
            return

        with self.lock:
            # Ajouter le fichier à la liste des fichiers en attente
            self.pending_files.add(relative_path_str)
            self.logger.debug(
                f"Fichier ajouté aux pending : {relative_path_str}",
                extra={"pending_count": len(self.pending_files)},
            )

            # Gérer le debounce selon le type de fréquence
            if self.frequency_type == "immediate":
                # Mode immédiat : synchroniser immédiatement
                self._trigger_sync()
            elif self.frequency_type == "debounce":
                # Mode debounce : annuler le timer précédent et en créer un nouveau
                if self.debounce_timer is not None:
                    self.debounce_timer.cancel()

                self.debounce_timer = threading.Timer(
                    self.debounce_seconds, self._trigger_sync
                )
                self.debounce_timer.daemon = True
                self.debounce_timer.start()
                self.logger.debug(
                    f"Timer de debounce démarré ({self.debounce_seconds}s)"
                )
            # Note : le mode "periodic" est géré par le CLI (pas de timer ici)

    def _trigger_sync(self) -> None:
        """Déclenche la synchronisation Git des fichiers en attente.

        Cette méthode est appelée par le timer de debounce ou en mode immediate.
        """
        with self.lock:
            if not self.pending_files:
                self.logger.debug("Aucun fichier à synchroniser (pending_files vide)")
                return

            # Copier et vider la liste des fichiers en attente
            files_to_sync = list(self.pending_files)
            self.pending_files.clear()
            self.debounce_timer = None

        self.logger.info(
            f"Déclenchement de la synchronisation Git ({len(files_to_sync)} fichiers)",
            extra={"file_count": len(files_to_sync), "files": files_to_sync},
        )

        # Synchroniser via le GitSyncManager
        try:
            success = self.git_manager.sync_changes(files_to_sync)
            if success:
                self.logger.info(
                    "Synchronisation Git terminée avec succès",
                    extra={"file_count": len(files_to_sync)},
                )
            else:
                self.logger.warning(
                    "Synchronisation Git échouée",
                    extra={"file_count": len(files_to_sync)},
                )
        except Exception as e:
            self.logger.error(
                f"Erreur lors de la synchronisation Git : {e}",
                extra={"file_count": len(files_to_sync), "error": str(e)},
            )

    def force_sync(self) -> None:
        """Force la synchronisation immédiate des fichiers en attente.

        Utile pour forcer un sync avant l'arrêt du programme (CTRL+C).
        """
        self.logger.info("Synchronisation forcée demandée")

        # Annuler le timer de debounce s'il existe
        with self.lock:
            if self.debounce_timer is not None:
                self.debounce_timer.cancel()
                self.debounce_timer = None

        # Déclencher la synchronisation
        self._trigger_sync()

    def get_pending_files_count(self) -> int:
        """Récupère le nombre de fichiers en attente de synchronisation.

        Returns:
            Nombre de fichiers dans pending_files.
        """
        with self.lock:
            return len(self.pending_files)
