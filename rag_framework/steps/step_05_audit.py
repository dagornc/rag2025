"""Étape 5 : Audit logging et traçabilité."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from rag_framework.config import get_llm_client, load_config
from rag_framework.exceptions import StepExecutionError, ValidationError
from rag_framework.steps.base_step import BaseStep
from rag_framework.types import StepData
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# PATTERNS REGEX POUR DÉTECTION PII (RGPD)
# ═══════════════════════════════════════════════════════════════════════════

# Email : RFC 5322 simplifié
PII_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

# Téléphone français : +33, 0033, 06/07 formats courants
PII_PHONE_FR_PATTERN = re.compile(r"(?:(?:\+|00)33\s?|0)[1-9](?:[\s.-]?\d{2}){4}\b")

# Téléphone international générique
PII_PHONE_INTL_PATTERN = re.compile(
    r"\+\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,9}"
)

# Numéro de sécurité sociale français (NIR) : 15 chiffres
PII_SSN_FR_PATTERN = re.compile(
    r"\b[12]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}\b"
)

# IBAN européen : 2 lettres + 2 chiffres + jusqu'à 30 caractères
PII_IBAN_PATTERN = re.compile(
    r"\b[A-Z]{2}\d{2}\s?(?:[A-Z0-9]{4}\s?){3,7}[A-Z0-9]{1,4}\b"
)

# Carte de crédit : 13-19 chiffres avec espaces optionnels
PII_CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[\s-]?){3}\d{1,7}\b")

# Adresse IP (IPv4)
PII_IP_ADDRESS_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


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

            # Récupération des chunks pour analyse
            chunks = data.get("enriched_chunks", [])

            # Création de l'enregistrement d'audit
            audit_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operation": "rag_pipeline_execution",
                "documents_processed": len(data.get("extracted_documents", [])),
                "chunks_created": len(chunks),
                "metadata": {
                    "monitoring_config": data.get("monitoring_config", {}),
                    "files_processed": [
                        doc["file_path"] for doc in data.get("extracted_documents", [])
                    ],
                },
            }

            # === DÉTECTION PII RGPD ===
            # Si activée, scanne les chunks pour détecter les données personnelles
            pii_detection_config = self.config.get("pii_detection", {})
            if pii_detection_config.get("enabled", False) and chunks:
                logger.info(
                    "🔍 Détection PII activée - Analyse des données personnelles"
                )
                try:
                    pii_report = self._detect_pii(chunks)
                    audit_record["pii_detection"] = pii_report

                    # Logging des résultats
                    if pii_report["total_pii_found"] > 0:
                        logger.warning(
                            f"⚠️ RGPD: {pii_report['total_pii_found']} PII détectés "
                            f"dans {pii_report['chunks_with_pii_count']} chunks "
                            f"({pii_report['pii_percentage']}%)"
                        )

                        # Log détaillé des types de PII
                        for pii_type, count in pii_report["pii_types"].items():
                            if count > 0:
                                logger.warning(f"  • {pii_type}: {count}")

                        # Log des recommandations
                        logger.info("📋 Recommandations RGPD:")
                        for rec in pii_report["recommendations"]:
                            logger.info(rec)

                        # Alerte critique si données sensibles détectées
                        critical_pii = (
                            pii_report["pii_types"]["ssn_fr"]
                            + pii_report["pii_types"]["credit_card"]
                        )
                        if critical_pii > 0:
                            logger.critical(
                                f"🚨 ALERTE CRITIQUE RGPD: {critical_pii} données "
                                "hautement sensibles détectées (SSN/Cartes)"
                            )

                    else:
                        logger.info("✅ Aucune donnée personnelle détectée")

                except Exception as e:
                    logger.error(f"Erreur détection PII: {e}", exc_info=True)
                    audit_record["pii_detection"] = {
                        "error": str(e),
                        "total_pii_found": 0,
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
        prompt_template = (
            self.config.get("llm", {})
            .get("prompts", {})
            .get(
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

        Examples:
        --------
        >>> step = AuditStep(config)
        >>> audit_record = {"timestamp": "...", "llm_summary": "...", ...}
        >>> output_config = {
        ...     "save_summaries": True,
        ...     "summaries_dir": "./data/output/audit_summaries",
        ... }
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
            timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
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
            logger.error(f"Erreur sauvegarde résumé d'audit: {e}", exc_info=True)
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
            lines.append(f"- **Chunks créés**: {audit_record.get('chunks_created')}")
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
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"*Généré automatiquement le {timestamp}*")

        # Écriture du fichier Markdown
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _detect_pii(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        """Détecte les données personnelles (PII) dans les chunks pour conformité RGPD.

        Scanne tous les contenus textuels des chunks à la recherche de PII
        (emails, téléphones, SSN, IBAN, cartes de crédit, IP) et retourne
        un rapport de détection pour logging dans l'audit trail.

        Parameters
        ----------
        chunks : list[dict[str, Any]]
            Liste des chunks à analyser.

        Returns:
        -------
        dict[str, Any]
            Rapport de détection contenant:
            - total_pii_found: Nombre total de PII détectés
            - pii_types: Dictionnaire {type: count}
            - chunks_with_pii: Liste des indices de chunks contenant PII
            - recommendations: Liste de recommandations RGPD

        Examples:
        --------
        >>> chunks = [{"text": "Contact: john@example.com, Tel: +33612345678"}]
        >>> report = step._detect_pii(chunks)
        >>> print(report["total_pii_found"])
        2
        >>> print(report["pii_types"])
        {'email': 1, 'phone': 1}
        """
        # Initialisation des compteurs
        pii_counts: dict[str, int] = {
            "email": 0,
            "phone_fr": 0,
            "phone_intl": 0,
            "ssn_fr": 0,
            "iban": 0,
            "credit_card": 0,
            "ip_address": 0,
        }

        # Liste des chunks contenant des PII
        chunks_with_pii: list[int] = []

        # Scan de tous les chunks
        for idx, chunk in enumerate(chunks):
            text = chunk.get("text", "")
            if not text:
                continue

            # Variable de tracking pour ce chunk
            chunk_has_pii = False

            # Détection email
            emails = PII_EMAIL_PATTERN.findall(text)
            if emails:
                pii_counts["email"] += len(emails)
                chunk_has_pii = True

            # Détection téléphone français
            phones_fr = PII_PHONE_FR_PATTERN.findall(text)
            if phones_fr:
                pii_counts["phone_fr"] += len(phones_fr)
                chunk_has_pii = True

            # Détection téléphone international
            phones_intl = PII_PHONE_INTL_PATTERN.findall(text)
            # Éviter double comptage avec téléphones FR
            phones_intl_unique = [p for p in phones_intl if p not in phones_fr]
            if phones_intl_unique:
                pii_counts["phone_intl"] += len(phones_intl_unique)
                chunk_has_pii = True

            # Détection SSN français (NIR)
            ssn_fr = PII_SSN_FR_PATTERN.findall(text)
            if ssn_fr:
                pii_counts["ssn_fr"] += len(ssn_fr)
                chunk_has_pii = True

            # Détection IBAN
            ibans = PII_IBAN_PATTERN.findall(text)
            if ibans:
                pii_counts["iban"] += len(ibans)
                chunk_has_pii = True

            # Détection carte de crédit
            credit_cards = PII_CREDIT_CARD_PATTERN.findall(text)
            if credit_cards:
                pii_counts["credit_card"] += len(credit_cards)
                chunk_has_pii = True

            # Détection adresse IP
            ip_addresses = PII_IP_ADDRESS_PATTERN.findall(text)
            if ip_addresses:
                pii_counts["ip_address"] += len(ip_addresses)
                chunk_has_pii = True

            # Enregistrer l'indice du chunk si PII détectés
            if chunk_has_pii:
                chunks_with_pii.append(idx)

        # Calcul du total
        total_pii = sum(pii_counts.values())

        # Génération des recommandations RGPD
        recommendations = []
        if total_pii > 0:
            recommendations.append(
                "⚠️ Données personnelles détectées - Vérifier la conformité RGPD"
            )

            if pii_counts["email"] > 0:
                recommendations.append(
                    f"  • {pii_counts['email']} email(s) détecté(s) - "
                    "Consentement requis (Art. 6 RGPD)"
                )

            if pii_counts["phone_fr"] + pii_counts["phone_intl"] > 0:
                total_phones = pii_counts["phone_fr"] + pii_counts["phone_intl"]
                recommendations.append(
                    f"  • {total_phones} numéro(s) de téléphone détecté(s) - "
                    "Minimisation des données requise"
                )

            if pii_counts["ssn_fr"] > 0:
                recommendations.append(
                    f"  • {pii_counts['ssn_fr']} NIR (Sécurité Sociale) détecté(s) - "
                    "CRITIQUE - Chiffrement obligatoire"
                )

            if pii_counts["iban"] > 0:
                recommendations.append(
                    f"  • {pii_counts['iban']} IBAN détecté(s) - "
                    "Données sensibles - Mesures de sécurité renforcées"
                )

            if pii_counts["credit_card"] > 0:
                recommendations.append(
                    f"  • {pii_counts['credit_card']} numéro(s) de carte détecté(s) - "
                    "CRITIQUE - Conformité PCI DSS requise"
                )

            if pii_counts["ip_address"] > 0:
                recommendations.append(
                    f"  • {pii_counts['ip_address']} adresse(s) IP détectée(s) - "
                    "Pseudonymisation recommandée"
                )

            recommendations.append(
                "📋 Actions requises: "
                "Notification DPO, Évaluation DPIA, Registre des traitements"
            )

        else:
            recommendations.append(
                "✅ Aucune donnée personnelle détectée par l'analyse automatique"
            )

        # Construction du rapport
        report = {
            "total_pii_found": total_pii,
            "pii_types": pii_counts,
            "chunks_with_pii": chunks_with_pii,
            "chunks_with_pii_count": len(chunks_with_pii),
            "total_chunks_analyzed": len(chunks),
            "pii_percentage": (
                round(len(chunks_with_pii) / len(chunks) * 100, 2) if chunks else 0.0
            ),
            "recommendations": recommendations,
        }

        return report
