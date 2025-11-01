"""Type aliases et protocols pour le framework RAG."""

from pathlib import Path
from typing import Any, Protocol, Union

# Type aliases (compatible Python 3.9+)
ConfigDict = dict[str, Any]
MetadataDict = dict[str, Any]
StepData = dict[str, Any]
PathLike = Union[str, Path]


class Embeddable(Protocol):
    """Protocol pour les objets qui peuvent être convertis en embeddings."""

    def to_text(self) -> str:
        """Convert the object to text representation."""
        ...


class Configurable(Protocol):
    """Protocol pour les objets configurables."""

    def validate_config(self) -> None:
        """Validate the configuration."""
        ...


class Executable(Protocol):
    """Protocol pour les étapes exécutables du pipeline."""

    def execute(self, data: StepData) -> StepData:
        """Execute the step logic."""
        ...
