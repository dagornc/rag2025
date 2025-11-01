"""Extracteur pour fichiers texte simples."""

from pathlib import Path
from typing import ClassVar

from rag_framework.extractors.base import BaseExtractor, ExtractionResult
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class TextExtractor(BaseExtractor):
    """Extracteur pour fichiers texte simples.

    Supporte les fichiers texte brut qui peuvent être lus directement
    sans librairie spécialisée : .txt, .md, .csv, .xml, .html, .rtf, .tex, .svg

    Avantages:
    - Très rapide (lecture directe)
    - Pas de dépendances externes
    - Fonctionne pour tous les fichiers texte encodés

    Limitations:
    - Pas de traitement spécial pour formats structurés (CSV, XML, HTML)
    - Nécessite que le fichier soit encodé texte (pas binaire)
    - RTF peut contenir des balises de formatage

    Parameters
    ----------
    config : dict[str, Any]
        Configuration de l'extracteur.
        Clés supportées:
        - encoding : str (défaut: "utf-8")
        - fallback_encodings : list[str] (défaut: ["utf-8", "latin-1", "cp1252"])
        - strip_html : bool (défaut: True pour .html)
        - min_text_length : int (défaut: 10)
    """

    # Extensions de fichiers texte supportées
    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {
        ".txt",
        ".md",
        ".csv",
        ".xml",
        ".html",
        ".rtf",
        ".tex",
        ".svg",
    }

    def can_extract(self, file_path: Path) -> bool:
        """Vérifie si le fichier est un texte simple.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier.

        Returns:
        -------
        bool
            True si le fichier a une extension texte supportée.

        Examples:
        --------
        >>> extractor = TextExtractor(config={})
        >>> extractor.can_extract(Path("README.md"))
        True
        >>> extractor.can_extract(Path("document.pdf"))
        False
        """
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def extract(self, file_path: Path) -> ExtractionResult:
        """Extrait le texte d'un fichier texte simple.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier texte.

        Returns:
        -------
        ExtractionResult
            Résultat de l'extraction.

        Examples:
        --------
        >>> extractor = TextExtractor(config={})
        >>> result = extractor.extract(Path("README.md"))
        >>> if result.success:
        ...     print(f"Extrait {len(result.text)} caractères")
        """
        # Encodages à essayer dans l'ordre
        encodings = self.config.get(
            "fallback_encodings", ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
        )

        # Tentative de lecture avec différents encodages
        text = None
        encoding_used = None

        for encoding in encodings:
            try:
                with open(file_path, encoding=encoding) as f:
                    text = f.read()
                encoding_used = encoding
                logger.debug(f"Fichier {file_path.name} lu avec encodage {encoding}")
                break

            except (UnicodeDecodeError, LookupError):
                continue

        if text is None:
            error_msg = (
                f"Impossible de lire {file_path.name} "
                f"avec les encodages : {', '.join(encodings)}"
            )
            logger.error(error_msg)
            return ExtractionResult(
                text="",
                success=False,
                extractor_name=self.name,
                metadata={"file_name": file_path.name},
                error=error_msg,
                confidence_score=0.0,
            )

        # Nettoyage optionnel pour HTML
        if file_path.suffix.lower() == ".html" and self.config.get(
            "strip_html", True
        ):
            text = self._strip_html_tags(text)

        # Métadonnées
        metadata = {
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size,
            "format": file_path.suffix[1:],
            "encoding": encoding_used,
            "text_length": len(text),
        }

        # Score de confiance élevé (lecture directe)
        # Réduit si le texte est très court
        if len(text) > 100:
            confidence = 1.0
        elif len(text) > 10:
            confidence = 0.8
        else:
            confidence = 0.5

        logger.debug(
            f"Text: Extrait {len(text)} caractères "
            f"de {file_path.name} (encoding={encoding_used})"
        )

        return ExtractionResult(
            text=text,
            success=True,
            extractor_name=self.name,
            metadata=metadata,
            confidence_score=confidence,
        )

    def _strip_html_tags(self, html_text: str) -> str:
        """Supprime les balises HTML basiques.

        Parameters
        ----------
        html_text : str
            Texte HTML.

        Returns:
        -------
        str
            Texte sans balises HTML.
        """
        import re

        # Supprimer les balises <script> et <style> et leur contenu
        html_text = re.sub(
            r"<script[^>]*>.*?</script>", "", html_text, flags=re.DOTALL | re.IGNORECASE
        )
        html_text = re.sub(
            r"<style[^>]*>.*?</style>", "", html_text, flags=re.DOTALL | re.IGNORECASE
        )

        # Supprimer toutes les balises HTML
        html_text = re.sub(r"<[^>]+>", " ", html_text)

        # Supprimer les entités HTML communes
        html_text = html_text.replace("&nbsp;", " ")
        html_text = html_text.replace("&amp;", "&")
        html_text = html_text.replace("&lt;", "<")
        html_text = html_text.replace("&gt;", ">")
        html_text = html_text.replace("&quot;", '"')

        # Normaliser les espaces multiples
        html_text = re.sub(r"\s+", " ", html_text).strip()

        return html_text
