"""Extracteur basé sur pdfplumber (extraction avancée avec tableaux)."""

from pathlib import Path
from typing import Any, ClassVar

from rag_framework.extractors.base import BaseExtractor, ExtractionResult
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class PdfPlumberExtractor(BaseExtractor):
    """Extracteur utilisant pdfplumber pour l'extraction avancée de PDF.

    pdfplumber est particulièrement reconnu en 2025 pour son excellence
    dans l'extraction de tableaux structurés et de texte avec mise en page
    complexe. Il analyse la position géométrique des éléments pour une
    meilleure reconstruction du contenu.

    Avantages:
    - Excellente extraction de tableaux (le meilleur disponible)
    - Préservation précise de la mise en page
    - Détection fine des colonnes et structures
    - Extraction de coordonnées et métadonnées géométriques
    - API intuitive et bien documentée

    Limitations:
    - Plus lent que PyMuPDF ou pypdf
    - Consommation mémoire plus élevée
    - Pas d'OCR intégré (PDF scannés non supportés)

    Parameters
    ----------
    config : dict[str, Any]
        Configuration de l'extracteur.
        Clés supportées:
        - extract_tables : bool (défaut: True)
        - table_format : str (défaut: "markdown") - "markdown", "text", "csv"
        - preserve_layout : bool (défaut: True)
        - min_text_length : int (défaut: 10)
        - extract_metadata : bool (défaut: True)

    Notes
    -----
    pdfplumber est idéal pour les documents avec tableaux complexes,
    formulaires, ou mises en page multi-colonnes. Pour des PDF simples,
    PyMuPDF sera plus rapide.
    """

    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {".pdf"}

    def can_extract(self, file_path: Path) -> bool:
        """Vérifie si le fichier est un PDF.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier.

        Returns
        -------
        bool
            True si le fichier a l'extension .pdf.

        Examples
        --------
        >>> extractor = PdfPlumberExtractor(config={})
        >>> extractor.can_extract(Path("rapport.pdf"))
        True
        >>> extractor.can_extract(Path("rapport.xlsx"))
        False
        """
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def extract(self, file_path: Path) -> ExtractionResult:
        """Extrait le texte et les tableaux d'un PDF avec pdfplumber.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier PDF.

        Returns
        -------
        ExtractionResult
            Résultat de l'extraction.

        Notes
        -----
        L'extraction combine le texte normal et les tableaux détectés.
        Les tableaux sont formatés selon table_format (markdown par défaut).
        """
        try:
            # Import tardif pour éviter erreur si librairie non installée
            import pdfplumber

            # Options d'extraction
            extract_tables = self.config.get("extract_tables", True)
            table_format = self.config.get("table_format", "markdown")
            preserve_layout = self.config.get("preserve_layout", True)

            # Ouverture du PDF
            with pdfplumber.open(str(file_path)) as pdf:
                text_parts = []
                total_tables = 0

                # Extraction page par page
                for page_num, page in enumerate(pdf.pages):
                    # Extraction du texte
                    if preserve_layout:
                        # layout=True preserve spaces et indentation
                        page_text = page.extract_text(layout=True)
                    else:
                        # Extraction basique plus rapide
                        page_text = page.extract_text()

                    if page_text:
                        text_parts.append(f"=== Page {page_num + 1} ===\n{page_text}")

                    # Extraction des tableaux si activé
                    if extract_tables:
                        tables = page.extract_tables()
                        if tables:
                            for table_idx, table in enumerate(tables):
                                total_tables += 1
                                formatted_table = self._format_table(
                                    table, table_format, page_num + 1, table_idx + 1
                                )
                                if formatted_table:
                                    text_parts.append(formatted_table)

                # Concaténation de toutes les parties
                full_text = "\n\n".join(text_parts)

                # Métadonnées
                metadata: dict[str, Any] = {
                    "num_pages": len(pdf.pages),
                    "file_size": file_path.stat().st_size,
                    "file_name": file_path.name,
                    "extractor": "pdfplumber",
                    "tables_detected": total_tables,
                }

                # Métadonnées PDF si disponibles
                if self.config.get("extract_metadata", True) and pdf.metadata:
                    pdf_meta = pdf.metadata
                    if pdf_meta.get("Title"):
                        metadata["title"] = pdf_meta["Title"]
                    if pdf_meta.get("Author"):
                        metadata["author"] = pdf_meta["Author"]
                    if pdf_meta.get("Subject"):
                        metadata["subject"] = pdf_meta["Subject"]
                    if pdf_meta.get("Creator"):
                        metadata["creator"] = pdf_meta["Creator"]
                    if pdf_meta.get("Producer"):
                        metadata["producer"] = pdf_meta["Producer"]

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

            # Calcul du score de confiance
            # pdfplumber est très fiable, surtout si des tableaux sont détectés
            char_per_page = (
                len(full_text) / metadata["num_pages"]
                if metadata["num_pages"] > 0
                else 0
            )

            if total_tables > 0:
                # Haute confiance si tableaux détectés (force de pdfplumber)
                confidence = 0.95
            elif char_per_page > 200:
                confidence = 0.9
            elif char_per_page > 100:
                confidence = 0.75
            elif char_per_page > 50:
                confidence = 0.6
            else:
                confidence = 0.4

            logger.debug(
                f"pdfplumber: Extrait {len(full_text)} caractères "
                f"depuis {metadata['num_pages']} pages "
                f"avec {total_tables} tableaux "
                f"(confidence={confidence:.2f})"
            )

            return ExtractionResult(
                text=full_text,
                success=True,
                extractor_name=self.name,
                metadata=metadata,
                confidence_score=confidence,
            )

        except ImportError:
            error_msg = (
                "pdfplumber n'est pas installé. Installez avec: pip install pdfplumber"
            )
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
            error_msg = f"Erreur pdfplumber extraction: {e}"
            logger.warning(error_msg)
            return ExtractionResult(
                text="",
                success=False,
                extractor_name=self.name,
                metadata={},
                error=error_msg,
                confidence_score=0.0,
            )

    def _format_table(
        self, table: list[list[Any]], format_type: str, page_num: int, table_num: int
    ) -> str:
        """Formate un tableau selon le format demandé.

        Parameters
        ----------
        table : list[list[Any]]
            Tableau extrait par pdfplumber (liste de lignes).
        format_type : str
            Format de sortie: "markdown", "text", ou "csv".
        page_num : int
            Numéro de la page.
        table_num : int
            Numéro du tableau sur la page.

        Returns
        -------
        str
            Tableau formaté.
        """
        if not table or len(table) == 0:
            return ""

        # Titre du tableau
        header = f"\n### Tableau {table_num} (Page {page_num})\n"

        if format_type == "markdown":
            # Format Markdown avec alignement
            rows = []
            for row in table:
                # Nettoyage des cellules (None → "")
                clean_row = [str(cell or "").strip() for cell in row]
                rows.append("| " + " | ".join(clean_row) + " |")

            # Ajout de la ligne de séparation après l'en-tête
            if len(rows) > 0:
                num_cols = len(table[0])
                separator = "|" + "|".join(["---"] * num_cols) + "|"
                rows.insert(1, separator)

            return header + "\n".join(rows)

        elif format_type == "csv":
            # Format CSV
            rows = []
            for row in table:
                clean_row = [str(cell or "").strip().replace(",", ";") for cell in row]
                rows.append(",".join(clean_row))
            return header + "\n".join(rows)

        else:  # "text" par défaut
            # Format texte tabulé
            rows = []
            for row in table:
                clean_row = [str(cell or "").strip() for cell in row]
                rows.append("\t".join(clean_row))
            return header + "\n".join(rows)
