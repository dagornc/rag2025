"""Adapter PyMuPDF pour le parsing de PDF.

PyMuPDF (fitz) est rapide et léger, idéal pour extraction de texte simple.

Auteur: RAG Framework Team
Version: 1.0.0
"""

from typing import Any, ClassVar

from rag_framework.preprocessing.adapters.base import LibraryAdapter, ParsingError


class PyMuPDFAdapter(LibraryAdapter):
    """Adapter pour la librairie PyMuPDF (fitz).

    PyMuPDF est particulièrement rapide pour l'extraction de texte simple
    des PDF sans mise en forme complexe.

    Attributes:
        REQUIRED_MODULES: Liste des modules requis (fitz).
    """

    REQUIRED_MODULES: ClassVar[list[str]] = ["fitz"]

    def parse(self, file_path: str) -> dict[str, Any]:
        """Parse un PDF avec PyMuPDF.

        Args:
            file_path: Chemin vers le fichier PDF.

        Returns:
            Dictionnaire avec:
                - text: Texte extrait de toutes les pages
                - metadata: Métadonnées du PDF
                - pages: Liste de dictionnaires par page

        Raises:
            ParsingError: Si le parsing échoue.
        """
        try:
            import fitz  # PyMuPDF

            # Ouvrir le document
            doc = fitz.open(file_path)

            # Configuration
            extract_images = self.library_config.get("extract_images", False)

            # Extraction du texte par page
            pages = []
            full_text = []

            for page_num, page in enumerate(doc, start=1):
                page_dict: dict[str, Any] = {
                    "page_number": page_num,
                    "text": page.get_text("text"),
                }

                # Extraire les images si configuré
                if extract_images:
                    images = []
                    image_list = page.get_images()
                    for img_index, img in enumerate(image_list):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        images.append(
                            {
                                "index": img_index,
                                "width": base_image["width"],
                                "height": base_image["height"],
                                "ext": base_image["ext"],
                            }
                        )
                    page_dict["images"] = images

                pages.append(page_dict)
                full_text.append(page_dict["text"])

            # Métadonnées du document
            metadata = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "producer": doc.metadata.get("producer", ""),
                "page_count": len(doc),
            }

            doc.close()

            return {
                "text": "\n\n".join(full_text),
                "metadata": metadata,
                "pages": pages,
            }

        except Exception as e:
            raise ParsingError(f"Échec PyMuPDF parsing : {e}") from e
