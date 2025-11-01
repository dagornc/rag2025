"""Gestion sécurisée des secrets et variables d'environnement."""

import os
from pathlib import Path
from typing import Optional, Union


def load_env_file(env_path: Union[Path, str] = ".env") -> None:
    """Charge les variables d'environnement depuis un fichier .env.

    Format attendu: KEY=value (une par ligne).
    Les lignes vides et commençant par # sont ignorées.

    Args:
        env_path: Chemin vers le fichier .env.

    Example:
        >>> load_env_file(".env")
        >>> api_key = os.getenv("OPENAI_API_KEY")
    """
    env_file = Path(env_path)

    if not env_file.exists():
        return

    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Ignore empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse KEY=value
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                os.environ[key] = value


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Récupère un secret depuis les variables d'environnement.

    Args:
        key: Nom de la variable d'environnement.
        default: Valeur par défaut si la variable n'existe pas.

    Returns:
        Valeur du secret ou default.

    Example:
        >>> api_key = get_secret("OPENAI_API_KEY", default="")
    """
    return os.getenv(key, default)
