"""Étape 4 : Enrichissement et métadonnées de conformité."""

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from rag_framework.config import get_llm_client, load_config
from rag_framework.exceptions import StepExecutionError
from rag_framework.steps.base_step import BaseStep
from rag_framework.types import StepData
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class EnrichmentStep(BaseStep):
    """Étape 4 : Enrichissement et métadonnées de conformité."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise l'étape d'enrichissement.

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
                temperature = llm_config.get("temperature", 0.0)

                # Validation des paramètres obligatoires
                if not provider or not model:
                    logger.warning(
                        "LLM activé mais configuration incomplète "
                        "(provider/model manquant). "
                        "Classification par mots-clés utilisée."
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
                        f"LLM activé pour enrichissement: {provider}/{model} "
                        f"(temperature={temperature})"
                    )

            except Exception as e:
                logger.warning(
                    f"Erreur lors de l'initialisation du client LLM: {e}. "
                    "Classification par mots-clés utilisée en fallback."
                )
                self.llm_client = None

    def validate_config(self) -> None:
        """Valide la configuration de l'étape."""
        pass  # Configuration optionnelle pour cette étape

    def execute(self, data: StepData) -> StepData:
        """Enrichit les chunks avec des métadonnées de conformité.

        Args:
            data: Données contenant 'chunks'.

        Returns:
            Données avec 'enriched_chunks' ajouté.

        Raises:
            StepExecutionError: En cas d'erreur durant l'enrichissement.
        """
        try:
            chunks = data.get("chunks", [])

            if not chunks:
                logger.warning("Aucun chunk à enrichir")
                data["enriched_chunks"] = []
                return data

            enriched_chunks = []

            for chunk in chunks:
                enriched_chunk = chunk.copy()

                # Ajout hash SHA-256
                if self.config.get("compliance_metadata", {}).get("include_hash", True):
                    enriched_chunk["content_hash"] = self._compute_hash(chunk["text"])

                # Timestamp immuable
                enriched_chunk["processed_at"] = datetime.now(timezone.utc).isoformat()

                # Classification de sensibilité (placeholder)
                enriched_chunk["sensitivity"] = self._classify_sensitivity(
                    chunk["text"]
                )

                # Type de document (placeholder)
                enriched_chunk["document_type"] = self._classify_document_type(
                    chunk["source_file"]
                )

                # Tags réglementaires (placeholder)
                enriched_chunk["regulatory_tags"] = self._extract_regulatory_tags(
                    chunk["text"]
                )

                enriched_chunks.append(enriched_chunk)

            data["enriched_chunks"] = enriched_chunks
            logger.info(f"Enrichment: {len(enriched_chunks)} chunks enrichis")

            # Sauvegarde des chunks enrichis si configuré
            output_config = self.config.get("output", {})
            if output_config.get("save_enriched_chunks", False):
                self._save_enriched_chunks(enriched_chunks, output_config)

            return data

        except Exception as e:
            raise StepExecutionError(
                step_name="EnrichmentStep",
                message=f"Erreur lors de l'enrichissement: {e!s}",
                details={"error": str(e)},
            ) from e

    def _compute_hash(self, text: str) -> str:
        """Calcule le hash SHA-256 d'un texte."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _classify_sensitivity(self, text: str) -> str:
        """Classifie la sensibilité d'un chunk.

        Args:
            text: Texte du chunk.

        Returns:
            Niveau de sensibilité (public, interne, confidentiel, secret).
        """
        # Si LLM activé, utiliser classification intelligente
        if self.llm_client is not None:
            try:
                return self._classify_sensitivity_with_llm(text)
            except Exception as e:
                logger.warning(
                    f"Erreur classification LLM sensibilité: {e}. "
                    "Fallback sur mots-clés."
                )
                # Fallback sur mots-clés en cas d'erreur

        # MVP: classification basique par mots-clés (fallback ou mode par défaut)
        sensitive_keywords = ["confidentiel", "secret", "privé", "interne"]

        text_lower = text.lower()
        for keyword in sensitive_keywords:
            if keyword in text_lower:
                return "confidentiel"

        default_level: str = self.config.get("sensitivity_classification", {}).get(
            "default_level", "interne"
        )
        return default_level

    def _call_llm_with_retry(
        self, prompt: str, max_tokens: int = 500
    ) -> Optional[str]:
        """Appelle le LLM avec gestion du rate limiting et retry.

        Parameters
        ----------
        prompt : str
            Prompt à envoyer au LLM.
        max_tokens : int
            Nombre maximum de tokens pour la réponse.

        Returns
        -------
        Optional[str]
            Réponse du LLM, ou None en cas d'échec après tous les retries.
        """
        assert self.llm_client is not None

        # Configuration du rate limiting
        rate_config = self.config.get("llm", {}).get("rate_limiting", {})
        max_retries = rate_config.get("max_retries", 3)
        retry_delay_base = rate_config.get("retry_delay_base", 2)
        exponential_backoff = rate_config.get("exponential_backoff", True)
        delay_between_requests = rate_config.get("delay_between_requests", 0.5)

        # Délai avant la requête (rate limiting préventif)
        if rate_config.get("enabled", True):
            time.sleep(delay_between_requests)

        # Tentatives avec retry
        for attempt in range(max_retries + 1):
            try:
                response = self.llm_client.chat.completions.create(
                    model=self.llm_client._model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.llm_client._temperature,
                    max_tokens=max_tokens,
                )

                content = response.choices[0].message.content
                return content if content is not None else None

            except Exception as e:
                error_str = str(e)

                # Si c'est une erreur 429 (rate limit), retry avec backoff
                if "429" in error_str or "rate" in error_str.lower():
                    if attempt < max_retries:
                        # Calcul du délai de retry
                        if exponential_backoff:
                            delay = retry_delay_base * (2**attempt)
                        else:
                            delay = retry_delay_base

                        logger.warning(
                            f"Rate limit atteint (tentative {attempt + 1}/{max_retries + 1}). "
                            f"Retry dans {delay}s..."
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(
                            f"Rate limit atteint après {max_retries + 1} tentatives. "
                            "Abandon de l'appel LLM."
                        )
                        raise

                # Pour les autres erreurs, pas de retry
                else:
                    raise

        return None

    def _classify_sensitivity_with_llm(self, text: str) -> str:
        """Classifie la sensibilité d'un chunk avec LLM.

        Parameters
        ----------
        text : str
            Texte du chunk à classifier.

        Returns:
        -------
        str
            Niveau de sensibilité (public, interne, confidentiel, secret).
        """
        # Récupération du prompt depuis la configuration
        # Permet de personnaliser le prompt sans modifier le code
        prompt_template = self.config.get("llm", {}).get("prompts", {}).get(
            "sensitivity_classification",
            # Prompt par défaut si non configuré (fallback)
            """Classifie le niveau de sensibilité du document suivant.
Réponds UNIQUEMENT par l'un de ces mots: public, interne, confidentiel, secret

Critères:
- public: Information accessible à tous
- interne: Information pour l'entreprise uniquement
- confidentiel: Information sensible, accès restreint
- secret: Information hautement sensible, accès très restreint

Document:
{text}

Niveau de sensibilité:""",
        )

        # Substitution du placeholder {text} avec le contenu (limité à 1000 chars)
        prompt = prompt_template.format(text=text[:1000])

        # Appel au LLM avec retry et rate limiting
        max_tokens = self.config.get("llm", {}).get("max_tokens", 500)
        content = self._call_llm_with_retry(prompt, max_tokens)
        if content is None:
            logger.warning("LLM a retourné None. Utilisation de la valeur par défaut.")
            default_level = self.config.get("sensitivity_classification", {}).get(
                "default_level", "interne"
            )
            return str(default_level)

        # Extraire uniquement la première ligne (ignore les explications supplémentaires)
        # Le LLM retourne souvent: "interne\n\nexplication: ..."
        # On ne garde que le premier mot de la première ligne non-vide
        first_line = content.strip().split('\n')[0].strip().lower()

        # Extraire le premier mot (au cas où il y aurait du texte sur la même ligne)
        classification: str = first_line.split()[0] if first_line.split() else ""

        # Validation: la réponse DOIT être l'une des valeurs attendues
        valid_levels = ["public", "interne", "confidentiel", "secret"]
        if classification in valid_levels:
            logger.debug(f"Classification LLM: '{classification}'")
            return classification
        else:
            logger.warning(
                f"Classification LLM invalide: '{classification}' (réponse complète: '{content[:100]}...'). "
                "Utilisation de la valeur par défaut."
            )
            default_level = self.config.get("sensitivity_classification", {}).get(
                "default_level", "interne"
            )
            return str(default_level)

    def _classify_document_type(self, file_path: str) -> str:
        """Classifie le type de document.

        Args:
            file_path: Chemin du fichier source.

        Returns:
            Type de document.
        """
        # Note: La classification par LLM du type de document nécessiterait
        # le contenu du document, pas juste le nom de fichier.
        # Pour le MVP, on garde la classification par nom de fichier
        # qui est rapide et suffisante dans la plupart des cas.

        # MVP: classification par nom de fichier
        file_lower = file_path.lower()

        if "contrat" in file_lower:
            return "contrat"
        elif "audit" in file_lower:
            return "rapport_audit"
        elif "politique" in file_lower:
            return "politique_interne"
        elif "procedure" in file_lower:
            return "procedure"
        else:
            return "autre"

    def _extract_regulatory_tags(self, text: str) -> list[str]:
        """Extrait les tags réglementaires (placeholder).

        Args:
            text: Texte du chunk.

        Returns:
            Liste de tags réglementaires.
        """
        tags = []
        text_lower = text.lower()

        # Détection RGPD
        if "rgpd" in text_lower or "gdpr" in text_lower:
            tags.append("RGPD")

        # Détection ISO27001
        if "iso 27001" in text_lower or "iso27001" in text_lower:
            tags.append("ISO27001")

        # Détection SOC2
        if "soc2" in text_lower or "soc 2" in text_lower:
            tags.append("SOC2")

        return tags

    def _save_enriched_chunks(
        self,
        enriched_chunks: list[dict[str, Any]],
        output_config: dict[str, Any],
    ) -> None:
        """Sauvegarde les chunks enrichis dans des fichiers JSON.

        Parameters
        ----------
        enriched_chunks : list[dict[str, Any]]
            Liste des chunks enrichis à sauvegarder.
        output_config : dict[str, Any]
            Configuration de sauvegarde depuis config/04_enrichment.yaml > output.

        Notes
        -----
        Si group_by_document est True, crée un fichier JSON par document source.
        Sinon, crée un seul fichier JSON contenant tous les chunks.
        """
        try:
            # Répertoire de destination
            enriched_dir = Path(
                output_config.get("enriched_dir", "./data/output/enriched")
            )
            enriched_dir.mkdir(parents=True, exist_ok=True)

            # Grouper par document source si configuré
            if output_config.get("group_by_document", True):
                self._save_by_document(enriched_chunks, enriched_dir, output_config)
            else:
                self._save_all_chunks(enriched_chunks, enriched_dir, output_config)

        except Exception as e:
            logger.error(
                f"Erreur sauvegarde chunks enrichis: {e}", exc_info=True
            )
            # Ne pas interrompre le pipeline en cas d'erreur de sauvegarde

    def _save_by_document(
        self,
        enriched_chunks: list[dict[str, Any]],
        enriched_dir: Path,
        output_config: dict[str, Any],
    ) -> None:
        """Sauvegarde les chunks enrichis en les groupant par document source.

        Parameters
        ----------
        enriched_chunks : list[dict[str, Any]]
            Liste des chunks enrichis.
        enriched_dir : Path
            Répertoire de destination.
        output_config : dict[str, Any]
            Configuration de sauvegarde.
        """
        # Grouper les chunks par document source
        chunks_by_document: dict[str, list[dict[str, Any]]] = {}
        for chunk in enriched_chunks:
            source_file = chunk.get("source_file", "unknown")
            if source_file not in chunks_by_document:
                chunks_by_document[source_file] = []
            chunks_by_document[source_file].append(chunk)

        # Sauvegarder un fichier JSON par document
        for source_file, chunks in chunks_by_document.items():
            # Nom de fichier basé sur le document source
            source_path = Path(source_file)
            base_name = source_path.stem

            # Ajouter timestamp si configuré
            if output_config.get("add_timestamp", True):
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{base_name}_enriched_{timestamp_str}.json"
            else:
                filename = f"{base_name}_enriched.json"

            file_path = enriched_dir / filename

            # Préparer le contenu à sauvegarder
            content = {
                "source_document": source_file,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "chunks_count": len(chunks),
                "chunks": chunks if output_config.get("include_metadata", True) else [
                    {k: v for k, v in chunk.items() if k not in ["metadata"]}
                    for chunk in chunks
                ],
            }

            # Écriture du fichier JSON
            indent = 2 if output_config.get("pretty_print", True) else None
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=indent)

            logger.info(f"💾 Chunks enrichis sauvegardés: {filename} ({len(chunks)} chunks)")

    def _save_all_chunks(
        self,
        enriched_chunks: list[dict[str, Any]],
        enriched_dir: Path,
        output_config: dict[str, Any],
    ) -> None:
        """Sauvegarde tous les chunks enrichis dans un seul fichier JSON.

        Parameters
        ----------
        enriched_chunks : list[dict[str, Any]]
            Liste des chunks enrichis.
        enriched_dir : Path
            Répertoire de destination.
        output_config : dict[str, Any]
            Configuration de sauvegarde.
        """
        # Ajouter timestamp si configuré
        if output_config.get("add_timestamp", True):
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"enriched_chunks_{timestamp_str}.json"
        else:
            filename = "enriched_chunks.json"

        file_path = enriched_dir / filename

        # Préparer le contenu à sauvegarder
        content = {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "chunks_count": len(enriched_chunks),
            "chunks": enriched_chunks if output_config.get("include_metadata", True) else [
                {k: v for k, v in chunk.items() if k not in ["metadata"]}
                for chunk in enriched_chunks
            ],
        }

        # Écriture du fichier JSON
        indent = 2 if output_config.get("pretty_print", True) else None
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=indent)

        logger.info(f"💾 Tous les chunks enrichis sauvegardés: {filename} ({len(enriched_chunks)} chunks)")
