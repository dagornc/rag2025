"""Adapter BeautifulSoup pour les fichiers HTML.

Auteur: RAG Framework Team
Version: 1.0.0
"""

from typing import Any, ClassVar

from rag_framework.preprocessing.adapters.base import LibraryAdapter, ParsingError


class BeautifulSoupAdapter(LibraryAdapter):
    """Adapter pour la librairie BeautifulSoup4.

    Extrait le texte des fichiers HTML.

    Attributes:
        REQUIRED_MODULES: Liste des modules requis.
    """

    REQUIRED_MODULES: ClassVar[list[str]] = ["bs4", "lxml"]

    def parse(self, file_path: str) -> dict[str, Any]:
        """Parse un fichier HTML avec BeautifulSoup.

        Args:
            file_path: Chemin vers le fichier .html.

        Returns:
            Dictionnaire avec text, metadata.

        Raises:
            ParsingError: Si le parsing échoue.
        """
        try:
            from bs4 import BeautifulSoup

            # Configuration
            parser = self.library_config.get("parser", "lxml")
            extract_text_only = self.library_config.get("extract_text_only", True)
            remove_scripts = self.library_config.get("remove_scripts", True)
            remove_styles = self.library_config.get("remove_styles", True)
            preserve_links = self.library_config.get("preserve_links", False)

            # Lire le fichier
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                html_content = f.read()

            # Parser le HTML
            soup = BeautifulSoup(html_content, parser)

            # Supprimer les scripts et styles si configuré
            if remove_scripts:
                for script in soup(["script", "noscript"]):
                    script.extract()

            if remove_styles:
                for style in soup(["style"]):
                    style.extract()

            # Extraire le texte
            if extract_text_only:
                text = soup.get_text(separator="\n", strip=True)
            else:
                text = str(soup)

            # Préserver les liens si configuré
            links = []
            if preserve_links:
                for link in soup.find_all("a", href=True):
                    links.append(
                        {"text": link.get_text(strip=True), "href": link["href"]}
                    )

            # Métadonnées
            metadata: dict[str, Any] = {
                "title": soup.title.string if soup.title else "",
                "links_count": len(links),
            }

            # Extraire les meta tags
            meta_tags = {}
            for meta in soup.find_all("meta"):
                if meta.get("name"):
                    meta_tags[meta["name"]] = meta.get("content", "")
                elif meta.get("property"):
                    meta_tags[meta["property"]] = meta.get("content", "")

            metadata["meta_tags"] = meta_tags

            if links:
                metadata["links"] = links

            return {"text": text, "metadata": metadata}

        except Exception as e:
            raise ParsingError(f"Échec BeautifulSoup parsing : {e}") from e
