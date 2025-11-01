"""Étape 2 : Extraction et prétraitement de documents avec fallback robuste."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from rag_framework.config_adapter import convert_parser_to_fallback_config
from rag_framework.exceptions import StepExecutionError, ValidationError
from rag_framework.extractors.fallback_manager import FallbackManager
from rag_framework.steps.base_step import BaseStep
from rag_framework.types import StepData
from rag_framework.utils.file_manager import FileManager
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class PreprocessingStep(BaseStep):
    """Étape 2 : Extraction et prétraitement de documents.

    Cette étape utilise un système de fallback robuste pour extraire le texte:
    1. PyPDF2 (rapide, léger)
    2. Docling (OCR, layout analysis)
    3. Marker (ML-based)
    4. VLM (Vision AI, dernier recours)

    Si un extracteur échoue, le système essaie automatiquement le suivant.

    Parameters
    ----------
    config : dict[str, Any]
        Configuration de l'étape depuis 02_preprocessing.yaml.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise l'étape de preprocessing.

        Parameters
        ----------
        config : dict[str, Any]
            Configuration de l'étape depuis 02_preprocessing.yaml.
        """
        super().__init__(config)

        # Conversion de la config 02_preprocessing.yaml vers format FallbackManager
        fallback_config = convert_parser_to_fallback_config(config)

        # Initialisation du gestionnaire de fallback
        self.fallback_manager = FallbackManager(fallback_config)

        # Initialisation du gestionnaire de fichiers
        # Note: file_management config vient de monitoring_config
        file_mgmt_config = config.get("file_management", {"enabled": False})
        self.file_manager = FileManager(file_mgmt_config)

        # Configuration de la sauvegarde du texte extrait
        # Note: output config vient de monitoring_config
        self.output_config = config.get("output", {"save_extracted_text": False})

        logger.info(
            f"PreprocessingStep initialisé avec extracteurs: "
            f"{self.fallback_manager.get_available_extractors()}"
        )

    def validate_config(self) -> None:
        """Valide la configuration de l'étape.

        Accepte deux formats:
        - Format file_categories: {"preprocessing": {"file_categories": {...}}}
        - Format fallback direct: {"fallback": {...}}
        """
        # Vérifier format file_categories (02_preprocessing.yaml) ou fallback direct
        has_preprocessing = "preprocessing" in self.config
        has_fallback = "fallback" in self.config

        if not has_preprocessing and not has_fallback:
            raise ValidationError(
                "Clé 'preprocessing' ou 'fallback' manquante dans la configuration",
                details={"step": "PreprocessingStep"},
            )

    def execute(self, data: StepData) -> StepData:
        """Extrait le texte des documents et applique le nettoyage.

        Args:
            data: Données contenant 'monitored_files' ou 'file_paths'.

        Returns:
            Données avec 'extracted_documents' ajouté.

        Raises:
            StepExecutionError: En cas d'erreur durant l'extraction.
        """
        try:
            file_paths = data.get("monitored_files", data.get("file_paths", []))

            if not file_paths:
                logger.warning("Aucun fichier à traiter")
                data["extracted_documents"] = []
                return data

            extracted_documents = []

            # Récupération des watch_paths pour préserver la structure
            monitoring_config = data.get("monitoring_config", {})
            watch_paths = monitoring_config.get("watch_paths", [])

            logger.info(f"Traitement de {len(file_paths)} fichiers...")

            for file_path_str in file_paths:
                file_path = Path(file_path_str)

                try:
                    # Extraction avec fallback automatique
                    result, extractor_name = (
                        self.fallback_manager.extract_with_fallback(file_path)
                    )

                    # Nettoyage du texte extrait
                    cleaned_text = self._clean_text(result.text)

                    # Validation de la longueur minimale
                    min_length = self.config.get("text_processing", {}).get(
                        "min_text_length", 100
                    )

                    if len(cleaned_text) < min_length:
                        logger.warning(
                            f"Document {file_path.name} trop court "
                            f"({len(cleaned_text)} < {min_length} chars). Ignoré."
                        )

                        # Déplacement vers errors (texte trop court)
                        if self.file_manager.enabled:
                            base_path = self.file_manager.get_base_watch_path(
                                file_path, watch_paths
                            )
                            self.file_manager.move_file_to_errors(
                                file_path,
                                base_path,
                                error_msg=f"Texte trop court: {len(cleaned_text)} < {min_length} chars",
                            )

                        continue

                    # Création de l'enregistrement du document extrait
                    document_record = {
                        "file_path": str(file_path),
                        "text": cleaned_text,
                        "original_length": len(result.text),
                        "cleaned_length": len(cleaned_text),
                        "extraction_method": extractor_name,
                        "confidence_score": result.confidence_score,
                        "metadata": result.metadata,
                    }

                    # Ajout des métadonnées optionnelles
                    if self.config.get("metadata", {}).get(
                        "include_extraction_method", True
                    ):
                        document_record["extractor_used"] = extractor_name

                    if self.config.get("metadata", {}).get(
                        "include_confidence_score", True
                    ):
                        document_record["confidence"] = result.confidence_score

                    extracted_documents.append(document_record)

                    logger.info(
                        f"✓ Document extrait: {file_path.name} "
                        f"(méthode: {extractor_name}, "
                        f"{len(cleaned_text)} chars, "
                        f"confidence: {result.confidence_score:.2f})"
                    )

                    # Sauvegarde du texte extrait en JSON
                    if self.output_config.get("save_extracted_text", False):
                        base_path = self.file_manager.get_base_watch_path(
                            file_path, watch_paths
                        )
                        json_path = self._save_extracted_json(
                            document_record, file_path, base_path
                        )
                        if json_path:
                            document_record["extracted_json_path"] = str(json_path)

                    # Déplacement vers processed (succès)
                    if self.file_manager.enabled:
                        base_path = self.file_manager.get_base_watch_path(
                            file_path, watch_paths
                        )
                        new_path = self.file_manager.move_file_to_processed(
                            file_path, base_path
                        )

                        # Mise à jour du file_path dans le document_record
                        if new_path:
                            document_record["original_file_path"] = str(file_path)
                            document_record["processed_file_path"] = str(new_path)

                except Exception as e:
                    logger.error(f"✗ Erreur extraction {file_path.name}: {e}")

                    # Déplacement vers errors
                    if self.file_manager.enabled:
                        base_path = self.file_manager.get_base_watch_path(
                            file_path, watch_paths
                        )
                        self.file_manager.move_file_to_errors(
                            file_path, base_path, error_msg=str(e)
                        )

                    # Gestion d'erreur: skip ou raise
                    skip_on_error = self.config.get("error_handling", {}).get(
                        "skip_on_error", False
                    )

                    if not skip_on_error:
                        raise

            # Vérification qu'au moins un document a été extrait
            if not extracted_documents:
                logger.warning(
                    "Aucun document n'a pu être extrait avec succès. "
                    "Vérifiez la configuration du fallback."
                )

            data["extracted_documents"] = extracted_documents

            logger.info(
                f"Preprocessing: {len(extracted_documents)} documents traités "
                f"avec succès (sur {len(file_paths)} tentatives)"
            )

            return data

        except Exception as e:
            raise StepExecutionError(
                step_name="PreprocessingStep",
                message=f"Erreur lors du prétraitement: {e!s}",
                details={"error": str(e)},
            ) from e

    def _clean_text(self, text: str) -> str:
        r"""Nettoie le texte extrait selon la configuration.

        Parameters
        ----------
        text : str
            Texte brut extrait.

        Returns:
        -------
        str
            Texte nettoyé.

        Examples:
        --------
        >>> step = PreprocessingStep(config)
        >>> clean = step._clean_text("  Multiple   spaces  \n\npage 42\n")
        >>> print(clean)
        'Multiple spaces'
        """
        cleaning_config = self.config.get("cleaning", {})

        # 1. Normalisation des espaces multiples
        if cleaning_config.get("normalize_whitespace", True):
            text = re.sub(r"\s+", " ", text)
            text = text.strip()

        # 2. Suppression des numéros de page
        if cleaning_config.get("remove_page_numbers", True):
            # Pattern : "page 42", "Page 1", etc.
            text = re.sub(r"\bpage\s+\d+\b", "", text, flags=re.IGNORECASE)

        # 3. Suppression des lignes vides
        if cleaning_config.get("remove_empty_lines", True):
            lines = [line for line in text.split("\n") if line.strip()]
            text = "\n".join(lines)

        # 4. Suppression des lignes trop courtes
        min_line_length = cleaning_config.get("min_line_length", 10)
        if min_line_length > 0:
            lines = [
                line
                for line in text.split("\n")
                if len(line.strip()) >= min_line_length
            ]
            text = "\n".join(lines)

        # 5. Suppression HTML si présent
        if cleaning_config.get("strip_html", True):
            text = re.sub(r"<[^>]+>", "", text)

        # 6. Conversion en minuscules (optionnel)
        if cleaning_config.get("lowercase", False):
            text = text.lower()

        # 7. Suppression des caractères spéciaux (optionnel)
        if cleaning_config.get("remove_special_chars", False):
            # Conserver uniquement lettres, chiffres, espaces et ponctuation basique
            text = re.sub(r"[^a-zA-Z0-9\s\.,!?;:\-\(\)]", "", text)

        return text.strip()

    def _save_extracted_json(
        self,
        document_record: dict[str, Any],
        file_path: Path,
        base_watch_path: Path | None,
    ) -> Path | None:
        """Sauvegarde le document extrait en JSON.

        Parameters
        ----------
        document_record : dict[str, Any]
            Enregistrement du document avec texte et métadonnées.
        file_path : Path
            Chemin du fichier source.
        base_watch_path : Path | None
            Chemin de base surveillé (pour préserver la structure).

        Returns
        -------
        Path | None
            Chemin du fichier JSON créé, ou None si désactivé/erreur.

        Examples
        --------
        >>> step = PreprocessingStep(config)
        >>> record = {"file_path": "...", "text": "...", ...}
        >>> json_path = step._save_extracted_json(record, Path("doc.pdf"), None)
        >>> print(json_path)
        data/output/extracted/doc_20250131_143022.json
        """
        # Vérifier si la sauvegarde est activée
        if not self.output_config.get("save_extracted_text", False):
            return None

        try:
            # Répertoire de destination
            extracted_dir = Path(
                self.output_config.get("extracted_dir", "./data/output/extracted")
            )

            # Nom du fichier JSON (avec timestamp optionnel)
            if self.output_config.get("add_timestamp", True):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = file_path.stem
                json_filename = f"{stem}_{timestamp}.json"
            else:
                json_filename = f"{file_path.stem}.json"

            # Préservation de la structure des sous-répertoires
            if self.output_config.get("preserve_structure", True) and base_watch_path:
                try:
                    # Calcul du chemin relatif depuis base_watch_path
                    relative_path = file_path.parent.relative_to(base_watch_path)
                    json_path = extracted_dir / relative_path / json_filename
                except ValueError:
                    # Si file_path n'est pas sous base_watch_path
                    json_path = extracted_dir / json_filename
            else:
                # Pas de préservation de structure
                json_path = extracted_dir / json_filename

            # Création du répertoire parent si nécessaire
            json_path.parent.mkdir(parents=True, exist_ok=True)

            # Préparation des données à sauvegarder
            json_data = document_record.copy()

            # Filtrer les métadonnées si demandé
            if not self.output_config.get("include_metadata", True):
                # Garder uniquement file_path et text
                json_data = {
                    "file_path": json_data.get("file_path"),
                    "text": json_data.get("text"),
                }

            # Écriture du fichier JSON
            indent = 2 if self.output_config.get("pretty_print", True) else None
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=indent)

            logger.info(f"💾 Texte extrait sauvegardé: {json_path.name}")
            logger.debug(f"  Chemin complet: {json_path}")

            return json_path

        except Exception as e:
            logger.error(
                f"Erreur sauvegarde JSON pour {file_path.name}: {e}", exc_info=True
            )
            return None
