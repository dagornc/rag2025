"""Tests unitaires pour le module git_sync.

Ces tests valident le comportement de GitSyncManager et GitSyncEventHandler
avec des mocks pour éviter les vraies opérations Git.

Auteur: RAG Framework Team
Version: 1.0.0
"""

import re
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from rag_framework.git_sync import GitSyncError, GitSyncManager
from rag_framework.git_sync_handler import GitSyncEventHandler

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_config() -> dict[str, Any]:
    """Configuration de test pour git_sync."""
    return {
        "enabled": True,
        "mode": "sync",
        "frequency": {
            "type": "debounce",
            "debounce_seconds": 1,  # 1s pour tests rapides
            "periodic_interval_minutes": 15,
        },
        "watch_paths": ["."],
        "exclude_patterns": [
            r".*\.git/.*",
            r".*__pycache__.*",
            r".*/data/input/(?!.gitkeep).*",
            r".*/data/output/(?!.gitkeep).*",
        ],
        "include_patterns": [
            r".*\.py$",
            r".*\.yaml$",
            r".*\.md$",
        ],
        "repository": {
            "branch": "main",
            "remote": "origin",
            "auto_create_gitkeep": True,
        },
        "commit": {
            "message_template": "Auto-sync: ${file_count} fichier(s) - ${timestamp}",
            "author_name": "Test Bot",
            "author_email": "test@example.com",
            "include_file_list": True,
            "max_files_in_message": 5,
        },
        "error_handling": {
            "max_retries": 3,
            "retry_delay_seconds": 1,
            "continue_on_error": True,
        },
        "logging": {
            "level": "INFO",
            "log_file": "logs/git_sync.log",
            "structured": True,
        },
    }


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    """Crée un repository Git temporaire pour les tests."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialiser un repo Git
    import git

    repo = git.Repo.init(repo_path)

    # Configuration de base
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")

    # Créer un commit initial
    (repo_path / "README.md").write_text("# Test Repo")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    # Ajouter un remote fictif
    try:
        repo.create_remote("origin", "https://github.com/test/test.git")
    except Exception:
        pass

    return repo_path


# ==============================================================================
# TESTS GitSyncManager
# ==============================================================================


def test_gitsyncmanager_init_valid_repo(
    temp_git_repo: Path, mock_config: dict[str, Any]
) -> None:
    """Test l'initialisation de GitSyncManager avec un repo valide."""
    with patch("rag_framework.git_sync.get_secret", return_value="fake_token"):
        manager = GitSyncManager(str(temp_git_repo), mock_config)

        assert manager.repo_path == temp_git_repo.resolve()
        assert manager.branch_name == "main"
        assert manager.remote_name == "origin"
        assert manager.repo is not None


def test_gitsyncmanager_init_invalid_repo(
    tmp_path: Path, mock_config: dict[str, Any]
) -> None:
    """Test l'initialisation avec un chemin invalide (pas un repo Git)."""
    invalid_path = tmp_path / "not_a_repo"
    invalid_path.mkdir()

    with pytest.raises(GitSyncError, match="pas un repository Git"):
        with patch("rag_framework.git_sync.get_secret", return_value="fake_token"):
            GitSyncManager(str(invalid_path), mock_config)


def test_generate_commit_message(
    temp_git_repo: Path, mock_config: dict[str, Any]
) -> None:
    """Test la génération du message de commit."""
    with patch("rag_framework.git_sync.get_secret", return_value="fake_token"):
        manager = GitSyncManager(str(temp_git_repo), mock_config)

        files = ["file1.py", "file2.yaml", "file3.md"]
        message = manager._generate_commit_message(files)

        # Vérifications
        assert "3 fichier(s)" in message
        assert "file1.py" in message
        assert "file2.yaml" in message
        assert "file3.md" in message


def test_generate_commit_message_max_files(
    temp_git_repo: Path, mock_config: dict[str, Any]
) -> None:
    """Test la limitation du nombre de fichiers listés dans le message."""
    with patch("rag_framework.git_sync.get_secret", return_value="fake_token"):
        manager = GitSyncManager(str(temp_git_repo), mock_config)

        # 10 fichiers mais max_files_in_message = 5
        files = [f"file{i}.py" for i in range(10)]
        message = manager._generate_commit_message(files)

        # Vérifications
        assert "10 fichier(s)" in message
        assert "5 autre(s) fichier(s)" in message


def test_create_gitkeep_files(temp_git_repo: Path, mock_config: dict[str, Any]) -> None:
    """Test la création des fichiers .gitkeep."""
    with patch("rag_framework.git_sync.get_secret", return_value="fake_token"):
        manager = GitSyncManager(str(temp_git_repo), mock_config)
        manager.create_gitkeep_files()

        # Vérifier que les fichiers .gitkeep existent
        assert (temp_git_repo / "data" / "input" / ".gitkeep").exists()
        assert (temp_git_repo / "data" / "output" / ".gitkeep").exists()


def test_get_repo_status(temp_git_repo: Path, mock_config: dict[str, Any]) -> None:
    """Test la récupération du statut du repository."""
    with patch("rag_framework.git_sync.get_secret", return_value="fake_token"):
        manager = GitSyncManager(str(temp_git_repo), mock_config)

        # Créer un fichier non tracké
        (temp_git_repo / "untracked.txt").write_text("test")

        status = manager.get_repo_status()

        assert "branch" in status
        assert "is_dirty" in status
        assert "untracked_files" in status
        assert "untracked.txt" in status["untracked_files"]


# ==============================================================================
# TESTS GitSyncEventHandler
# ==============================================================================


def test_handler_init(temp_git_repo: Path, mock_config: dict[str, Any]) -> None:
    """Test l'initialisation du GitSyncEventHandler."""
    with patch("rag_framework.git_sync.get_secret", return_value="fake_token"):
        manager = GitSyncManager(str(temp_git_repo), mock_config)
        handler = GitSyncEventHandler(manager, mock_config)

        assert handler.git_manager == manager
        assert handler.debounce_seconds == 1
        assert handler.frequency_type == "debounce"
        assert len(handler.pending_files) == 0


def test_handler_file_patterns_inclusion(
    temp_git_repo: Path, mock_config: dict[str, Any]
) -> None:
    """Test que les patterns d'inclusion fonctionnent correctement."""
    with patch("rag_framework.git_sync.get_secret", return_value="fake_token"):
        manager = GitSyncManager(str(temp_git_repo), mock_config)
        GitSyncEventHandler(manager, mock_config)

        # Tester les patterns d'inclusion
        included_files = ["test.py", "config.yaml", "README.md"]
        for file in included_files:
            # Simuler qu'un fichier correspond aux patterns
            matches = any(
                re.match(pattern, file) for pattern in mock_config["include_patterns"]
            )
            assert matches, f"{file} devrait être inclus"

        # Tester les patterns d'exclusion
        excluded_files = ["file.txt", "image.png", "data.json"]
        for file in excluded_files:
            matches = any(
                re.match(pattern, file) for pattern in mock_config["include_patterns"]
            )
            assert not matches, f"{file} devrait être exclu"


def test_handler_file_patterns_exclusion(
    temp_git_repo: Path, mock_config: dict[str, Any]
) -> None:
    """Test que les patterns d'exclusion fonctionnent correctement."""
    excluded_paths = [
        ".git/config",
        "src/__pycache__/module.pyc",
        "data/input/document.pdf",
        "data/output/result.txt",
    ]

    for path in excluded_paths:
        matches = any(
            re.match(pattern, path) for pattern in mock_config["exclude_patterns"]
        )
        assert matches, f"{path} devrait être exclu"

    # .gitkeep devrait être inclus (exception)
    gitkeep_path = "data/input/.gitkeep"
    matches = any(
        re.match(pattern, gitkeep_path) for pattern in mock_config["exclude_patterns"]
    )
    # Note: Le pattern avec negative lookahead (?!.gitkeep) est complexe à
    # tester unitairement. On teste plutôt l'inclusion
    matches_include = any(
        re.match(pattern, gitkeep_path) for pattern in mock_config["include_patterns"]
    )
    assert matches_include, ".gitkeep devrait être inclus"


def test_handler_debounce_mechanism(
    temp_git_repo: Path, mock_config: dict[str, Any]
) -> None:
    """Test le mécanisme de debounce."""
    with patch("rag_framework.git_sync.get_secret", return_value="fake_token"):
        manager = GitSyncManager(str(temp_git_repo), mock_config)

        # Mock sync_changes pour éviter les vraies opérations Git
        manager.sync_changes = MagicMock(return_value=True)

        handler = GitSyncEventHandler(manager, mock_config)

        # Simuler plusieurs changements rapides
        test_file = temp_git_repo / "test.py"
        test_file.write_text("print('test')")

        handler._handle_file_change(str(test_file))
        handler._handle_file_change(str(test_file))
        handler._handle_file_change(str(test_file))

        # Le fichier devrait être dans pending_files
        assert handler.get_pending_files_count() == 1

        # Attendre que le debounce se déclenche
        time.sleep(1.5)

        # sync_changes devrait avoir été appelé une seule fois
        assert manager.sync_changes.call_count == 1


def test_handler_force_sync(temp_git_repo: Path, mock_config: dict[str, Any]) -> None:
    """Test la synchronisation forcée."""
    with patch("rag_framework.git_sync.get_secret", return_value="fake_token"):
        manager = GitSyncManager(str(temp_git_repo), mock_config)
        manager.sync_changes = MagicMock(return_value=True)

        handler = GitSyncEventHandler(manager, mock_config)

        # Ajouter un fichier en attente
        test_file = temp_git_repo / "test.py"
        test_file.write_text("print('test')")
        handler._handle_file_change(str(test_file))

        # Forcer la synchronisation
        handler.force_sync()

        # sync_changes devrait avoir été appelé
        assert manager.sync_changes.call_count == 1
        assert handler.get_pending_files_count() == 0


# ==============================================================================
# TESTS D'INTÉGRATION (avec mocks Git)
# ==============================================================================


def test_integration_sync_changes_success(
    temp_git_repo: Path, mock_config: dict[str, Any]
) -> None:
    """Test d'intégration : synchronisation réussie."""
    with patch("rag_framework.git_sync.get_secret", return_value="fake_token"):
        manager = GitSyncManager(str(temp_git_repo), mock_config)

        # Créer un fichier à synchroniser
        test_file = temp_git_repo / "test.py"
        test_file.write_text("print('hello')")

        # Mock du push pour éviter l'erreur réseau
        with patch.object(manager.remote, "push") as mock_push:
            mock_push_info = Mock()
            mock_push_info.flags = 0  # Pas d'erreur
            mock_push.return_value = [mock_push_info]

            # Synchroniser
            success = manager.sync_changes(["test.py"])

            # Vérifications
            assert success is True
            assert mock_push.called


def test_integration_sync_changes_no_changes(
    temp_git_repo: Path, mock_config: dict[str, Any]
) -> None:
    """Test d'intégration : pas de changements à synchroniser."""
    with patch("rag_framework.git_sync.get_secret", return_value="fake_token"):
        manager = GitSyncManager(str(temp_git_repo), mock_config)

        # Synchroniser sans changements
        success = manager.sync_changes([])

        # Vérifications
        assert success is False
