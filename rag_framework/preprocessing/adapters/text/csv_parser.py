"""Adapter pandas pour les fichiers CSV.

Auteur: RAG Framework Team
Version: 1.0.0
"""

from typing import Any, ClassVar

from rag_framework.preprocessing.adapters.base import LibraryAdapter, ParsingError


class CSVAdapter(LibraryAdapter):
    """Adapter pour les fichiers CSV avec pandas.

    Extrait et convertit les données tabulaires en texte.

    Attributes:
        REQUIRED_MODULES: Liste des modules requis.
    """

    REQUIRED_MODULES: ClassVar[list[str]] = ["pandas"]

    def parse(self, file_path: str) -> dict[str, Any]:
        """Parse un fichier CSV avec pandas.

        Args:
            file_path: Chemin vers le fichier .csv.

        Returns:
            Dictionnaire avec text, metadata, data.

        Raises:
            ParsingError: Si le parsing échoue.
        """
        try:
            import pandas as pd

            # Tenter de détecter le séparateur automatiquement
            try:
                df = pd.read_csv(file_path, encoding="utf-8")
            except Exception:
                # Essayer avec d'autres encodings
                try:
                    df = pd.read_csv(file_path, encoding="latin-1")
                except Exception:
                    df = pd.read_csv(file_path, encoding="cp1252")

            # Convertir en texte formaté
            text_lines = []

            # En-têtes
            headers = " | ".join(str(col) for col in df.columns)
            text_lines.append(headers)
            text_lines.append("-" * len(headers))

            # Données (limiter à 1000 premières lignes pour éviter textes trop longs)
            max_rows = 1000
            for _, row in df.head(max_rows).iterrows():
                row_text = " | ".join(str(val) for val in row)
                text_lines.append(row_text)

            if len(df) > max_rows:
                text_lines.append(
                    f"\n... ({len(df) - max_rows} lignes supplémentaires)"
                )

            text = "\n".join(text_lines)

            # Métadonnées
            metadata = {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            }

            # Statistiques de base sur les colonnes numériques
            numeric_cols = df.select_dtypes(include=["number"]).columns
            if len(numeric_cols) > 0:
                metadata["numeric_summary"] = {
                    col: {
                        "mean": float(df[col].mean()),
                        "min": float(df[col].min()),
                        "max": float(df[col].max()),
                    }
                    for col in numeric_cols
                }

            return {
                "text": text,
                "metadata": metadata,
                "data": df.to_dict(orient="records")[
                    :100
                ],  # Inclure 100 premières lignes
            }

        except Exception as e:
            raise ParsingError(f"Échec pandas CSV parsing : {e}") from e
