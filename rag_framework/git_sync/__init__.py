"""Package de synchronisation Git automatique.

Ce package contient les modules nécessaires pour la surveillance et la
synchronisation automatique des fichiers vers GitHub.

Modules:
    watcher: Point d'entrée CLI pour lancer la surveillance
    sync_manager: GitSyncManager pour opérations Git
"""

from rag_framework.git_sync.sync_manager import GitSyncError, GitSyncManager

__all__ = ["GitSyncManager", "GitSyncError"]
