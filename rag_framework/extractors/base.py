"""Classe de base abstraite pour les extracteurs de texte."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class ExtractionResult:
    """Résultat d'une extraction de texte.

    Attributes:
    ----------
    text : str
        Texte extrait du document.
    success : bool
        True si l'extraction a réussi, False sinon.
    extractor_name : str
        Nom de l'extracteur utilisé.
    metadata : dict[str, Any]
        Métadonnées additionnelles (nombre de pages, format, etc.).
    error : Optional[str]
        Message d'erreur si l'extraction a échoué.
    confidence_score : float
        Score de confiance de l'extraction (0.0 à 1.0).
    """

    text: str
    success: bool
    extractor_name: str
    metadata: dict[str, Any]
    error: Optional[str] = None
    confidence_score: float = 1.0


class BaseExtractor(ABC):
    """Classe de base abstraite pour tous les extracteurs de texte.

    Chaque extracteur implémente une stratégie spécifique d'extraction
    (PyPDF2, Docling, Marker, VLM, etc.) et peut échouer, déclenchant
    un fallback vers l'extracteur suivant dans la chaîne.

    Parameters
    ----------
    config : dict[str, Any]
        Configuration spécifique à cet extracteur.

    Attributes:
    ----------
    name : str
        Nom de l'extracteur (ex: "pypdf2", "docling", "vlm").
    config : dict[str, Any]
        Configuration de l'extracteur.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise l'extracteur.

        Parameters
        ----------
        config : dict[str, Any]
            Configuration spécifique à cet extracteur.
        """
        self.config = config
        self.name = self.__class__.__name__.replace("Extractor", "").lower()

    @abstractmethod
    def can_extract(self, file_path: Path) -> bool:
        """Vérifie si cet extracteur peut traiter ce fichier.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier à extraire.

        Returns:
        -------
        bool
            True si l'extracteur peut traiter ce fichier, False sinon.

        Examples:
        --------
        >>> extractor = PyPDF2Extractor(config={})
        >>> extractor.can_extract(Path("document.pdf"))
        True
        >>> extractor.can_extract(Path("image.png"))
        False
        """
        pass

    @abstractmethod
    def extract(self, file_path: Path) -> ExtractionResult:
        """Extrait le texte d'un fichier.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier à extraire.

        Returns:
        -------
        ExtractionResult
            Résultat de l'extraction avec texte, statut, et métadonnées.

        Raises:
        ------
        Exception
            En cas d'erreur durant l'extraction.
            L'exception est capturée par le gestionnaire de fallback.

        Examples:
        --------
        >>> extractor = PyPDF2Extractor(config={})
        >>> result = extractor.extract(Path("document.pdf"))
        >>> if result.success:
        ...     print(f"Extrait {len(result.text)} caractères")
        """
        pass

    def validate_result(self, result: ExtractionResult) -> bool:
        """Valide qu'un résultat d'extraction est acceptable.

        Cette méthode peut être surchargée pour des critères spécifiques
        (longueur minimale, présence de certain contenu, etc.).

        Parameters
        ----------
        result : ExtractionResult
            Résultat à valider.

        Returns:
        -------
        bool
            True si le résultat est acceptable, False pour déclencher fallback.

        Examples:
        --------
        >>> result = ExtractionResult(text="abc", success=True, ...)
        >>> extractor.validate_result(result)
        False  # Trop court (< 10 caractères par défaut)
        """
        # Critères par défaut de validation
        if not result.success:
            return False

        # Longueur minimale configurable
        min_length = self.config.get("min_text_length", 10)
        if len(result.text.strip()) < min_length:
            return False

        # Score de confiance minimum configurable
        min_confidence = self.config.get("min_confidence", 0.0)
        if result.confidence_score < min_confidence:
            return False

        return True

    def __repr__(self) -> str:
        """Représentation string de l'extracteur."""
        return f"{self.__class__.__name__}(name='{self.name}')"
