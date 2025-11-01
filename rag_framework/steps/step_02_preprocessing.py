"""Étape 2 : Extraction et prétraitement de documents avec fallback robuste."""

import json
import re
import statistics
import time
from datetime import datetime, timezone
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


class MetricsCollector:
    """Collecteur de métriques de performance pour le preprocessing.

    Collecte les métriques configurées dans 02_preprocessing.yaml > metrics.

    Métriques disponibles:
    - processing_time: Temps de traitement total et par document
    - parser_time: Temps par parser utilisé
    - memory_usage: Pic d'utilisation mémoire
    - success_rate: Taux de succès d'extraction
    - fallback_usage: Fréquence d'utilisation des fallbacks
    - text_length: Longueur du texte extrait
    - file_size: Taille des fichiers traités
    - error_count: Nombre d'erreurs rencontrées
    """

    def __init__(self, metrics_config: dict[str, Any]) -> None:
        """Initialise le collecteur de métriques.

        Parameters
        ----------
        metrics_config : dict[str, Any]
            Configuration des métriques depuis 02_preprocessing.yaml > metrics.
        """
        self.enabled = metrics_config.get("enabled", False)
        self.metrics_to_collect = set(metrics_config.get("collect", []))
        self.export_config = metrics_config.get("aggregation", {})
        self.export_path = metrics_config.get(
            "export_path", "logs/preprocessing_metrics.json"
        )
        self.export_frequency = metrics_config.get("export_frequency", "per_batch")

        # Métriques collectées
        self.metrics: dict[str, Any] = {
            "session_start": datetime.now(timezone.utc).isoformat(),
            "documents_processed": 0,
            "documents_succeeded": 0,
            "documents_failed": 0,
            "processing_times": [],
            "parser_usage": {},
            "memory_usage_mb": [],
            "text_lengths": [],
            "file_sizes": [],
            "errors": [],
        }

    def record_document(
        self,
        success: bool,
        processing_time: float,
        parser_used: str,
        text_length: int,
        file_size: int,
        error: str | None = None,
    ) -> None:
        """Enregistre les métriques d'un document traité.

        Parameters
        ----------
        success : bool
            True si l'extraction a réussi, False sinon.
        processing_time : float
            Temps de traitement en secondes.
        parser_used : str
            Nom du parser utilisé (ex: "marker", "docling", "pymupdf").
        text_length : int
            Longueur du texte extrait (en caractères).
        file_size : int
            Taille du fichier en octets.
        error : str | None, optional
            Message d'erreur si échec.
        """
        if not self.enabled:
            return

        self.metrics["documents_processed"] += 1

        if success:
            self.metrics["documents_succeeded"] += 1
        else:
            self.metrics["documents_failed"] += 1
            if error and "error_count" in self.metrics_to_collect:
                self.metrics["errors"].append(error)

        if "processing_time" in self.metrics_to_collect:
            self.metrics["processing_times"].append(processing_time)

        if (
            "parser_time" in self.metrics_to_collect
            or "fallback_usage" in self.metrics_to_collect
        ):
            if parser_used not in self.metrics["parser_usage"]:
                self.metrics["parser_usage"][parser_used] = {"count": 0, "times": []}
            self.metrics["parser_usage"][parser_used]["count"] += 1
            self.metrics["parser_usage"][parser_used]["times"].append(processing_time)

        if "text_length" in self.metrics_to_collect:
            self.metrics["text_lengths"].append(text_length)

        if "file_size" in self.metrics_to_collect:
            self.metrics["file_sizes"].append(file_size)

        if "memory_usage" in self.metrics_to_collect:
            # Mesure de la mémoire RSS du processus (en MB)
            try:
                import resource

                usage_mb = (
                    resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024
                )
                self.metrics["memory_usage_mb"].append(usage_mb)
            except Exception:
                # Fallback si resource n'est pas disponible (Windows)
                pass

    def get_summary(self) -> dict[str, Any]:
        """Génère un résumé statistique des métriques collectées.

        Returns:
        -------
        dict[str, Any]
            Dictionnaire contenant les statistiques agrégées.
        """
        summary = {
            "session_start": self.metrics["session_start"],
            "session_end": datetime.now(timezone.utc).isoformat(),
            "total_documents": self.metrics["documents_processed"],
            "successful_documents": self.metrics["documents_succeeded"],
            "failed_documents": self.metrics["documents_failed"],
            "success_rate": (
                round(
                    self.metrics["documents_succeeded"]
                    / self.metrics["documents_processed"]
                    * 100,
                    2,
                )
                if self.metrics["documents_processed"] > 0
                else 0.0
            ),
        }

        # Statistiques de temps de traitement
        if self.metrics["processing_times"]:
            times = self.metrics["processing_times"]
            summary["processing_time"] = {
                "total_seconds": round(sum(times), 2),
                "mean_seconds": round(statistics.mean(times), 2),
                "median_seconds": round(statistics.median(times), 2),
                "min_seconds": round(min(times), 2),
                "max_seconds": round(max(times), 2),
            }

            # Calcul des percentiles si configuré
            if self.export_config.get("compute_percentiles", False) and len(times) >= 2:
                sorted_times = sorted(times)
                summary["processing_time"]["p50"] = round(
                    statistics.median(sorted_times), 2
                )
                p95_idx = int(len(sorted_times) * 0.95)
                p99_idx = int(len(sorted_times) * 0.99)
                summary["processing_time"]["p95"] = round(sorted_times[p95_idx], 2)
                summary["processing_time"]["p99"] = round(sorted_times[p99_idx], 2)

        # Statistiques d'utilisation des parsers
        if self.metrics["parser_usage"]:
            summary["parser_usage"] = {}
            for parser, data in self.metrics["parser_usage"].items():
                summary["parser_usage"][parser] = {
                    "count": data["count"],
                    "percentage": round(
                        data["count"] / self.metrics["documents_processed"] * 100, 2
                    )
                    if self.metrics["documents_processed"] > 0
                    else 0.0,
                    "mean_time_seconds": round(statistics.mean(data["times"]), 2)
                    if data["times"]
                    else 0.0,
                }

        # Statistiques de mémoire
        if self.metrics["memory_usage_mb"]:
            memory = self.metrics["memory_usage_mb"]
            summary["memory_usage_mb"] = {
                "peak": round(max(memory), 2),
                "mean": round(statistics.mean(memory), 2),
            }

        # Statistiques de longueur de texte
        if self.metrics["text_lengths"]:
            lengths = self.metrics["text_lengths"]
            summary["text_length_stats"] = {
                "total_chars": sum(lengths),
                "mean_chars": round(statistics.mean(lengths), 2),
                "median_chars": round(statistics.median(lengths), 2),
                "min_chars": min(lengths),
                "max_chars": max(lengths),
            }

        # Statistiques de taille de fichier
        if self.metrics["file_sizes"]:
            sizes = self.metrics["file_sizes"]
            summary["file_size_stats"] = {
                "total_bytes": sum(sizes),
                "mean_bytes": round(statistics.mean(sizes), 2),
                "median_bytes": round(statistics.median(sizes), 2),
                "min_bytes": min(sizes),
                "max_bytes": max(sizes),
            }

        # Statistiques d'erreurs
        if self.metrics["errors"]:
            summary["errors"] = {
                "count": len(self.metrics["errors"]),
                "samples": self.metrics["errors"][:5],  # 5 premières erreurs
            }

        return summary

    def export_metrics(self) -> None:
        """Exporte les métriques vers le fichier JSON configuré."""
        if not self.enabled:
            return

        try:
            export_path = Path(self.export_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)

            summary = self.get_summary()

            # Lecture des métriques existantes si le fichier existe
            if export_path.exists():
                with open(export_path, encoding="utf-8") as f:
                    existing_metrics = json.load(f)
                    if not isinstance(existing_metrics, list):
                        existing_metrics = [existing_metrics]
            else:
                existing_metrics = []

            # Ajout de la nouvelle session
            existing_metrics.append(summary)

            # Écriture
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(existing_metrics, f, indent=2, ensure_ascii=False)

            logger.info(f"Métriques exportées vers {export_path}")

        except Exception as e:
            logger.error(f"Erreur lors de l'export des métriques: {e}")


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

    def _apply_optimization_mode(self) -> None:
        """Applique le mode d'optimisation configuré.

        Modifie la configuration en fonction du mode d'optimisation sélectionné:
        - speed: Vitesse maximale (OCR désactivé, parsers légers)
        - memory: Faible empreinte mémoire (streaming, parsers légers)
        - compromise: Équilibre entre vitesse, mémoire et qualité
        - quality: Qualité maximale (OCR activé, chunking sémantique)
        - custom: Configuration personnalisée

        Le mode est défini dans preprocessing.optimization_mode
        et les paramètres sont définis dans preprocessing.optimization_modes
        """
        # Récupération du mode actif
        # Les clés sont sous preprocessing: dans 02_preprocessing.yaml
        preprocessing_config = self.config.get("preprocessing", {})
        optimization_mode = preprocessing_config.get("optimization_mode")
        optimization_modes = preprocessing_config.get("optimization_modes", {})

        # Si aucun mode n'est défini ou modes non configurés, ne rien faire
        if not optimization_mode or not optimization_modes:
            return

        # Récupération des paramètres du mode
        mode_config = optimization_modes.get(optimization_mode)

        if not mode_config:
            logger.warning(
                f"Mode d'optimisation '{optimization_mode}' introuvable. "
                "Configuration par défaut utilisée."
            )
            return

        # Affichage du mode actif
        mode_desc = mode_config.get("description", "")
        logger.info(f"Mode d'optimisation: {optimization_mode} - {mode_desc}")

        # Application des paramètres du mode
        # Les paramètres du mode écrasent la configuration existante

        # 1. Gestion OCR
        if "enable_ocr" in mode_config:
            enable_ocr = mode_config["enable_ocr"]
            if not enable_ocr:
                # Désactiver l'OCR dans file_categories > pdf
                pdf_config = (
                    self.config.get("file_categories", {})
                    .get("pdf", {})
                    .get("extractors", [])
                )
                # Filtrer les extracteurs OCR
                if pdf_config:
                    self.config.setdefault("file_categories", {}).setdefault("pdf", {})[
                        "extractors"
                    ] = [
                        ext
                        for ext in pdf_config
                        if ext.get("name") not in ["docling", "marker", "tesseract"]
                    ]
                logger.info(f"  OCR: {'activé' if enable_ocr else 'désactivé'}")

        # 2. Gestion parsers légers (prefer_lightweight_libraries)
        if mode_config.get("prefer_lightweight_libraries", False):
            # Prioriser pypdf2 et désactiver les parsers lourds
            pdf_config = (
                self.config.get("file_categories", {})
                .get("pdf", {})
                .get("extractors", [])
            )
            if pdf_config:
                # Réorganiser pour mettre pypdf2 en premier
                lightweight_first = []
                others = []
                for ext in pdf_config:
                    if ext.get("name") in ["pypdf2", "pdfplumber"]:
                        lightweight_first.append(ext)
                    else:
                        others.append(ext)

                self.config.setdefault("file_categories", {}).setdefault("pdf", {})[
                    "extractors"
                ] = lightweight_first + others

                logger.info("  Parsers: Priorité aux parsers légers (PyPDF2)")

        # 3. Gestion chunking sémantique
        if "enable_semantic_chunking" in mode_config:
            enable_semantic = mode_config["enable_semantic_chunking"]
            # Cette configuration sera utilisée par step_03_chunking
            # On la stocke dans preprocessing pour accès ultérieur
            self.config.setdefault("preprocessing", {})["semantic_chunking_enabled"] = (
                enable_semantic
            )
            logger.info(
                f"  Chunking sémantique: {'activé' if enable_semantic else 'désactivé'}"
            )

        # 4. Gestion streaming (pour optimisation mémoire)
        if mode_config.get("streaming_enabled", False):
            self.config.setdefault("preprocessing", {})["streaming_enabled"] = True
            logger.info("  Streaming: activé (optimisation mémoire)")

        # 5. Limites de ressources
        if "max_memory_gb" in mode_config:
            max_mem = mode_config["max_memory_gb"]
            self.config.setdefault("preprocessing", {})["max_memory_gb"] = max_mem
            logger.info(f"  Mémoire max: {max_mem} GB")

        if "target_speed_docs_per_second" in mode_config:
            target_speed = mode_config["target_speed_docs_per_second"]
            self.config.setdefault("preprocessing", {})["target_speed"] = target_speed
            logger.info(f"  Vitesse cible: {target_speed} docs/s")

        if "quality_target_percent" in mode_config:
            quality = mode_config["quality_target_percent"]
            self.config.setdefault("preprocessing", {})["quality_target"] = quality
            logger.info(f"  Qualité cible: {quality}%")

        # 6. Gestion retries (pour mode quality)
        if "max_retries" in mode_config:
            max_retries = mode_config["max_retries"]
            self.config.setdefault("preprocessing", {})["max_retries"] = max_retries
            logger.info(f"  Retries max: {max_retries}")

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise l'étape de preprocessing.

        Parameters
        ----------
        config : dict[str, Any]
            Configuration de l'étape depuis 02_preprocessing.yaml.
        """
        super().__init__(config)

        # Application du mode d'optimisation (Feature #5)
        self._apply_optimization_mode()

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

        # Initialisation du collecteur de métriques (Feature #7)
        preprocessing_config = config.get("preprocessing", {})
        metrics_config = preprocessing_config.get("metrics", {"enabled": False})
        self.metrics_collector = MetricsCollector(metrics_config)

        logger.info(
            f"PreprocessingStep initialisé avec extracteurs: "
            f"{self.fallback_manager.get_available_extractors()}"
        )

        if self.metrics_collector.enabled:
            logger.info("Collecte de métriques activée")

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

                # Mesure de performance pour métriques (Feature #7)
                start_time = time.time()
                file_size = file_path.stat().st_size if file_path.exists() else 0

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
                                error_msg=(
                                    f"Texte trop court: "
                                    f"{len(cleaned_text)} < {min_length} chars"
                                ),
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

                    # Enregistrement des métriques de succès (Feature #7)
                    processing_time = time.time() - start_time
                    self.metrics_collector.record_document(
                        success=True,
                        processing_time=processing_time,
                        parser_used=extractor_name,
                        text_length=len(cleaned_text),
                        file_size=file_size,
                    )

                except Exception as e:
                    logger.error(f"✗ Erreur extraction {file_path.name}: {e}")

                    # Enregistrement des métriques d'échec (Feature #7)
                    processing_time = time.time() - start_time
                    self.metrics_collector.record_document(
                        success=False,
                        processing_time=processing_time,
                        parser_used="error",
                        text_length=0,
                        file_size=file_size,
                        error=str(e),
                    )

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

            # Export des métriques si activé (Feature #7)
            if self.metrics_collector.enabled:
                summary = self.metrics_collector.get_summary()
                logger.info(
                    f"📊 Métriques: {summary['success_rate']}% succès, "
                    f"{summary.get('processing_time', {}).get('mean_seconds', 0)} s/doc"
                )
                self.metrics_collector.export_metrics()

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

        Returns:
        -------
        Path | None
            Chemin du fichier JSON créé, ou None si désactivé/erreur.

        Examples:
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
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
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
