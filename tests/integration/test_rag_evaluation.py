"""Tests d'évaluation RAG end-to-end (avec Ragas)."""

from pathlib import Path

import pytest

from rag_framework.pipeline import RAGPipeline


@pytest.mark.integration
@pytest.mark.slow
class TestRAGEvaluation:
    """Tests d'évaluation de la qualité du RAG."""

    @pytest.fixture
    def pipeline(
        self,
        config_dir: Path,
        mock_env_vars: None,
    ) -> RAGPipeline:
        """Fixture pipeline pour les tests."""
        return RAGPipeline(config_dir=config_dir)

    def test_end_to_end_pipeline(
        self,
        pipeline: RAGPipeline,
        create_test_file: Path,
    ) -> None:
        """Test end-to-end du pipeline complet."""
        # Données d'entrée avec le fichier de test
        input_data = {
            "file_paths": [str(create_test_file)],
        }

        # Exécution du pipeline
        result = pipeline.execute(input_data)

        # Vérifications
        assert "normalized_chunks" in result
        assert len(result["normalized_chunks"]) > 0

        # Vérification de la structure des chunks
        first_chunk = result["normalized_chunks"][0]
        assert "text" in first_chunk
        assert "embedding" in first_chunk
        assert "metadata" in first_chunk

    @pytest.mark.skip(reason="Nécessite Ragas et données ground truth")
    def test_ragas_evaluation(self) -> None:
        """Test évaluation avec Ragas (faithfulness, relevancy, etc.)."""
        # TODO: Implémenter après ajout de données ground truth
        pass
