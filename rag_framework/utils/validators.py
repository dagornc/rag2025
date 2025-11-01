"""Validateurs Pydantic personnalisés."""

from pathlib import Path
from typing import Union


def validate_file_exists(value: Union[str, Path]) -> Path:
    """Valide qu'un fichier existe.

    Args:
        value: Chemin vers le fichier.

    Returns:
        Path validé.

    Raises:
        ValueError: Si le fichier n'existe pas.
    """
    path = Path(value)
    if not path.exists():
        raise ValueError(f"Fichier introuvable: {path}")
    if not path.is_file():
        raise ValueError(f"Le chemin n'est pas un fichier: {path}")
    return path


def validate_directory_exists(value: Union[str, Path]) -> Path:
    """Valide qu'un répertoire existe.

    Args:
        value: Chemin vers le répertoire.

    Returns:
        Path validé.

    Raises:
        ValueError: Si le répertoire n'existe pas.
    """
    path = Path(value)
    if not path.exists():
        raise ValueError(f"Répertoire introuvable: {path}")
    if not path.is_dir():
        raise ValueError(f"Le chemin n'est pas un répertoire: {path}")
    return path


def validate_positive_int(value: int) -> int:
    """Valide qu'un entier est positif.

    Args:
        value: Valeur à valider.

    Returns:
        Valeur validée.

    Raises:
        ValueError: Si la valeur n'est pas positive.
    """
    if value <= 0:
        raise ValueError("La valeur doit être strictement positive")
    return value


def validate_probability(value: float) -> float:
    """Valide qu'un float est entre 0 et 1.

    Args:
        value: Valeur à valider.

    Returns:
        Valeur validée.

    Raises:
        ValueError: Si la valeur n'est pas entre 0 et 1.
    """
    if not 0.0 <= value <= 1.0:
        raise ValueError("La valeur doit être entre 0 et 1")
    return value
