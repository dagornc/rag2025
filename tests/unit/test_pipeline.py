"""Tests pour le pipeline RAG."""

from pathlib import Path

import pytest

from rag_framework.pipeline import RAGPipeline


class TestRAGPipeline:
    """Tests pour RAGPipeline."""

    @pytest.fixture
    def pipeline(
        self,
        config_dir: Path,
        mock_env_vars: None,
    ) -> RAGPipeline:
        """Fixture pipeline pour les tests."""
        return RAGPipeline(config_dir=config_dir)

    def test_initialization(self, pipeline: RAGPipeline) -> None:
        """Test initialisation du pipeline."""
        assert pipeline is not None
        assert len(pipeline.steps) == 8

    def test_get_status(self, pipeline: RAGPipeline) -> None:
        """Test récupération du statut."""
        status = pipeline.get_status()
        assert "total_steps" in status
        assert status["total_steps"] == 8
        assert "enabled_steps" in status

    def test_get_step(self, pipeline: RAGPipeline) -> None:
        """Test récupération d'une étape."""
        step = pipeline.get_step("MonitoringStep")
        assert step is not None
        assert step.__class__.__name__ == "MonitoringStep"

    def test_get_nonexistent_step(self, pipeline: RAGPipeline) -> None:
        """Test erreur si étape inexistante."""
        with pytest.raises(ValueError) as exc_info:
            pipeline.get_step("NonexistentStep")
        assert "introuvable" in str(exc_info.value)

    def test_execute_empty_pipeline(
        self,
        pipeline: RAGPipeline,
    ) -> None:
        """Test exécution avec données vides."""
        result = pipeline.execute({})
        assert isinstance(result, dict)
