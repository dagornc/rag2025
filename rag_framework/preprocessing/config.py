"""Configuration Pydantic pour validation stricte de parser.yaml.

Ce module fournit des classes Pydantic pour valider la configuration
du système de prétraitement avec fallback.

Auteur: RAG Framework Team
Version: 1.0.0
"""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator

from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class OptimizationModeConfig(BaseModel):
    """Configuration d'un mode d'optimisation."""

    description: str
    target_speed_docs_per_second: int = Field(gt=0, description="Vitesse cible")
    max_memory_gb: float = Field(gt=0, le=32, description="Mémoire max")
    quality_target_percent: int = Field(ge=50, le=100, description="Qualité cible")
    prefer_lightweight_libraries: bool = False
    enable_ocr: bool = True
    enable_semantic_chunking: bool = False
    streaming_enabled: bool | None = None
    max_retries: int | None = None


class LibraryConfig(BaseModel):
    """Configuration d'une librairie dans la chaîne de fallback."""

    library: str
    priority: int = Field(ge=1, le=10)
    description: str | None = None
    timeout_seconds: int = Field(gt=0, le=300)
    max_file_size_mb: int = Field(gt=0, le=1000)
    config: dict[str, Any] = Field(default_factory=dict)


class OCREngineConfig(BaseModel):
    """Configuration d'un moteur OCR."""

    engine: Literal["tesseract", "easyocr", "paddleocr", "rapidocr", "surya"]
    priority: int = Field(ge=1, le=10)
    description: str | None = None
    language: str | None = None
    languages: list[str] | None = None
    config: str | dict[str, Any] | None = None
    gpu: bool | None = None
    use_gpu: bool | None = None
    use_onnx: bool | None = None
    timeout_seconds: int = Field(default=60, gt=0, le=300)


class OCRFallbackConfig(BaseModel):
    """Configuration du fallback OCR."""

    enabled: bool = True
    trigger_on_empty_text: bool = True
    min_text_length: int = Field(ge=0)
    min_text_density: float | None = Field(default=None, ge=0)
    chain: list[OCREngineConfig] = Field(min_length=1)

    @field_validator("chain")
    @classmethod
    def validate_ocr_priorities_unique(
        cls, v: list[OCREngineConfig]
    ) -> list[OCREngineConfig]:
        """Vérifie que les priorités sont uniques."""
        priorities = [engine.priority for engine in v]
        if len(priorities) != len(set(priorities)):
            raise ValueError("Les priorités OCR doivent être uniques")
        return v


class FileCategoryConfig(BaseModel):
    """Configuration d'une catégorie de fichiers."""

    enabled: bool = True
    extensions: list[str] | None = None
    fallback_chain: list[LibraryConfig] | None = None
    ocr_fallback: OCRFallbackConfig | None = None
    ocr_chain: list[OCREngineConfig] | None = None
    library: str | None = None
    parser: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int | None = None
    max_file_size_mb: int | None = None

    @field_validator("fallback_chain")
    @classmethod
    def validate_priorities_unique(
        cls, v: list[LibraryConfig] | None
    ) -> list[LibraryConfig] | None:
        """Vérifie que les priorités sont uniques."""
        if v is None:
            return None
        priorities = [lib.priority for lib in v]
        if len(priorities) != len(set(priorities)):
            raise ValueError("Les priorités doivent être uniques")
        return v


class ChunkingStrategyConfig(BaseModel):
    """Configuration d'une stratégie de chunking."""

    chunk_size: int | None = Field(default=None, gt=0, le=5000)
    overlap: int | None = Field(default=None, ge=0)
    separator: str | None = None
    separators: list[str] | None = None
    keep_separator: bool | None = None
    provider: str | None = None  # Référence au provider d'embeddings (ex: "sentence_transformers")
    model: str | None = None  # Nom du modèle (ex: "paraphrase-multilingual-MiniLM-L12-v2")
    similarity_threshold: float | None = Field(default=None, ge=0, le=1)
    min_chunk_size: int | None = Field(default=None, gt=0)
    max_chunk_size: int | None = Field(default=None, gt=0)
    buffer_size: int | None = Field(default=None, ge=0)
    breakpoint_percentile_threshold: int | None = Field(default=None, ge=0, le=100)
    base_chunk_size: int | None = Field(default=None, gt=0)
    respect_boundaries: bool | None = None
    boundary_markers: list[str] | None = None
    density_threshold: float | None = Field(default=None, ge=0, le=1)

    @field_validator("overlap")
    @classmethod
    def validate_overlap_smaller_than_chunk(
        cls, v: int | None, info: Any
    ) -> int | None:
        """Vérifie que overlap < chunk_size."""
        if v is None:
            return None
        chunk_size = info.data.get("chunk_size") or info.data.get("base_chunk_size")
        if chunk_size and v >= chunk_size:
            raise ValueError(f"overlap ({v}) doit être < chunk_size ({chunk_size})")
        return v


class ChunkingConfig(BaseModel):
    """Configuration complète du chunking."""

    strategy: Literal["fixed", "recursive", "semantic", "adaptive"]
    strategies: dict[str, ChunkingStrategyConfig]


class MemoryOptimizationConfig(BaseModel):
    """Configuration de l'optimisation mémoire."""

    enabled: bool = True
    strategies: dict[str, Any]


class ErrorHandlingConfig(BaseModel):
    """Configuration de la gestion des erreurs."""

    max_retries: int = Field(ge=0, le=10)
    retry_delay_seconds: int = Field(ge=0, le=60)
    continue_on_error: bool = True
    fallback_to_raw_text: bool = True
    log_errors: bool = True
    error_behaviors: dict[str, str] = Field(default_factory=dict)


class MetricsConfig(BaseModel):
    """Configuration des métriques."""

    enabled: bool = True
    collect: list[str] = Field(min_length=1)
    aggregation: dict[str, Any] | None = None
    export_format: Literal["json", "csv", "yaml"] = "json"
    export_path: str
    export_frequency: Literal["per_document", "per_batch", "on_shutdown"] = "per_batch"


class LoggingConfig(BaseModel):
    """Configuration du logging."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    structured: bool = True
    format: str
    log_file: str
    log_to_console: bool = True
    log_to_file: bool = True
    max_log_size_mb: int = Field(gt=0)
    backup_count: int = Field(ge=0)


class PreprocessingConfig(BaseModel):
    """Configuration complète du système de prétraitement."""

    optimization_mode: Literal["speed", "memory", "compromise", "quality", "custom"]
    optimization_modes: dict[str, OptimizationModeConfig]
    file_categories: dict[str, FileCategoryConfig]
    chunking: ChunkingConfig
    memory_optimization: MemoryOptimizationConfig
    error_handling: ErrorHandlingConfig
    metrics: MetricsConfig
    logging: LoggingConfig

    @field_validator("optimization_modes")
    @classmethod
    def validate_required_modes(
        cls, v: dict[str, OptimizationModeConfig]
    ) -> dict[str, OptimizationModeConfig]:
        """Vérifie que les 5 modes obligatoires sont présents."""
        required = {"speed", "memory", "compromise", "quality", "custom"}
        if not required.issubset(v.keys()):
            missing = required - v.keys()
            raise ValueError(f"Modes manquants: {missing}")
        return v


class ParserConfig(BaseModel):
    """Configuration racine du fichier parser.yaml."""

    preprocessing: PreprocessingConfig


def load_parser_config(config_path: str | Path) -> PreprocessingConfig:
    """Charge et valide parser.yaml avec Pydantic.

    Args:
        config_path: Chemin vers le fichier parser.yaml.

    Returns:
        Configuration validée.

    Raises:
        FileNotFoundError: Si le fichier n'existe pas.
        ValueError: Si la configuration est invalide.
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Fichier de configuration introuvable : {config_path}")

    logger.info(f"Chargement de la configuration depuis {config_path}")

    with open(config_path, encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)

    # Validation automatique via Pydantic
    parser_config = ParserConfig(**raw_config)

    logger.info(
        "Configuration validée avec succès",
        extra={
            "optimization_mode": parser_config.preprocessing.optimization_mode,
            "categories_enabled": sum(
                1
                for cat in parser_config.preprocessing.file_categories.values()
                if cat.enabled
            ),
        },
    )

    return parser_config.preprocessing
