"""Adapter Markdown pour les fichiers .md.

Auteur: RAG Framework Team
Version: 1.0.0
"""

from typing import Any, ClassVar

from rag_framework.preprocessing.adapters.base import LibraryAdapter, ParsingError


class MarkdownAdapter(LibraryAdapter):
    """Adapter pour la librairie markdown.

    Extrait et convertit le texte des fichiers Markdown.

    Attributes:
        REQUIRED_MODULES: Liste des modules requis.
    """

    REQUIRED_MODULES: ClassVar[list[str]] = ["markdown"]

    def parse(self, file_path: str) -> dict[str, Any]:
        """Parse un fichier Markdown.

        Args:
            file_path: Chemin vers le fichier .md.

        Returns:
            Dictionnaire avec text (markdown brut), html, metadata.

        Raises:
            ParsingError: Si le parsing échoue.
        """
        try:
            import markdown

            # Configuration des extensions
            extensions = self.library_config.get(
                "extensions", ["extra", "codehilite", "tables", "toc"]
            )

            # Lire le fichier
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                markdown_text = f.read()

            # Convertir en HTML
            md = markdown.Markdown(extensions=extensions)
            html_content = md.convert(markdown_text)

            # Extraire les métadonnées si extension meta est active
            metadata: dict[str, Any] = {}
            if hasattr(md, "Meta"):
                metadata["meta"] = md.Meta

            # Détecter le titre (première ligne # si présente)
            lines = markdown_text.split("\n")
            for line in lines:
                if line.strip().startswith("# "):
                    metadata["title"] = line.strip("# ").strip()
                    break

            # Compter les sections
            section_count = markdown_text.count("\n## ")
            metadata["section_count"] = section_count

            # Compter les liens
            import re

            links = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", markdown_text)
            metadata["links_count"] = len(links)
            if links:
                metadata["links"] = [
                    {"text": text, "url": url} for text, url in links[:10]
                ]  # Limit to 10

            # Compter les blocs de code
            code_blocks = re.findall(r"```[\s\S]*?```", markdown_text)
            metadata["code_blocks_count"] = len(code_blocks)

            return {
                "text": markdown_text,  # Texte markdown brut
                "html": html_content,  # HTML converti
                "metadata": metadata,
            }

        except Exception as e:
            raise ParsingError(f"Échec Markdown parsing : {e}") from e
