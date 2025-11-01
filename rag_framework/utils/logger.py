"""Configuration du logging structuré."""

import logging
import sys
from pathlib import Path
from typing import Optional, Union


def setup_logger(
    name: str = "rag_framework",
    level: str = "INFO",
    log_file: Optional[Union[Path, str]] = None,
    log_format: Optional[str] = None,
) -> logging.Logger:
    """Configure et retourne un logger.

    Args:
        name: Nom du logger.
        level: Niveau de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Chemin vers le fichier de log (optionnel).
        log_format: Format des messages de log (optionnel).

    Returns:
        Logger configuré.

    Example:
        >>> logger = setup_logger("my_app", level="DEBUG")
        >>> logger.info("Application démarrée")
    """
    # Récupération du logger par son nom (crée un nouveau si inexistant)
    # Les loggers sont organisés en hiérarchie par points (ex: rag_framework.steps)
    logger = logging.getLogger(name)

    # Conversion du niveau string en constante logging (INFO → logging.INFO)
    # getattr() permet d'accéder dynamiquement aux attributs de logging
    logger.setLevel(getattr(logging, level.upper()))

    # Nettoyage des handlers existants pour éviter duplication
    # Sans cela, chaque appel à setup_logger() ajouterait des handlers
    # Symptôme: logs en double, triple, etc.
    if logger.hasHandlers():
        logger.handlers.clear()

    # Format par défaut si non spécifié
    # Inclut: timestamp, nom du logger, niveau, message
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Création du formatter pour tous les handlers
    formatter = logging.Formatter(log_format)

    # Handler 1: Console (stdout)
    # Affiche les logs dans le terminal/console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler 2: Fichier (optionnel)
    # Persiste les logs sur disque pour analyse ultérieure
    if log_file:
        log_path = Path(log_file)

        # Création du répertoire parent si nécessaire
        # parents=True : crée tous les répertoires intermédiaires
        # exist_ok=True : pas d'erreur si le répertoire existe déjà
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Création du handler fichier avec encoding UTF-8
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Récupère un logger existant.

    Args:
        name: Nom du logger.

    Returns:
        Logger existant.
    """
    return logging.getLogger(name)
