"""Module de synchronisation Git automatique pour le framework RAG.

Ce module fournit la classe GitSyncManager qui gère les opérations Git
(add, commit, push) de manière automatisée avec retry logic et logging structuré.

SÉCURITÉ:
    Le token GitHub est lu depuis la variable d'environnement GITHUB_TOKEN
    (définie dans .env). Ne JAMAIS commiter le token en clair.

Exemple:
    >>> from rag_framework.git_sync import GitSyncManager
    >>> config = {"repository": {"branch": "main", "remote": "origin"}}
    >>> manager = GitSyncManager("/path/to/repo", config)
    >>> manager.sync_changes(["file1.py", "file2.yaml"])

Auteur: RAG Framework Team
Version: 1.0.0
"""

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import git
from git import GitCommandError, InvalidGitRepositoryError, Repo

from rag_framework.exceptions import RAGFrameworkError
from rag_framework.utils.logger import get_logger
from rag_framework.utils.secrets import get_secret


class GitSyncError(RAGFrameworkError):
    """Exception levée lors d'erreurs de synchronisation Git."""

    pass


class GitSyncManager:
    """Gestionnaire de synchronisation Git automatique.

    Cette classe gère les opérations Git (add, commit, push) avec retry logic,
    gestion d'erreurs robuste et logging structuré.

    Attributes:
        repo_path: Chemin absolu vers le repository Git.
        config: Configuration de git_sync depuis global.yaml.
        repo: Instance GitPython Repo.
        logger: Logger structuré pour traçabilité.
    """

    def __init__(self, repo_path: str, config: dict[str, Any]) -> None:
        """Initialise le GitSyncManager.

        Args:
            repo_path: Chemin absolu vers le repository Git.
            config: Configuration git_sync depuis global.yaml.

        Raises:
            GitSyncError: Si le chemin n'est pas un repository Git valide.
        """
        self.repo_path = Path(repo_path).resolve()
        self.config = config
        self.logger = get_logger(__name__)

        # Validation du repository Git
        try:
            self.repo = Repo(self.repo_path)
            if self.repo.bare:
                raise GitSyncError(f"Repository Git bare non supporté : {repo_path}")
        except InvalidGitRepositoryError as e:
            raise GitSyncError(
                f"Chemin invalide (pas un repository Git) : {repo_path}"
            ) from e

        # Configuration du remote et de la branche
        self.remote_name = config["repository"]["remote"]
        self.branch_name = config["repository"]["branch"]

        # Vérification du remote
        try:
            self.remote = self.repo.remote(self.remote_name)
        except ValueError as e:
            raise GitSyncError(
                f"Remote '{self.remote_name}' introuvable. Vérifiez git remote -v"
            ) from e

        # Configuration de l'authentification GitHub
        self._configure_auth()

        self.logger.info(
            "GitSyncManager initialisé",
            extra={
                "repo_path": str(self.repo_path),
                "branch": self.branch_name,
                "remote": self.remote_name,
            },
        )

    def _configure_auth(self) -> None:
        """Configure l'authentification GitHub via token HTTPS.

        Le token est lu depuis la variable d'environnement GITHUB_TOKEN.
        Si absent, on suppose que l'authentification SSH est configurée.
        """
        github_token = get_secret("GITHUB_TOKEN")
        if github_token and github_token != "GITHUB_TOKEN_NOT_SET":
            # Configuration HTTPS avec token dans l'URL
            # Format: https://<token>@github.com/user/repo.git
            try:
                remote_url = next(iter(self.remote.urls))
                if remote_url.startswith("https://github.com"):
                    # Injection du token dans l'URL
                    authenticated_url = remote_url.replace(
                        "https://github.com", f"https://{github_token}@github.com"
                    )
                    self.remote.set_url(authenticated_url)
                    self.logger.info("Authentification GitHub configurée (HTTPS token)")
                elif remote_url.startswith("git@github.com"):
                    self.logger.info(
                        "Authentification SSH détectée (token GitHub ignoré)"
                    )
                else:
                    self.logger.warning(
                        f"URL remote non reconnue : {remote_url}. "
                        "Authentification non configurée automatiquement."
                    )
            except Exception as e:
                self.logger.warning(
                    f"Impossible de configurer l'authentification : {e}"
                )
        else:
            self.logger.info(
                "Aucun GITHUB_TOKEN trouvé. "
                "Utilisation de l'authentification git configurée."
            )

    def sync_changes(self, modified_files: list[str]) -> bool:
        """Synchronise les changements (add, commit, push).

        Args:
            modified_files: Liste des chemins de fichiers modifiés
                (relatifs à repo_path).

        Returns:
            True si la synchronisation a réussi, False sinon.

        Raises:
            GitSyncError: Si une erreur critique survient après tous les retries.
        """
        if not modified_files:
            self.logger.warning("Aucun fichier à synchroniser")
            return False

        # Configuration retry
        max_retries = self.config["error_handling"]["max_retries"]
        retry_delay = self.config["error_handling"]["retry_delay_seconds"]
        continue_on_error = self.config["error_handling"]["continue_on_error"]

        for attempt in range(1, max_retries + 1):
            try:
                # 1. Git add
                self._git_add(modified_files)

                # 2. Git commit
                commit_sha = self._git_commit(modified_files)
                if not commit_sha:
                    self.logger.info("Aucun changement à commiter")
                    return True

                # 3. Git push
                self._git_push()

                self.logger.info(
                    f"Synchronisation réussie (commit {commit_sha[:7]})",
                    extra={
                        "commit_sha": commit_sha,
                        "file_count": len(modified_files),
                        "attempt": attempt,
                    },
                )
                return True

            except GitCommandError as e:
                self.logger.error(
                    f"Erreur Git (tentative {attempt}/{max_retries}) : {e.stderr}",
                    extra={
                        "attempt": attempt,
                        "max_retries": max_retries,
                        "error": str(e),
                    },
                )
                if attempt < max_retries:
                    self.logger.info(f"Nouvelle tentative dans {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    if continue_on_error:
                        self.logger.error(
                            "Synchronisation échouée après toutes les tentatives "
                            "(continue_on_error=True)"
                        )
                        return False
                    else:
                        raise GitSyncError(
                            f"Échec synchronisation après {max_retries} tentatives"
                        ) from e

            except Exception as e:
                self.logger.error(f"Erreur inattendue lors de la synchronisation : {e}")
                if continue_on_error:
                    return False
                else:
                    raise GitSyncError(f"Erreur synchronisation : {e}") from e

        return False

    def _git_add(self, files: list[str]) -> None:
        """Ajoute les fichiers à l'index Git (git add).

        Args:
            files: Liste des chemins de fichiers (relatifs à repo_path).

        Raises:
            GitCommandError: Si git add échoue.
        """
        self.logger.debug(f"Git add : {len(files)} fichier(s)")
        self.repo.index.add(files)

    def _git_commit(self, files: list[str]) -> Optional[str]:
        """Crée un commit Git (git commit).

        Args:
            files: Liste des fichiers modifiés (pour le message de commit).

        Returns:
            SHA du commit créé, ou None si rien à commiter.

        Raises:
            GitCommandError: Si git commit échoue.
        """
        # Vérifier s'il y a des changements à commiter
        if not self.repo.index.diff("HEAD") and not self.repo.untracked_files:
            return None

        # Génération du message de commit
        commit_message = self._generate_commit_message(files)

        # Configuration de l'auteur
        author_name = self.config["commit"]["author_name"]
        author_email = self.config["commit"]["author_email"]
        author = git.Actor(author_name, author_email)

        # Commit
        commit = self.repo.index.commit(commit_message, author=author, committer=author)
        self.logger.debug(f"Commit créé : {commit.hexsha[:7]}")
        return commit.hexsha

    def _git_push(self) -> None:
        """Pousse les commits vers le remote (git push).

        Raises:
            GitCommandError: Si git push échoue.
        """
        self.logger.debug(f"Git push vers {self.remote_name}/{self.branch_name}")

        # Push avec --set-upstream si la branche n'existe pas encore sur le remote
        push_info = self.remote.push(
            refspec=f"{self.branch_name}:{self.branch_name}", set_upstream=True
        )

        # Vérification du résultat
        for info in push_info:
            if info.flags & info.ERROR:
                raise GitCommandError(
                    f"git push a échoué : {info.summary}", status=1, stderr=info.summary
                )

        self.logger.debug("Git push réussi")

    def _generate_commit_message(self, files: list[str]) -> str:
        """Génère un message de commit à partir du template.

        Args:
            files: Liste des fichiers modifiés.

        Returns:
            Message de commit formaté.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        file_count = len(files)

        # Message de base depuis le template
        message_template = str(self.config["commit"]["message_template"])
        message = message_template.replace("${timestamp}", timestamp)
        message = message.replace("${file_count}", str(file_count))
        message = message.replace("${operation}", "modifié")

        # Ajout de la liste des fichiers si configuré
        if self.config["commit"]["include_file_list"]:
            max_files = self.config["commit"]["max_files_in_message"]
            files_to_list = files[:max_files]

            message += "\n\nFichiers modifiés :"
            for file in files_to_list:
                message += f"\n  - {file}"

            if len(files) > max_files:
                remaining = len(files) - max_files
                message += f"\n  ... et {remaining} autre(s) fichier(s)"

        return message

    def create_gitkeep_files(self) -> None:
        """Crée des fichiers .gitkeep dans data/input et data/output.

        Cela permet de préserver l'arborescence sans commiter le contenu.
        """
        if not self.config["repository"]["auto_create_gitkeep"]:
            return

        gitkeep_dirs = ["data/input", "data/output"]
        for dir_path in gitkeep_dirs:
            full_path = self.repo_path / dir_path
            gitkeep_file = full_path / ".gitkeep"

            # Créer le répertoire s'il n'existe pas
            full_path.mkdir(parents=True, exist_ok=True)

            # Créer le fichier .gitkeep s'il n'existe pas
            if not gitkeep_file.exists():
                gitkeep_file.touch()
                self.logger.info(f"Fichier .gitkeep créé : {gitkeep_file}")

    def get_repo_status(self) -> dict[str, Any]:
        """Récupère le statut du repository Git.

        Returns:
            Dictionnaire avec les informations de statut :
                - branch: Branche actuelle
                - is_dirty: True si des changements non commités existent
                - untracked_files: Liste des fichiers non trackés
                - modified_files: Liste des fichiers modifiés
        """
        return {
            "branch": str(self.repo.active_branch.name),
            "is_dirty": self.repo.is_dirty(),
            "untracked_files": self.repo.untracked_files,
            "modified_files": [item.a_path for item in self.repo.index.diff(None)],
        }
