"""Extracteur basé sur BeautifulSoup (parsing HTML/XML avancé)."""

from pathlib import Path
from typing import Any, ClassVar

from rag_framework.extractors.base import BaseExtractor, ExtractionResult
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class HTMLExtractor(BaseExtractor):
    """Extracteur utilisant BeautifulSoup pour le parsing HTML/XML.

    BeautifulSoup est la librairie de référence en 2025 pour l'extraction
    de contenu structuré depuis HTML et XML. Plus puissante que le simple
    stripping de balises, elle permet une extraction intelligente.

    Avantages:
    - Parsing robuste de HTML/XML mal formé
    - Extraction sélective par balises, classes, IDs
    - Nettoyage automatique du bruit (scripts, styles, etc.)
    - Support de multiples parsers (html.parser, lxml, html5lib)
    - Navigation dans l'arbre DOM
    - Extraction de métadonnées (title, meta tags)

    Limitations:
    - Ne gère pas JavaScript dynamique (utiliser Selenium/Playwright)
    - Pages très volumineuses peuvent être lentes
    - N'exécute pas de code (formulaires, AJAX)

    Parameters
    ----------
    config : dict[str, Any]
        Configuration de l'extracteur.
        Clés supportées:
        - parser : str (défaut: "lxml") - "html.parser", "lxml", "html5lib"
        - extract_links : bool (défaut: False)
        - extract_images : bool (défaut: False)
        - extract_metadata : bool (défaut: True)
        - remove_tags : list[str] (défaut: ["script", "style", "nav", "footer"])
        - preserve_structure : bool (défaut: False)
        - min_text_length : int (défaut: 10)

    Notes
    -----
    Parsers disponibles:
    - html.parser : Intégré Python, rapide, pas de dépendance
    - lxml : Très rapide, nécessite lxml (recommandé)
    - html5lib : Le plus tolérant, lent, nécessite html5lib
    """

    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {
        ".html",
        ".htm",
        ".xhtml",
        ".xml",
    }

    def can_extract(self, file_path: Path) -> bool:
        """Vérifie si le fichier est un HTML/XML.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier.

        Returns
        -------
        bool
            True si le fichier a une extension HTML/XML.

        Examples
        --------
        >>> extractor = HTMLExtractor(config={})
        >>> extractor.can_extract(Path("page.html"))
        True
        >>> extractor.can_extract(Path("data.xml"))
        True
        >>> extractor.can_extract(Path("document.pdf"))
        False
        """
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def extract(self, file_path: Path) -> ExtractionResult:
        """Extrait le texte d'un fichier HTML/XML avec BeautifulSoup.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier.

        Returns
        -------
        ExtractionResult
            Résultat de l'extraction.

        Notes
        -----
        L'extraction:
        1. Parse le document avec BeautifulSoup
        2. Supprime les balises indésirables (scripts, styles, etc.)
        3. Extrait le texte principal
        4. Optionnellement extrait métadonnées, liens et images
        """
        try:
            # Import tardif pour éviter erreur si librairie non installée
            from bs4 import BeautifulSoup

            # Options d'extraction
            parser = self.config.get("parser", "lxml")
            extract_links = self.config.get("extract_links", False)
            extract_images = self.config.get("extract_images", False)
            extract_metadata = self.config.get("extract_metadata", True)
            remove_tags = self.config.get(
                "remove_tags", ["script", "style", "nav", "footer", "header", "aside"]
            )
            preserve_structure = self.config.get("preserve_structure", False)

            # Lecture du fichier
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                html_content = f.read()

            # Parsing avec BeautifulSoup
            soup = BeautifulSoup(html_content, parser)

            # Suppression des balises indésirables
            for tag_name in remove_tags:
                for tag in soup.find_all(tag_name):
                    tag.decompose()

            # Métadonnées
            metadata: dict[str, Any] = {
                "file_size": file_path.stat().st_size,
                "file_name": file_path.name,
                "extractor": "beautifulsoup",
                "parser": parser,
            }

            # Extraction des métadonnées HTML
            if extract_metadata:
                metadata.update(self._extract_html_metadata(soup))

            # Extraction du texte principal
            if preserve_structure:
                # Préservation de la structure (titres, paragraphes, listes)
                full_text = self._extract_structured_text(soup)
            else:
                # Extraction simple (tout le texte)
                full_text = soup.get_text(separator="\n", strip=True)

            # Extraction des liens si demandé
            if extract_links:
                links = self._extract_links(soup)
                if links:
                    full_text += "\n\n### Liens\n\n" + "\n".join(links)
                    metadata["links_count"] = len(links)

            # Extraction des images si demandé
            if extract_images:
                images = self._extract_images(soup)
                if images:
                    full_text += "\n\n### Images\n\n" + "\n".join(images)
                    metadata["images_count"] = len(images)

            # Vérification de la longueur minimale
            min_length = self.config.get("min_text_length", 10)
            if len(full_text.strip()) < min_length:
                return ExtractionResult(
                    text=full_text,
                    success=False,
                    extractor_name=self.name,
                    metadata=metadata,
                    error=f"Texte extrait trop court ({len(full_text)} < {min_length})",
                    confidence_score=0.1,
                )

            # Score de confiance élevé pour BeautifulSoup (très fiable)
            confidence = 0.95

            logger.debug(
                f"BeautifulSoup: Extrait {len(full_text)} caractères "
                f"(parser={parser}, confidence={confidence:.2f})"
            )

            return ExtractionResult(
                text=full_text,
                success=True,
                extractor_name=self.name,
                metadata=metadata,
                confidence_score=confidence,
            )

        except ImportError as e:
            error_msg = f"Dépendance manquante: {e}. "
            if "bs4" in str(e):
                error_msg += "Installez avec: pip install beautifulsoup4"
            elif "lxml" in str(e):
                error_msg += "Installez avec: pip install lxml (ou utilisez parser='html.parser')"
            logger.error(error_msg)
            return ExtractionResult(
                text="",
                success=False,
                extractor_name=self.name,
                metadata={},
                error=error_msg,
                confidence_score=0.0,
            )

        except Exception as e:
            error_msg = f"Erreur BeautifulSoup extraction: {e}"
            logger.warning(error_msg)
            return ExtractionResult(
                text="",
                success=False,
                extractor_name=self.name,
                metadata={},
                error=error_msg,
                confidence_score=0.0,
            )

    def _extract_html_metadata(self, soup: Any) -> dict[str, Any]:
        """Extrait les métadonnées HTML (title, meta tags).

        Parameters
        ----------
        soup : BeautifulSoup
            Objet BeautifulSoup.

        Returns
        -------
        dict[str, Any]
            Métadonnées extraites.
        """
        metadata: dict[str, Any] = {}

        # Titre de la page
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text(strip=True)

        # Meta tags courantes
        meta_tags = {
            "description": "description",
            "keywords": "keywords",
            "author": "author",
            "language": "language",
        }

        for key, meta_name in meta_tags.items():
            meta_tag = soup.find("meta", attrs={"name": meta_name})
            if meta_tag and meta_tag.get("content"):
                metadata[key] = meta_tag["content"]

        # Open Graph (og:) pour réseaux sociaux
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content") and "title" not in metadata:
            metadata["title"] = og_title["content"]

        return metadata

    def _extract_structured_text(self, soup: Any) -> str:
        """Extrait le texte en préservant la structure (titres, paragraphes).

        Parameters
        ----------
        soup : BeautifulSoup
            Objet BeautifulSoup.

        Returns
        -------
        str
            Texte structuré avec marqueurs Markdown.
        """
        text_parts = []

        # Extraction des éléments principaux
        for element in soup.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "blockquote"]
        ):
            tag_name = element.name

            # Titres
            if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                level = int(tag_name[1])
                text = element.get_text(strip=True)
                if text:
                    text_parts.append(f"{'#' * level} {text}")

            # Paragraphes
            elif tag_name == "p":
                text = element.get_text(strip=True)
                if text:
                    text_parts.append(text)

            # Listes
            elif tag_name in ["ul", "ol"]:
                list_items = []
                for li in element.find_all("li", recursive=False):
                    text = li.get_text(strip=True)
                    if text:
                        prefix = "-" if tag_name == "ul" else "1."
                        list_items.append(f"  {prefix} {text}")
                if list_items:
                    text_parts.append("\n".join(list_items))

            # Citations
            elif tag_name == "blockquote":
                text = element.get_text(strip=True)
                if text:
                    text_parts.append(f"> {text}")

        return "\n\n".join(text_parts)

    def _extract_links(self, soup: Any) -> list[str]:
        """Extrait tous les liens <a href="...">.

        Parameters
        ----------
        soup : BeautifulSoup
            Objet BeautifulSoup.

        Returns
        -------
        list[str]
            Liste des liens au format "Texte: URL".
        """
        links = []
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            url = link["href"]
            if url and not url.startswith("#"):  # Ignorer ancres locales
                links.append(f"- {text}: {url}" if text else f"- {url}")
        return links

    def _extract_images(self, soup: Any) -> list[str]:
        """Extrait tous les chemins d'images <img src="...">.

        Parameters
        ----------
        soup : BeautifulSoup
            Objet BeautifulSoup.

        Returns
        -------
        list[str]
            Liste des images au format "Alt: URL".
        """
        images = []
        for img in soup.find_all("img", src=True):
            alt = img.get("alt", "")
            src = img["src"]
            images.append(f"- {alt}: {src}" if alt else f"- {src}")
        return images
