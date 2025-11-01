"""Adapter Unstructured pour formats universels.

Support pour LibreOffice (ODT, ODS, ODP) et autres formats.

Auteur: RAG Framework Team
Version: 1.0.0
"""

from typing import Any, ClassVar

from rag_framework.preprocessing.adapters.base import LibraryAdapter, ParsingError


class UnstructuredAdapter(LibraryAdapter):
    """Adapter pour la librairie unstructured.

    Parser universel pour ODT, ODS, ODP, et autres formats.

    Attributes:
        REQUIRED_MODULES: Liste des modules requis.
    """

    REQUIRED_MODULES: ClassVar[list[str]] = ["unstructured"]

    def parse(self, file_path: str) -> dict[str, Any]:
        """Parse un fichier avec Unstructured.

        Args:
            file_path: Chemin vers le fichier.

        Returns:
            Dictionnaire avec text, metadata, elements.

        Raises:
            ParsingError: Si le parsing échoue.
        """
        try:
            from unstructured.partition.auto import partition

            # Configuration
            strategy = self.library_config.get("strategy", "auto")

            # Parser le fichier automatiquement
            elements = partition(filename=file_path, strategy=strategy)

            # Extraire le texte de tous les éléments
            text_parts = []
            element_details = []

            for element in elements:
                element_text = str(element)
                if element_text.strip():
                    text_parts.append(element_text)

                    # Détails de l'élément
                    element_dict = {
                        "type": type(element).__name__,
                        "text": element_text,
                    }

                    # Métadonnées de l'élément si disponibles
                    if hasattr(element, "metadata"):
                        element_dict["metadata"] = {
                            "page_number": getattr(
                                element.metadata, "page_number", None
                            ),
                            "filename": getattr(element.metadata, "filename", None),
                        }

                    element_details.append(element_dict)

            # Métadonnées globales
            metadata = {
                "element_count": len(elements),
                "element_types": list(
                    set(type(e).__name__ for e in elements)
                ),  # Types uniques
                "strategy_used": strategy,
            }

            return {
                "text": "\n\n".join(text_parts),
                "metadata": metadata,
                "elements": element_details,
            }

        except Exception as e:
            raise ParsingError(f"Échec Unstructured parsing : {e}") from e
