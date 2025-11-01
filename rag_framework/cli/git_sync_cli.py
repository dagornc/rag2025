#!/usr/bin/env python3
"""CLI pour la synchronisation Git automatique du framework RAG.

Ce script lance la surveillance des fichiers via watchdog et déclenche
la synchronisation Git automatique selon la configuration définie dans
config/global.yaml.

Usage:
    python -m rag_framework.cli.git_sync_cli
    # ou avec rye :
    rye run python -m rag_framework.cli.git_sync_cli

Arrêt:
    CTRL+C pour arrêter proprement (synchronisation forcée des fichiers en attente)

Auteur: RAG Framework Team
Version: 1.0.0
"""

import signal
import sys
import time
from pathlib import Path
from types import FrameType
from typing import Any, Optional, cast

import yaml
from watchdog.observers import Observer

from rag_framework.git_sync import GitSyncManager
from rag_framework.git_sync_handler import GitSyncEventHandler
from rag_framework.utils.logger import get_logger


def load_config(config_path: Path) -> dict[str, Any]:
    """Charge la configuration depuis global.yaml.

    Args:
        config_path: Chemin vers le fichier global.yaml.

    Returns:
        Configuration complète de global.yaml.

    Raises:
        FileNotFoundError: Si le fichier de configuration n'existe pas.
        yaml.YAMLError: Si le fichier YAML est invalide.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Fichier de configuration introuvable : {config_path}")

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return cast(dict[str, Any], config)


def main() -> int:
    """Point d'entrée principal du CLI git_sync.

    Returns:
        Code de sortie (0 = succès, 1 = erreur).
    """
    logger = get_logger(__name__)
    logger.info("🚀 Démarrage de Git Auto-Sync pour le framework RAG")

    # Déterminer le chemin du projet (racine du repository)
    project_root = Path(__file__).resolve().parent.parent.parent
    config_file = project_root / "config" / "global.yaml"

    # Charger la configuration
    try:
        config = load_config(config_file)
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la configuration : {e}")
        return 1

    # Vérifier que git_sync est activé
    git_sync_config = config.get("git_sync", {})
    if not git_sync_config.get("enabled", False):
        logger.warning(
            "Git Auto-Sync est désactivé dans config/global.yaml "
            "(git_sync.enabled=false)"
        )
        return 0

    # Initialiser le GitSyncManager
    try:
        git_manager = GitSyncManager(str(project_root), git_sync_config)
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de GitSyncManager : {e}")
        return 1

    # Créer les fichiers .gitkeep si configuré
    try:
        git_manager.create_gitkeep_files()
    except Exception as e:
        logger.warning(f"Impossible de créer les fichiers .gitkeep : {e}")

    # Initialiser le handler watchdog
    event_handler = GitSyncEventHandler(git_manager, git_sync_config)

    # Configurer l'observer watchdog
    observer = Observer()
    watch_paths = git_sync_config.get("watch_paths", ["."])

    for watch_path in watch_paths:
        full_watch_path = project_root / watch_path
        observer.schedule(event_handler, str(full_watch_path), recursive=True)
        logger.info(f"👁️  Surveillance activée : {full_watch_path}")

    # Gérer CTRL+C proprement
    def signal_handler(signum: int, frame: Optional[FrameType]) -> None:
        """Gère l'arrêt gracieux avec CTRL+C."""
        logger.info("\n⚠️  Signal d'arrêt reçu (CTRL+C)")
        logger.info("🔄 Synchronisation forcée des fichiers en attente...")

        # Forcer la synchronisation des fichiers en attente
        event_handler.force_sync()

        # Arrêter l'observer
        observer.stop()
        observer.join()

        logger.info("✅ Git Auto-Sync arrêté proprement")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Démarrer l'observer
    observer.start()
    logger.info("✅ Git Auto-Sync démarré avec succès")
    logger.info(
        f"⏱️  Mode : {git_sync_config['frequency']['type']}, "
        f"Debounce : {git_sync_config['frequency']['debounce_seconds']}s"
    )
    logger.info("💡 Appuyez sur CTRL+C pour arrêter proprement")

    # Afficher le statut du repository
    try:
        status = git_manager.get_repo_status()
        logger.info(
            f"📊 Statut du repository : Branche={status['branch']}, "
            f"Dirty={status['is_dirty']}, "
            f"Untracked={len(status['untracked_files'])}"
        )
    except Exception as e:
        logger.warning(f"Impossible de récupérer le statut du repository : {e}")

    # Boucle infinie (watchdog surveille en arrière-plan)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Normalement géré par signal_handler, mais au cas où
        observer.stop()

    observer.join()
    return 0


if __name__ == "__main__":
    sys.exit(main())
