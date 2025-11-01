"""Tests unitaires pour le système de preprocessing.

Auteur: RAG Framework Team
Version: 1.0.0
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from rag_framework.preprocessing.config import load_parser_config
from rag_framework.preprocessing.router import DocumentRouter


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    """Crée un fichier de config minimal pour les tests.

    Args:
        tmp_path: Chemin temporaire fourni par pytest.

    Returns:
        Chemin vers le fichier de config créé.
    """
    config_content = """
preprocessing:
  optimization_mode: "quality"
  optimization_modes:
    speed:
      description: "Speed mode"
      target_speed_docs_per_second: 30
      max_memory_gb: 4.0
      quality_target_percent: 80
      prefer_lightweight_libraries: true
      enable_ocr: false
      enable_semantic_chunking: false
    memory:
      description: "Memory mode"
      target_speed_docs_per_second: 10
      max_memory_gb: 2.0
      quality_target_percent: 85
      prefer_lightweight_libraries: true
      enable_ocr: true
      enable_semantic_chunking: false
    compromise:
      description: "Compromise mode"
      target_speed_docs_per_second: 20
      max_memory_gb: 3.0
      quality_target_percent: 90
      prefer_lightweight_libraries: false
      enable_ocr: true
      enable_semantic_chunking: false
    quality:
      description: "Quality mode"
      target_speed_docs_per_second: 5
      max_memory_gb: 8.0
      quality_target_percent: 98
      prefer_lightweight_libraries: false
      enable_ocr: true
      enable_semantic_chunking: true
    custom:
      description: "Custom mode"
      target_speed_docs_per_second: 15
      max_memory_gb: 4.0
      quality_target_percent: 92
      prefer_lightweight_libraries: false
      enable_ocr: true
      enable_semantic_chunking: true
  file_categories:
    pdf:
      enabled: true
      extensions:
        - ".pdf"
      fallback_chain:
        - library: "pymupdf"
          priority: 1
          timeout_seconds: 30
          max_file_size_mb: 100
          config: {}
  chunking:
    strategy: "fixed"
    strategies:
      fixed:
        chunk_size: 1000
        overlap: 200
  memory_optimization:
    enabled: true
    strategies: {}
  error_handling:
    max_retries: 2
    retry_delay_seconds: 2
    continue_on_error: true
    fallback_to_raw_text: true
    log_errors: true
  metrics:
    enabled: true
    collect: ["processing_time"]
    export_format: "json"
    export_path: "logs/test_metrics.json"
  logging:
    level: "INFO"
    structured: true
    format: "%(message)s"
    log_file: "logs/test.log"
    log_to_console: true
    log_to_file: false
    max_log_size_mb: 10
    backup_count: 2
"""
    config_file = tmp_path / "parser_test.yaml"
    config_file.write_text(config_content, encoding="utf-8")
    return config_file


def test_load_parser_config(config_path: Path) -> None:
    """Test le chargement et la validation de la config."""
    config = load_parser_config(str(config_path))

    assert config.optimization_mode == "quality"
    assert len(config.optimization_modes) == 5
    assert "pdf" in config.file_categories


def test_document_router_routing(config_path: Path) -> None:
    """Test le routing des fichiers par extension."""
    config = load_parser_config(str(config_path))
    router = DocumentRouter(config)

    # Test routing PDF
    category = router.route("test.pdf")
    assert category == "pdf"

    # Test extension non supportée
    with pytest.raises(ValueError, match="Extension non supportée"):
        router.route("test.unknown")


def test_document_router_extension_map(config_path: Path) -> None:
    """Test la construction du mapping extension -> catégorie."""
    config = load_parser_config(str(config_path))
    router = DocumentRouter(config)

    assert ".pdf" in router.extension_map
    assert router.extension_map[".pdf"] == "pdf"


def test_config_validation_missing_mode(tmp_path: Path) -> None:
    """Test que la validation Pydantic détecte les modes manquants."""
    invalid_config = """
preprocessing:
  optimization_mode: "quality"
  optimization_modes:
    speed:
      description: "Speed"
      target_speed_docs_per_second: 30
      max_memory_gb: 4.0
      quality_target_percent: 80
      prefer_lightweight_libraries: false
      enable_ocr: false
      enable_semantic_chunking: false
  file_categories: {}
  chunking:
    strategy: "fixed"
    strategies:
      fixed:
        chunk_size: 1000
  memory_optimization:
    enabled: true
    strategies: {}
  error_handling:
    max_retries: 2
    retry_delay_seconds: 2
    continue_on_error: true
    fallback_to_raw_text: true
    log_errors: true
  metrics:
    enabled: true
    collect: ["time"]
    export_format: "json"
    export_path: "logs/test.json"
  logging:
    level: "INFO"
    structured: true
    format: "%(message)s"
    log_file: "logs/test.log"
    log_to_console: true
    log_to_file: false
    max_log_size_mb: 10
    backup_count: 2
"""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text(invalid_config, encoding="utf-8")

    # Le chargement doit échouer car il manque les modes requis
    with pytest.raises(ValueError, match="Modes manquants"):
        load_parser_config(str(config_file))
