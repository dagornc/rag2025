"""Tests pour le module de configuration."""

from pathlib import Path

import pytest

from rag_framework.config import (
    load_config,
    load_step_config,
    load_yaml_config,
    substitute_env_vars,
)
from rag_framework.exceptions import ConfigurationError


class TestSubstituteEnvVars:
    """Tests pour substitute_env_vars."""

    def test_substitute_simple_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test substitution d'une variable simple."""
        monkeypatch.setenv("TEST_VAR", "value123")
        result = substitute_env_vars("${TEST_VAR}")
        assert result == "value123"

    def test_substitute_nested_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test substitution dans un dictionnaire imbriqué."""
        monkeypatch.setenv("API_KEY", "secret")
        data = {"config": {"key": "${API_KEY}"}}
        result = substitute_env_vars(data)
        assert result["config"]["key"] == "secret"

    def test_substitute_missing_var(self) -> None:
        """Test erreur si variable manquante."""
        with pytest.raises(ConfigurationError) as exc_info:
            substitute_env_vars("${MISSING_VAR}")
        assert "Variable d'environnement non définie" in str(exc_info.value)

    def test_substitute_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test substitution dans une liste."""
        monkeypatch.setenv("VAR1", "value1")
        data = ["${VAR1}", "static", "${VAR1}"]
        result = substitute_env_vars(data)
        assert result == ["value1", "static", "value1"]


class TestLoadYamlConfig:
    """Tests pour load_yaml_config."""

    def test_load_existing_file(self, config_dir: Path) -> None:
        """Test chargement d'un fichier existant."""
        config = load_yaml_config(config_dir / "global.yaml")
        assert isinstance(config, dict)
        assert "vlm_providers" in config

    def test_load_nonexistent_file(self) -> None:
        """Test erreur si fichier inexistant."""
        with pytest.raises(ConfigurationError) as exc_info:
            load_yaml_config(Path("nonexistent.yaml"))
        assert "introuvable" in str(exc_info.value)


class TestLoadConfig:
    """Tests pour load_config."""

    def test_load_global_config(
        self,
        config_dir: Path,
        mock_env_vars: None,
    ) -> None:
        """Test chargement de la configuration globale."""
        config = load_config(config_dir)
        assert config.vlm_providers is not None
        assert config.compliance is not None


class TestLoadStepConfig:
    """Tests pour load_step_config."""

    def test_load_monitoring_config(self, config_dir: Path) -> None:
        """Test chargement config étape monitoring."""
        config = load_step_config("01_monitoring.yaml", config_dir)
        assert isinstance(config, dict)
        assert "watch_paths" in config

    def test_load_by_path(self, config_dir: Path) -> None:
        """Test chargement par chemin complet."""
        full_path = config_dir / "01_monitoring.yaml"
        config = load_step_config(full_path)
        assert isinstance(config, dict)
