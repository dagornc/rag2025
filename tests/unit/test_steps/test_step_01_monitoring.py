"""Tests pour l'étape de monitoring."""

from pathlib import Path

import pytest

from rag_framework.exceptions import ValidationError
from rag_framework.steps.step_01_monitoring import MonitoringStep


class TestMonitoringStep:
    """Tests pour MonitoringStep."""

    @pytest.fixture
    def valid_config(self, test_data_dir: Path) -> dict:
        """Configuration valide pour les tests."""
        return {
            "enabled": True,
            "watch_paths": [str(test_data_dir)],
            "file_patterns": ["*.txt", "*.pdf"],
            "polling_interval_seconds": 10,
            "triggers": {
                "on_created": True,
                "on_modified": True,
            },
            "recursive": True,
        }

    def test_initialization(self, valid_config: dict) -> None:
        """Test initialisation de l'étape."""
        step = MonitoringStep(valid_config)
        assert step is not None
        assert step.enabled is True

    def test_validation_missing_key(self) -> None:
        """Test erreur si clé manquante."""
        invalid_config = {"enabled": True}
        with pytest.raises(ValidationError):
            MonitoringStep(invalid_config)

    def test_execute(
        self,
        valid_config: dict,
        create_test_file: Path,
    ) -> None:
        """Test exécution de l'étape."""
        step = MonitoringStep(valid_config)
        result = step.execute({})

        assert "monitored_files" in result
        assert isinstance(result["monitored_files"], list)
        # Au moins le fichier de test devrait être détecté
        assert len(result["monitored_files"]) >= 1
