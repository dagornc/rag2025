"""Adapter pour les fichiers texte brut (.txt).

Auteur: RAG Framework Team
Version: 1.0.0
"""

from typing import Any, ClassVar

from rag_framework.preprocessing.adapters.base import LibraryAdapter, ParsingError


class TextAdapter(LibraryAdapter):
    """Adapter pour les fichiers texte brut.

    Lecture simple sans dépendances externes.

    Attributes:
        REQUIRED_MODULES: Aucun module requis.
    """

    REQUIRED_MODULES: ClassVar[list[str]] = []  # Pas de dépendances

    def parse(self, file_path: str) -> dict[str, Any]:
        """Parse un fichier texte brut.

        Args:
            file_path: Chemin vers le fichier .txt.

        Returns:
            Dictionnaire avec text, metadata.

        Raises:
            ParsingError: Si la lecture échoue.
        """
        try:
            # Tenter différents encodages
            encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]

            text = None
            encoding_used = None

            for encoding in encodings:
                try:
                    with open(file_path, encoding=encoding) as f:
                        text = f.read()
                    encoding_used = encoding
                    break
                except UnicodeDecodeError:
                    continue

            if text is None:
                # Dernier recours: ignorer les erreurs
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                encoding_used = "utf-8 (with errors ignored)"

            # Métadonnées
            lines = text.split("\n")
            metadata = {
                "encoding": encoding_used,
                "line_count": len(lines),
                "char_count": len(text),
                "word_count": len(text.split()),
            }

            return {"text": text, "metadata": metadata}

        except Exception as e:
            raise ParsingError(f"Échec lecture fichier texte : {e}") from e
