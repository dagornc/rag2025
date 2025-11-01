"""Configuration pytest et fixtures pour les tests."""

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Retourne le répertoire des données de test."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def config_dir() -> Path:
    """Retourne le répertoire de configuration."""
    return Path(__file__).parent.parent / "config"


@pytest.fixture
def sample_text() -> str:
    """Retourne un texte d'exemple pour les tests."""
    return """
    Ceci est un document de conformité test.
    Il contient des informations confidentielles sur la politique RGPD.

    Article 1: Protection des données personnelles
    Les données doivent être traitées de manière sécurisée.

    Article 2: Droits des utilisateurs
    Les utilisateurs ont le droit d'accès à leurs données.
    """


@pytest.fixture
def sample_chunks() -> list[dict[str, Any]]:
    """Retourne des chunks d'exemple pour les tests."""
    return [
        {
            "text": "Ceci est un chunk de test sur le RGPD.",
            "source_file": "test.pdf",
            "chunk_index": 0,
        },
        {
            "text": "Ceci est un deuxième chunk confidentiel.",
            "source_file": "test.pdf",
            "chunk_index": 1,
        },
    ]


@pytest.fixture
def sample_step_data() -> dict[str, Any]:
    """Retourne des données d'étape d'exemple."""
    return {
        "monitored_files": ["tests/data/sample.txt"],
        "extracted_documents": [
            {
                "file_path": "tests/data/sample.txt",
                "text": "Contenu du document de test.",
                "original_length": 100,
                "cleaned_length": 90,
            }
        ],
    }


@pytest.fixture(scope="session")
def create_test_file(test_data_dir: Path) -> Path:
    """Crée un fichier texte de test temporaire."""
    test_data_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_data_dir / "sample.txt"

    if not test_file.exists():
        test_file.write_text(
            "Ceci est un document de test pour le framework RAG. "
            "Il contient des informations de conformité RGPD.",
            encoding="utf-8",
        )

    return test_file


@pytest.fixture
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock les variables d'environnement pour les tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
