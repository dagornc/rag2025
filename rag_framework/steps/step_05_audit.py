"""Étape 5 : Audit logging et traçabilité."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from rag_framework.config import get_llm_client, load_config
from rag_framework.exceptions import StepExecutionError, ValidationError
from rag_framework.steps.base_step import BaseStep
from rag_framework.types import StepData
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class AuditStep(BaseStep):
    """Étape 5 : Audit logging et traçabilité."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise l'étape d'audit.

        Parameters
        ----------
        config : dict[str, Any]
            Configuration de l'étape.
        """
        super().__init__(config)

        # Chargement de la config globale pour accès aux LLM providers
        self.global_config = load_config()

        # Initialisation du client LLM si activé dans la config
        self.llm_client: Optional[Any] = None
        llm_config = self.config.get("llm", {})

        if llm_config.get("enabled", False):
            try:
                # Récupération des paramètres fonctionnels depuis la config de l'étape
                provider = llm_config.get("provider")
                model = llm_config.get("model")
                temperature = llm_config.get("temperature", 0.3)

                # Validation des paramètres obligatoires
                if not provider or not model:
                    logger.warning(
                        "LLM activé mais configuration incomplète "
                        "(provider/model manquant). "
                        "Résumés d'audit désactivés."
                    )
                else:
                    # Création du client LLM via la fonction helper
                    self.llm_client = get_llm_client(
                        provider_name=provider,
                        model=model,
                        temperature=temperature,
                        global_config=self.global_config,
                    )
                    logger.info(
                        f"LLM activé pour résumés d'audit: {provider}/{model} "
                        f"(temperature={temperature})"
                    )

            except Exception as e:
                logger.warning(
                    f"Erreur lors de l'initialisation du client LLM: {e}. "
                    "Résumés d'audit désactivés."
                )
                self.llm_client = None

    def validate_config(self) -> None:
        """Valide la configuration de l'étape."""
        if "audit_logging" not in self.config:
            raise ValidationError(
                "Clé 'audit_logging' manquante dans la configuration",
                details={"step": "AuditStep"},
            )

    def execute(self, data: StepData) -> StepData:
        """Enregistre un audit trail complet de l'opération.

        Args:
            data: Données contenant les résultats des étapes précédentes.

        Returns:
            Données avec 'audit_record' ajouté.

        Raises:
            StepExecutionError: En cas d'erreur durant l'audit.
        """
        try:
            audit_config = self.config.get("audit_logging", {})

            # Création de l'enregistrement d'audit
            audit_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operation": "rag_pipeline_execution",
                "documents_processed": len(data.get("extracted_documents", [])),
                "chunks_created": len(data.get("enriched_chunks", [])),
                "metadata": {
                    "monitoring_config": data.get("monitoring_config", {}),
                    "files_processed": [
                        doc["file_path"] for doc in data.get("extracted_documents", [])
                    ],
                },
            }

            # Enregistrement dans le fichier d'audit
            if audit_config.get("log_all_operations", True):
                self._write_audit_log(audit_record, audit_config)

            # Génération d'un résumé narratif avec LLM si activé
            if self.llm_client is not None:
                try:
                    audit_summary = self._generate_audit_summary(audit_record)
                    audit_record["llm_summary"] = audit_summary
                    logger.info("Résumé d'audit généré avec LLM")

                    # Sauvegarde du résumé dans un fichier séparé si configuré
                    output_config = self.config.get("output", {})
                    if output_config.get("save_summaries", False):
                        self._save_audit_summary(audit_record, output_config)

                except Exception as e:
                    logger.warning(
                        f"Erreur lors de la génération du résumé d'audit: {e}"
                    )
                    audit_record["llm_summary"] = None

            data["audit_record"] = audit_record
            logger.info("Audit: Enregistrement créé avec succès")

            return data

        except Exception as e:
            raise StepExecutionError(
                step_name="AuditStep",
                message=f"Erreur lors de l'audit: {e!s}",
                details={"error": str(e)},
            ) from e

    def _write_audit_log(
        self,
        audit_record: dict[str, Any],
        audit_config: dict[str, Any],
    ) -> None:
        """Écrit l'enregistrement d'audit dans le fichier de log.

        Args:
            audit_record: Enregistrement d'audit.
            audit_config: Configuration de l'audit.
        """
        log_file = audit_config.get("log_file", "logs/audit_trail.jsonl")
        log_path = Path(log_file)

        # Créer le répertoire si nécessaire
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Écriture en mode append (JSONL)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(audit_record, ensure_ascii=False) + "\n")

    def _generate_audit_summary(self, audit_record: dict[str, Any]) -> str:
        """Génère un résumé narratif de l'audit avec LLM.

        Parameters
        ----------
        audit_record : dict[str, Any]
            Enregistrement d'audit structuré.

        Returns:
        -------
        str
            Résumé narratif lisible par un humain.
        """
        # Construction de la liste des fichiers traités
        files_list = "\n".join(
            f"- {file}" for file in audit_record["metadata"].get("files_processed", [])
        )

        # Récupération du prompt depuis la configuration
        # Permet de personnaliser le prompt sans modifier le code
        prompt_template = self.config.get("llm", {}).get("prompts", {}).get(
            "audit_summary",
            # Prompt par défaut si non configuré (fallback)
            """Génère un résumé narratif professionnel de cette opération d'audit.

Timestamp: {timestamp}
Opération: {operation}
Documents traités: {documents_processed}
Chunks créés: {chunks_created}

Fichiers traités:
{files_list}

Rédige un résumé concis (2-3 phrases) adapté pour un rapport de conformité.
Le résumé doit être factuel, professionnel et sans interprétation subjective.""",
        )

        # Substitution des placeholders avec les données de l'audit
        prompt = prompt_template.format(
            timestamp=audit_record["timestamp"],
            operation=audit_record["operation"],
            documents_processed=audit_record["documents_processed"],
            chunks_created=audit_record["chunks_created"],
            files_list=files_list,
        )

        # Appel au LLM pour génération du résumé
        assert self.llm_client is not None
        response = self.llm_client.chat.completions.create(
            model=self.llm_client._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.llm_client._temperature,
            max_tokens=self.config.get("llm", {}).get("max_tokens", 1000),
        )

        # Extraction du résumé généré
        content = response.choices[0].message.content
        if content is None:
            return "Erreur: le LLM a retourné un résumé vide."

        summary: str = content.strip()

        return summary

    def _save_audit_summary(
        self,
        audit_record: dict[str, Any],
        output_config: dict[str, Any],
    ) -> None:
        """Sauvegarde le résumé d'audit dans un fichier séparé.

        Parameters
        ----------
        audit_record : dict[str, Any]
            Enregistrement d'audit complet avec résumé LLM.
        output_config : dict[str, Any]
            Configuration de sauvegarde des résumés.

        Examples
        --------
        >>> step = AuditStep(config)
        >>> audit_record = {"timestamp": "...", "llm_summary": "...", ...}
        >>> output_config = {"save_summaries": True, "summaries_dir": "./data/output/audit_summaries"}
        >>> step._save_audit_summary(audit_record, output_config)
        """
        try:
            # Répertoire de destination
            summaries_dir = Path(
                output_config.get("summaries_dir", "./data/output/audit_summaries")
            )
            summaries_dir.mkdir(parents=True, exist_ok=True)

            # Format de sauvegarde
            format_type = output_config.get("format", "json")

            # Génération du nom de fichier
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_template = output_config.get(
                "filename_template", "audit_summary_{timestamp}.{format}"
            )
            filename = filename_template.format(
                timestamp=timestamp_str, format=format_type
            )
            file_path = summaries_dir / filename

            # Préparation du contenu à sauvegarder
            if format_type == "json":
                self._save_json_summary(audit_record, file_path, output_config)
            elif format_type == "txt":
                self._save_txt_summary(audit_record, file_path, output_config)
            elif format_type == "markdown":
                self._save_markdown_summary(audit_record, file_path, output_config)
            else:
                logger.warning(
                    f"Format de sauvegarde inconnu: {format_type}, "
                    f"utilisation de JSON par défaut"
                )
                self._save_json_summary(audit_record, file_path, output_config)

            logger.info(f"💾 Résumé d'audit sauvegardé: {filename}")
            logger.debug(f"  Chemin complet: {file_path}")

        except Exception as e:
            logger.error(
                f"Erreur sauvegarde résumé d'audit: {e}", exc_info=True
            )
            # Ne pas interrompre le pipeline en cas d'erreur de sauvegarde

    def _save_json_summary(
        self,
        audit_record: dict[str, Any],
        file_path: Path,
        output_config: dict[str, Any],
    ) -> None:
        """Sauvegarde le résumé d'audit au format JSON.

        Parameters
        ----------
        audit_record : dict[str, Any]
            Enregistrement d'audit complet.
        file_path : Path
            Chemin du fichier de destination.
        output_config : dict[str, Any]
            Configuration de sauvegarde.
        """
        # Construction du contenu JSON
        content = {}

        # Métadonnées de base
        if output_config.get("include_metadata", True):
            content["timestamp"] = audit_record.get("timestamp")
            content["operation"] = audit_record.get("operation")
            content["documents_processed"] = audit_record.get("documents_processed")
            content["chunks_created"] = audit_record.get("chunks_created")
            content["files_processed"] = audit_record.get("metadata", {}).get(
                "files_processed", []
            )

        # Résumé LLM
        if output_config.get("include_llm_summary", True):
            content["llm_summary"] = audit_record.get("llm_summary")

        # Données brutes complètes (optionnel)
        if output_config.get("include_raw_data", False):
            content["raw_audit_record"] = audit_record

        # Écriture du fichier JSON
        indent = 2 if output_config.get("pretty_print", True) else None
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=indent)

    def _save_txt_summary(
        self,
        audit_record: dict[str, Any],
        file_path: Path,
        output_config: dict[str, Any],
    ) -> None:
        """Sauvegarde le résumé d'audit au format texte brut.

        Parameters
        ----------
        audit_record : dict[str, Any]
            Enregistrement d'audit complet.
        file_path : Path
            Chemin du fichier de destination.
        output_config : dict[str, Any]
            Configuration de sauvegarde.
        """
        # Modification de l'extension si nécessaire
        file_path = file_path.with_suffix(".txt")

        # Construction du contenu texte
        lines = []

        # En-tête
        lines.append("=" * 70)
        lines.append("RÉSUMÉ D'AUDIT")
        lines.append("=" * 70)
        lines.append("")

        # Métadonnées
        if output_config.get("include_metadata", True):
            lines.append(f"Date: {audit_record.get('timestamp')}")
            lines.append(f"Opération: {audit_record.get('operation')}")
            lines.append(
                f"Documents traités: {audit_record.get('documents_processed')}"
            )
            lines.append(f"Chunks créés: {audit_record.get('chunks_created')}")
            lines.append("")

            # Liste des fichiers
            files = audit_record.get("metadata", {}).get("files_processed", [])
            if files:
                lines.append("Fichiers traités:")
                for file in files:
                    lines.append(f"  - {file}")
                lines.append("")

        # Résumé LLM
        if output_config.get("include_llm_summary", True):
            lines.append("Résumé:")
            lines.append("-" * 70)
            lines.append(audit_record.get("llm_summary", "N/A"))
            lines.append("")

        lines.append("=" * 70)

        # Écriture du fichier texte
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _save_markdown_summary(
        self,
        audit_record: dict[str, Any],
        file_path: Path,
        output_config: dict[str, Any],
    ) -> None:
        """Sauvegarde le résumé d'audit au format Markdown.

        Parameters
        ----------
        audit_record : dict[str, Any]
            Enregistrement d'audit complet.
        file_path : Path
            Chemin du fichier de destination.
        output_config : dict[str, Any]
            Configuration de sauvegarde.
        """
        # Modification de l'extension si nécessaire
        file_path = file_path.with_suffix(".md")

        # Construction du contenu Markdown
        lines = []

        # Titre
        lines.append("# Résumé d'Audit")
        lines.append("")

        # Métadonnées
        if output_config.get("include_metadata", True):
            lines.append("## Métadonnées")
            lines.append("")
            lines.append(f"- **Date**: {audit_record.get('timestamp')}")
            lines.append(f"- **Opération**: `{audit_record.get('operation')}`")
            lines.append(
                f"- **Documents traités**: {audit_record.get('documents_processed')}"
            )
            lines.append(
                f"- **Chunks créés**: {audit_record.get('chunks_created')}"
            )
            lines.append("")

            # Liste des fichiers
            files = audit_record.get("metadata", {}).get("files_processed", [])
            if files:
                lines.append("### Fichiers traités")
                lines.append("")
                for file in files:
                    lines.append(f"- `{file}`")
                lines.append("")

        # Résumé LLM
        if output_config.get("include_llm_summary", True):
            lines.append("## Résumé")
            lines.append("")
            lines.append(audit_record.get("llm_summary", "*Aucun résumé disponible*"))
            lines.append("")

        # Footer
        lines.append("---")
        lines.append(
            f"*Généré automatiquement le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        )

        # Écriture du fichier Markdown
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
