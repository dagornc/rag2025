"""Extracteur basé sur pandas (extraction de données structurées CSV/Excel)."""

from pathlib import Path
from typing import Any, ClassVar

from rag_framework.extractors.base import BaseExtractor, ExtractionResult
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class PandasExtractor(BaseExtractor):
    """Extracteur utilisant pandas pour l'extraction de données tabulaires.

    pandas est la librairie de référence en 2025 pour le traitement de
    données structurées. Idéale pour CSV, Excel et autres formats tabulaires.

    Avantages:
    - Très performant pour les grands fichiers CSV/Excel
    - Gestion automatique des encodages et délimiteurs
    - Support de multiples formats (CSV, Excel, TSV, etc.)
    - Analyse et statistiques intégrées
    - Détection automatique des types de données
    - Gestion des valeurs manquantes

    Limitations:
    - Conçu pour données structurées (pas de texte libre)
    - Fichiers Excel avec mise en page complexe partiellement supportés
    - Pas d'extraction d'images ou graphiques Excel

    Parameters
    ----------
    config : dict[str, Any]
        Configuration de l'extracteur.
        Clés supportées:
        - output_format : str (défaut: "markdown") - "markdown", "csv", "json"
        - include_index : bool (défaut: False)
        - include_stats : bool (défaut: True)
        - max_rows_display : int (défaut: None) - Limite de lignes à afficher
        - detect_encoding : bool (défaut: True)
        - min_text_length : int (défaut: 10)

    Notes:
    -----
    Pour les fichiers Excel avec mises en page complexes, formules
    ou macros, python-openpyxl ou Docling peuvent être utilisés en fallback.
    """

    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {
        ".csv",
        ".tsv",
        ".xlsx",
        ".xls",
        ".xlsm",
        ".ods",  # OpenDocument Spreadsheet
    }

    def can_extract(self, file_path: Path) -> bool:
        """Vérifie si le fichier est un format tabulaire supporté.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier.

        Returns:
        -------
        bool
            True si le fichier a une extension supportée.

        Examples:
        --------
        >>> extractor = PandasExtractor(config={})
        >>> extractor.can_extract(Path("data.csv"))
        True
        >>> extractor.can_extract(Path("data.xlsx"))
        True
        >>> extractor.can_extract(Path("data.txt"))
        False
        """
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def extract(self, file_path: Path) -> ExtractionResult:
        """Extrait les données d'un fichier tabulaire avec pandas.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier.

        Returns:
        -------
        ExtractionResult
            Résultat de l'extraction.

        Notes:
        -----
        L'extraction détecte automatiquement le format et l'encodage.
        Les données sont formatées selon output_format (markdown par défaut).
        """
        try:
            # Import tardif pour éviter erreur si librairie non installée
            import pandas as pd

            # Options d'extraction
            output_format = self.config.get("output_format", "markdown")
            include_index = self.config.get("include_index", False)
            include_stats = self.config.get("include_stats", True)
            max_rows_display = self.config.get("max_rows_display", None)

            # Lecture selon le format
            file_extension = file_path.suffix.lower()

            if file_extension == ".csv":
                # CSV avec détection automatique du délimiteur et encodage
                df = pd.read_csv(
                    str(file_path),
                    encoding_errors="replace",
                    on_bad_lines="skip",
                )

            elif file_extension == ".tsv":
                # TSV (Tab-Separated Values)
                df = pd.read_csv(
                    str(file_path),
                    sep="\t",
                    encoding_errors="replace",
                    on_bad_lines="skip",
                )

            elif file_extension in {".xlsx", ".xls", ".xlsm"}:
                # Excel (toutes les feuilles)
                excel_file = pd.ExcelFile(str(file_path))
                sheets_data = []

                for sheet_name in excel_file.sheet_names:
                    df_sheet = pd.read_excel(excel_file, sheet_name=sheet_name)
                    sheets_data.append((sheet_name, df_sheet))

                # Traitement des feuilles multiples
                return self._process_multiple_sheets(
                    sheets_data,
                    file_path,
                    output_format,
                    include_index,
                    include_stats,
                    max_rows_display,
                )

            elif file_extension == ".ods":
                # OpenDocument Spreadsheet
                df = pd.read_excel(str(file_path), engine="odf", sheet_name=None)  # type: ignore
                # Note: sheet_name=None retourne un dict de DataFrames
                if isinstance(df, dict):
                    sheets_data = list(df.items())
                    return self._process_multiple_sheets(
                        sheets_data,
                        file_path,
                        output_format,
                        include_index,
                        include_stats,
                        max_rows_display,
                    )

            else:
                # Fallback: tentative de lecture CSV
                df = pd.read_csv(str(file_path), encoding_errors="replace")

            # Traitement d'un DataFrame unique
            return self._process_single_dataframe(
                df,
                file_path,
                output_format,
                include_index,
                include_stats,
                max_rows_display,
            )

        except ImportError:
            error_msg = "pandas n'est pas installé. Installez avec: pip install pandas"
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
            error_msg = f"Erreur pandas extraction: {e}"
            logger.warning(error_msg)
            return ExtractionResult(
                text="",
                success=False,
                extractor_name=self.name,
                metadata={},
                error=error_msg,
                confidence_score=0.0,
            )

    def _process_single_dataframe(
        self,
        df: Any,
        file_path: Path,
        output_format: str,
        include_index: bool,
        include_stats: bool,
        max_rows_display: int | None,
    ) -> ExtractionResult:
        """Traite un DataFrame unique.

        Parameters
        ----------
        df : pandas.DataFrame
            DataFrame à traiter.
        file_path : Path
            Chemin du fichier source.
        output_format : str
            Format de sortie.
        include_index : bool
            Inclure l'index.
        include_stats : bool
            Inclure les statistiques.
        max_rows_display : int | None
            Nombre maximum de lignes à afficher.

        Returns:
        -------
        ExtractionResult
            Résultat de l'extraction.
        """
        text_parts = []

        # Limitation du nombre de lignes si spécifié
        df_display = df.head(max_rows_display) if max_rows_display else df

        # Format de sortie
        if output_format == "markdown":
            table_text = df_display.to_markdown(index=include_index)
        elif output_format == "json":
            table_text = df_display.to_json(orient="records", indent=2)
        else:  # "csv" par défaut
            table_text = df_display.to_csv(index=include_index)

        text_parts.append(table_text)

        # Statistiques descriptives si demandées
        if include_stats and len(df) > 0:
            stats_text = self._generate_stats(df)
            if stats_text:
                text_parts.append(f"\n\n### Statistiques\n\n{stats_text}")

        # Concaténation
        full_text = "\n".join(text_parts)

        # Métadonnées
        metadata: dict[str, Any] = {
            "file_size": file_path.stat().st_size,
            "file_name": file_path.name,
            "extractor": "pandas",
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
        }

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

        # Score de confiance élevé pour pandas (très fiable)
        confidence = 0.95

        logger.debug(
            f"pandas: Extrait {len(df)} lignes × {len(df.columns)} colonnes "
            f"(confidence={confidence:.2f})"
        )

        return ExtractionResult(
            text=full_text,
            success=True,
            extractor_name=self.name,
            metadata=metadata,
            confidence_score=confidence,
        )

    def _process_multiple_sheets(
        self,
        sheets_data: list[tuple[str, Any]],
        file_path: Path,
        output_format: str,
        include_index: bool,
        include_stats: bool,
        max_rows_display: int | None,
    ) -> ExtractionResult:
        """Traite un fichier Excel avec plusieurs feuilles.

        Parameters
        ----------
        sheets_data : list[tuple[str, pandas.DataFrame]]
            Liste de tuples (nom_feuille, DataFrame).
        file_path : Path
            Chemin du fichier source.
        output_format : str
            Format de sortie.
        include_index : bool
            Inclure l'index.
        include_stats : bool
            Inclure les statistiques.
        max_rows_display : int | None
            Nombre maximum de lignes par feuille.

        Returns:
        -------
        ExtractionResult
            Résultat de l'extraction.
        """
        text_parts = []
        total_rows = 0
        total_columns = 0

        for sheet_name, df in sheets_data:
            text_parts.append(f"\n{'=' * 60}")
            text_parts.append(f"FEUILLE: {sheet_name}")
            text_parts.append(f"{'=' * 60}\n")

            # Limitation du nombre de lignes si spécifié
            df_display = df.head(max_rows_display) if max_rows_display else df

            # Format de sortie
            if output_format == "markdown":
                table_text = df_display.to_markdown(index=include_index)
            elif output_format == "json":
                table_text = df_display.to_json(orient="records", indent=2)
            else:  # "csv"
                table_text = df_display.to_csv(index=include_index)

            text_parts.append(table_text)

            # Statistiques
            if include_stats and len(df) > 0:
                stats_text = self._generate_stats(df)
                if stats_text:
                    text_parts.append(f"\n### Statistiques\n\n{stats_text}")

            total_rows += len(df)
            total_columns += len(df.columns)

        # Concaténation
        full_text = "\n".join(text_parts)

        # Métadonnées
        metadata: dict[str, Any] = {
            "file_size": file_path.stat().st_size,
            "file_name": file_path.name,
            "extractor": "pandas",
            "sheets": len(sheets_data),
            "total_rows": total_rows,
            "total_columns": total_columns,
        }

        # Vérification minimale
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

        confidence = 0.95

        logger.debug(
            f"pandas: Extrait {len(sheets_data)} feuilles "
            f"({total_rows} lignes totales) "
            f"(confidence={confidence:.2f})"
        )

        return ExtractionResult(
            text=full_text,
            success=True,
            extractor_name=self.name,
            metadata=metadata,
            confidence_score=confidence,
        )

    def _generate_stats(self, df: Any) -> str:
        """Génère des statistiques descriptives sur un DataFrame.

        Parameters
        ----------
        df : pandas.DataFrame
            DataFrame à analyser.

        Returns:
        -------
        str
            Statistiques formatées.
        """
        stats_lines = []

        # Nombre de lignes et colonnes
        stats_lines.append(f"- **Lignes**: {len(df)}")
        stats_lines.append(f"- **Colonnes**: {len(df.columns)}")

        # Valeurs manquantes
        missing = df.isnull().sum()
        if missing.sum() > 0:
            missing_pct = (missing / len(df) * 100).round(2)
            stats_lines.append("- **Valeurs manquantes**:")
            for col, count in missing[missing > 0].items():
                stats_lines.append(f"  - {col}: {count} ({missing_pct[col]}%)")

        # Types de colonnes
        numeric_cols = df.select_dtypes(include=["number"]).columns
        if len(numeric_cols) > 0:
            stats_lines.append(f"- **Colonnes numériques**: {len(numeric_cols)}")

        return "\n".join(stats_lines)
