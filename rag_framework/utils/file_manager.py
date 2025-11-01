"""Gestionnaire de fichiers pour le déplacement post-traitement."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class FileManager:
    """Gestionnaire pour le déplacement de fichiers après traitement.

    Déplace les fichiers traités vers:
    - output/processed : Fichiers traités avec succès
    - output/errors : Fichiers en erreur

    Parameters
    ----------
    config : dict[str, Any]
        Configuration file_management depuis monitoring config.

    Attributes:
    ----------
    enabled : bool
        Active/désactive la gestion des fichiers.
    move_processed : bool
        Déplacer les fichiers traités avec succès.
    move_errors : bool
        Déplacer les fichiers en erreur.
    processed_dir : Path
        Répertoire pour les fichiers traités.
    errors_dir : Path
        Répertoire pour les fichiers en erreur.
    preserve_structure : bool
        Préserver la structure des sous-répertoires.
    add_timestamp : bool
        Ajouter timestamp au nom du fichier déplacé.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise le gestionnaire de fichiers.

        Parameters
        ----------
        config : dict[str, Any]
            Configuration file_management.
        """
        self.enabled = config.get("enabled", False)
        self.move_processed = config.get("move_processed", True)
        self.move_errors = config.get("move_errors", True)

        # Répertoires de destination
        self.processed_dir = Path(config.get("processed_dir", "./output/processed"))
        self.errors_dir = Path(config.get("errors_dir", "./output/errors"))

        # Options
        self.preserve_structure = config.get("preserve_structure", True)
        self.add_timestamp = config.get("add_timestamp", True)

        # Création des répertoires si nécessaire
        if self.enabled:
            self._ensure_directories()

            logger.info(
                f"FileManager initialisé - "
                f"processed: {self.processed_dir}, "
                f"errors: {self.errors_dir}"
            )

    def _ensure_directories(self) -> None:
        """Crée les répertoires de destination si ils n'existent pas."""
        if self.move_processed:
            self.processed_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Répertoire processed créé/vérifié: {self.processed_dir}")

        if self.move_errors:
            self.errors_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Répertoire errors créé/vérifié: {self.errors_dir}")

    def move_file_to_processed(
        self, file_path: Path, base_watch_path: Path | None = None
    ) -> Path | None:
        """Déplace un fichier traité avec succès vers output/processed.

        Parameters
        ----------
        file_path : Path
            Chemin du fichier à déplacer.
        base_watch_path : Path | None
            Chemin de base surveillé (pour préserver la structure).

        Returns:
        -------
        Path | None
            Nouveau chemin du fichier déplacé, ou None si désactivé/erreur.

        Examples:
        --------
        >>> manager = FileManager(config)
        >>> source = Path("data/input/docs/rapport.pdf")
        >>> new_path = manager.move_file_to_processed(source)
        >>> print(new_path)
        output/processed/docs/rapport_20250131_143022.pdf
        """
        if not self.enabled or not self.move_processed:
            return None

        if not file_path.exists():
            logger.warning(f"Fichier introuvable pour déplacement: {file_path}")
            return None

        try:
            # Détermination du chemin de destination
            dest_path = self._compute_destination_path(
                file_path, self.processed_dir, base_watch_path
            )

            # Création du répertoire parent si nécessaire
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Déplacement du fichier
            shutil.move(str(file_path), str(dest_path))

            logger.info(f"✓ Fichier déplacé vers processed: {file_path.name}")
            logger.debug(f"  Source: {file_path}")
            logger.debug(f"  Destination: {dest_path}")

            return dest_path

        except Exception as e:
            logger.error(
                f"Erreur déplacement vers processed {file_path.name}: {e}",
                exc_info=True,
            )
            return None

    def move_file_to_errors(
        self, file_path: Path, base_watch_path: Path | None = None, error_msg: str = ""
    ) -> Path | None:
        """Déplace un fichier en erreur vers output/errors.

        Parameters
        ----------
        file_path : Path
            Chemin du fichier à déplacer.
        base_watch_path : Path | None
            Chemin de base surveillé (pour préserver la structure).
        error_msg : str
            Message d'erreur à logger.

        Returns:
        -------
        Path | None
            Nouveau chemin du fichier déplacé, ou None si désactivé/erreur.

        Examples:
        --------
        >>> manager = FileManager(config)
        >>> source = Path("data/input/docs/corrupt.pdf")
        >>> new_path = manager.move_file_to_errors(source, error_msg="Extraction failed")
        >>> print(new_path)
        output/errors/docs/corrupt_20250131_143022.pdf
        """
        if not self.enabled or not self.move_errors:
            return None

        if not file_path.exists():
            logger.warning(f"Fichier introuvable pour déplacement: {file_path}")
            return None

        try:
            # Détermination du chemin de destination
            dest_path = self._compute_destination_path(
                file_path, self.errors_dir, base_watch_path
            )

            # Création du répertoire parent si nécessaire
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Déplacement du fichier
            shutil.move(str(file_path), str(dest_path))

            logger.warning(
                f"✗ Fichier déplacé vers errors: {file_path.name}"
                + (f" - {error_msg}" if error_msg else "")
            )
            logger.debug(f"  Source: {file_path}")
            logger.debug(f"  Destination: {dest_path}")

            # Optionnel : Créer un fichier .error avec le message
            if error_msg:
                error_log_path = dest_path.with_suffix(dest_path.suffix + ".error")
                error_log_path.write_text(
                    f"Erreur: {error_msg}\n"
                    f"Fichier: {file_path}\n"
                    f"Date: {datetime.now().isoformat()}\n",
                    encoding="utf-8",
                )

            return dest_path

        except Exception as e:
            logger.error(
                f"Erreur déplacement vers errors {file_path.name}: {e}", exc_info=True
            )
            return None

    def _compute_destination_path(
        self, file_path: Path, dest_dir: Path, base_watch_path: Path | None
    ) -> Path:
        """Calcule le chemin de destination en préservant optionnellement la structure.

        Parameters
        ----------
        file_path : Path
            Chemin du fichier source.
        dest_dir : Path
            Répertoire de destination de base.
        base_watch_path : Path | None
            Chemin de base surveillé.

        Returns:
        -------
        Path
            Chemin de destination complet.
        """
        # Nom du fichier (avec timestamp optionnel)
        if self.add_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = file_path.stem
            suffix = file_path.suffix
            filename = f"{stem}_{timestamp}{suffix}"
        else:
            filename = file_path.name

        # Préservation de la structure des sous-répertoires
        if self.preserve_structure and base_watch_path:
            try:
                # Calcul du chemin relatif depuis base_watch_path
                relative_path = file_path.parent.relative_to(base_watch_path)
                dest_path = dest_dir / relative_path / filename
            except ValueError:
                # Si file_path n'est pas sous base_watch_path, utiliser nom direct
                dest_path = dest_dir / filename
        else:
            # Pas de préservation de structure
            dest_path = dest_dir / filename

        # Gestion des doublons
        if dest_path.exists():
            # Ajout d'un suffixe numérique
            counter = 1
            while dest_path.exists():
                if self.add_timestamp:
                    # Insérer le counter avant le timestamp
                    stem = file_path.stem
                    suffix = file_path.suffix
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{stem}_{counter}_{timestamp}{suffix}"
                else:
                    stem = file_path.stem
                    suffix = file_path.suffix
                    filename = f"{stem}_{counter}{suffix}"

                if self.preserve_structure and base_watch_path:
                    try:
                        relative_path = file_path.parent.relative_to(base_watch_path)
                        dest_path = dest_dir / relative_path / filename
                    except ValueError:
                        dest_path = dest_dir / filename
                else:
                    dest_path = dest_dir / filename

                counter += 1

        return dest_path

    def get_base_watch_path(
        self, file_path: Path, watch_paths: list[str]
    ) -> Path | None:
        """Détermine le watch_path de base pour un fichier donné.

        Parameters
        ----------
        file_path : Path
            Chemin du fichier.
        watch_paths : list[str]
            Liste des chemins surveillés.

        Returns:
        -------
        Path | None
            Chemin de base surveillé, ou None si non trouvé.
        """
        file_path = file_path.resolve()

        for watch_path_str in watch_paths:
            watch_path = Path(watch_path_str).resolve()
            try:
                # Vérifier si file_path est sous watch_path
                file_path.relative_to(watch_path)
                return watch_path
            except ValueError:
                # Pas sous ce watch_path
                continue

        return None
