"""Collecteur de métriques pour le preprocessing.

Auteur: RAG Framework Team
Version: 1.0.0
"""

import json
import time
from pathlib import Path
from typing import Any

from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """Collecte et exporte les métriques de preprocessing.

    Attributes:
        config: Configuration des métriques.
        metrics: Liste des métriques collectées.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise le collecteur.

        Args:
            config: Configuration des métriques depuis parser.yaml.
        """
        self.config = config
        self.metrics: list[dict[str, Any]] = []
        self.enabled = config.get("enabled", True)

    def record_processing(
        self,
        file_path: str,
        library_used: str,
        processing_time: float,
        memory_peak_mb: float,
        success: bool,
        text_length: int = 0,
        chunk_count: int = 0,
    ) -> None:
        """Enregistre une opération de preprocessing.

        Args:
            file_path: Chemin du fichier traité.
            library_used: Librairie utilisée pour le parsing.
            processing_time: Temps de traitement en secondes.
            memory_peak_mb: Pic mémoire en MB.
            success: True si le traitement a réussi.
            text_length: Longueur du texte extrait.
            chunk_count: Nombre de chunks générés.
        """
        if not self.enabled:
            return

        metric = {
            "timestamp": time.time(),
            "file_path": file_path,
            "library_used": library_used,
            "processing_time": processing_time,
            "memory_peak_mb": memory_peak_mb,
            "success": success,
            "text_length": text_length,
            "chunk_count": chunk_count,
        }

        self.metrics.append(metric)

        # Auto-export si batch atteint
        export_frequency = self.config.get("export_frequency", "per_batch")
        if export_frequency == "per_document":
            self.export_metrics()

    def export_metrics(self) -> None:
        """Exporte les métriques au format JSON."""
        if not self.metrics:
            return

        export_path = Path(
            self.config.get("export_path", "logs/preprocessing_metrics.json")
        )
        export_path.parent.mkdir(parents=True, exist_ok=True)

        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(self.metrics, f, indent=2)

        logger.info(
            f"Métriques exportées : {len(self.metrics)} entrées",
            extra={"export_path": str(export_path), "count": len(self.metrics)},
        )

    def get_summary(self) -> dict[str, Any]:
        """Calcule un résumé des métriques.

        Returns:
            Dictionnaire avec statistiques agrégées.
        """
        if not self.metrics:
            return {}

        total = len(self.metrics)
        successes = sum(1 for m in self.metrics if m["success"])
        avg_time = sum(m["processing_time"] for m in self.metrics) / total
        avg_memory = sum(m["memory_peak_mb"] for m in self.metrics) / total

        return {
            "total_documents": total,
            "success_count": successes,
            "success_rate": successes / total if total > 0 else 0,
            "avg_processing_time": avg_time,
            "avg_memory_mb": avg_memory,
        }
