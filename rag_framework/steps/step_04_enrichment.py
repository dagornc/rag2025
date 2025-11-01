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

            # Génération de résumé au niveau document si configuré
            document_summaries = {}
            if self.config.get("summary_generation", {}).get("document_level", False):
                document_summaries = self._generate_document_summaries(chunks)

            for chunk in chunks:
                enriched_chunk = chunk.copy()

                # Ajout hash SHA-256
                if self.config.get("compliance_metadata", {}).get("include_hash", True):
                    enriched_chunk["content_hash"] = self._compute_hash(chunk["text"])

                # Timestamp immuable
                enriched_chunk["processed_at"] = datetime.now(timezone.utc).isoformat()

                # Classification de sensibilité
                enriched_chunk["sensitivity"] = self._classify_sensitivity(
                    chunk["text"]
                )

                # Type de document (avec LLM si disponible)
                enriched_chunk["document_type"] = self._classify_document_type(
                    chunk["text"], chunk["source_file"]
                )

                # Tags réglementaires (avec LLM si disponible)
                enriched_chunk["regulatory_tags"] = self._extract_regulatory_tags(
                    chunk["text"]
                )

                # Extraction de tags (avec LLM si disponible)
                if self.config.get("tags_extraction", {}).get("enabled", False):
                    enriched_chunk["tags"] = self._extract_tags(chunk["text"])

                # Génération de résumé au niveau chunk si configuré
                if self.config.get("summary_generation", {}).get("chunk_level", False):
                    enriched_chunk["summary"] = self._generate_chunk_summary(
                        chunk["text"]
                    )

                # Ajout du résumé document si disponible
                source_file = chunk.get("source_file")
                if source_file and source_file in document_summaries:
                    enriched_chunk["document_summary"] = document_summaries[source_file]

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

    def _call_llm_with_retry(self, prompt: str, max_tokens: int = 500) -> Optional[str]:
        """Appelle le LLM avec gestion du rate limiting et retry.

        Parameters
        ----------
        prompt : str
            Prompt à envoyer au LLM.
        max_tokens : int
            Nombre maximum de tokens pour la réponse.

        Returns:
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
                            f"Rate limit atteint (tentative "
                            f"{attempt + 1}/{max_retries + 1}). "
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
        prompt_template = (
            self.config.get("llm", {})
            .get("prompts", {})
            .get(
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

        # Extraire uniquement la première ligne
        # (ignore les explications supplémentaires)
        # Le LLM retourne souvent: "interne\n\nexplication: ..."
        # On ne garde que le premier mot de la première ligne non-vide
        first_line = content.strip().split("\n")[0].strip().lower()

        # Extraire le premier mot (au cas où il y aurait du texte sur la même ligne)
        classification: str = first_line.split()[0] if first_line.split() else ""

        # Validation: la réponse DOIT être l'une des valeurs attendues
        valid_levels = ["public", "interne", "confidentiel", "secret"]
        if classification in valid_levels:
            logger.debug(f"Classification LLM: '{classification}'")
            return classification
        else:
            logger.warning(
                f"Classification LLM invalide: '{classification}' "
                f"(réponse complète: '{content[:100]}...'). "
                "Utilisation de la valeur par défaut."
            )
            default_level = self.config.get("sensitivity_classification", {}).get(
                "default_level", "interne"
            )
            return str(default_level)

    def _classify_document_type(self, text: str, file_path: str) -> str:
        """Classifie le type de document.

        Args:
            text: Contenu textuel du chunk.
            file_path: Chemin du fichier source.

        Returns:
            Type de document.
        """
        # Si LLM activé et configuration document_classification activée, utiliser LLM
        if self.llm_client is not None and self.config.get(
            "document_classification", {}
        ).get("enabled", False):
            try:
                return self._classify_document_type_with_llm(text)
            except Exception as e:
                logger.warning(
                    f"Erreur classification LLM type document: {e}. "
                    "Fallback sur nom de fichier."
                )

        # Fallback: classification par nom de fichier
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

    def _classify_document_type_with_llm(self, text: str) -> str:
        """Classifie le type de document avec LLM.

        Parameters
        ----------
        text : str
            Texte du document à classifier.

        Returns:
        -------
        str
            Type de document (contrat, rapport_audit, politique_interne, etc.).
        """
        # Récupération du prompt depuis la configuration
        prompt_template = (
            self.config.get("llm", {})
            .get("prompts", {})
            .get(
                "document_type_classification",
                # Prompt par défaut si non configuré
                """Identifie le type de document parmi les catégories suivantes.
Réponds UNIQUEMENT par l'une de ces catégories:
contrat, rapport_audit, politique_interne, procedure,
rapport_conformite, directive

Document:
{text}

Type de document:""",
            )
        )

        # Substitution du placeholder {text} (limité à 1000 chars)
        prompt = prompt_template.format(text=text[:1000])

        # Appel au LLM
        max_tokens = self.config.get("llm", {}).get("max_tokens", 500)
        content = self._call_llm_with_retry(prompt, max_tokens)
        if content is None:
            return "autre"

        # Extraire la première ligne
        classification: str = content.strip().split("\n")[0].strip().lower()

        # Validation
        valid_types = [
            "contrat",
            "rapport_audit",
            "politique_interne",
            "procedure",
            "rapport_conformite",
            "directive",
            "autre",
        ]
        if classification in valid_types:
            logger.debug(f"Classification type document LLM: '{classification}'")
            return classification
        else:
            logger.warning(
                f"Classification type document LLM invalide: '{classification}'. "
                "Utilisation de 'autre'."
            )
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

        Notes:
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
            logger.error(f"Erreur sauvegarde chunks enrichis: {e}", exc_info=True)
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
                timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                filename = f"{base_name}_enriched_{timestamp_str}.json"
            else:
                filename = f"{base_name}_enriched.json"

            file_path = enriched_dir / filename

            # Préparer le contenu à sauvegarder
            content = {
                "source_document": source_file,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "chunks_count": len(chunks),
                "chunks": chunks
                if output_config.get("include_metadata", True)
                else [
                    {k: v for k, v in chunk.items() if k not in ["metadata"]}
                    for chunk in chunks
                ],
            }

            # Écriture du fichier JSON
            indent = 2 if output_config.get("pretty_print", True) else None
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=indent)

            logger.info(
                f"💾 Chunks enrichis sauvegardés: {filename} ({len(chunks)} chunks)"
            )

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
            timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"enriched_chunks_{timestamp_str}.json"
        else:
            filename = "enriched_chunks.json"

        file_path = enriched_dir / filename

        # Préparer le contenu à sauvegarder
        content = {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "chunks_count": len(enriched_chunks),
            "chunks": enriched_chunks
            if output_config.get("include_metadata", True)
            else [
                {k: v for k, v in chunk.items() if k not in ["metadata"]}
                for chunk in enriched_chunks
            ],
        }

        # Écriture du fichier JSON
        indent = 2 if output_config.get("pretty_print", True) else None
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=indent)

        logger.info(
            f"💾 Tous les chunks enrichis sauvegardés: {filename} "
            f"({len(enriched_chunks)} chunks)"
        )

    def _generate_document_summaries(
        self, chunks: list[dict[str, Any]]
    ) -> dict[str, str]:
        """Génère des résumés au niveau document.

        Parameters
        ----------
        chunks : list[dict[str, Any]]
            Liste de tous les chunks à traiter.

        Returns:
        -------
        dict[str, str]
            Dictionnaire mapping source_file -> résumé du document.
        """
        # Grouper les chunks par document source
        chunks_by_document: dict[str, list[dict[str, Any]]] = {}
        for chunk in chunks:
            source_file = chunk.get("source_file", "unknown")
            if source_file not in chunks_by_document:
                chunks_by_document[source_file] = []
            chunks_by_document[source_file].append(chunk)

        # Générer un résumé pour chaque document
        document_summaries: dict[str, str] = {}
        summary_config = self.config.get("summary_generation", {})

        for source_file, doc_chunks in chunks_by_document.items():
            # Concaténer le texte de tous les chunks du document
            # Limiter à un nombre raisonnable de caractères
            # pour éviter de dépasser les limites du LLM
            full_text = " ".join([chunk.get("text", "") for chunk in doc_chunks])
            max_chars = 5000  # Limite raisonnable pour le contexte LLM
            text_to_summarize = full_text[:max_chars]

            # Générer le résumé
            if self.llm_client is not None:
                try:
                    summary = self._generate_document_summary_with_llm(
                        text_to_summarize
                    )
                    document_summaries[source_file] = summary
                    logger.debug(f"Résumé document généré pour {source_file}")
                except Exception as e:
                    logger.warning(
                        f"Erreur génération résumé LLM pour {source_file}: {e}. "
                        "Utilisation du fallback extractif."
                    )
                    # Fallback extractif
                    summary = self._generate_extractive_summary(
                        text_to_summarize,
                        summary_config.get("extractive_sentences", 3),
                    )
                    document_summaries[source_file] = summary
            else:
                # Pas de LLM, utiliser directement le fallback extractif
                summary = self._generate_extractive_summary(
                    text_to_summarize,
                    summary_config.get("extractive_sentences", 3),
                )
                document_summaries[source_file] = summary

        logger.info(f"Résumés documents générés: {len(document_summaries)} documents")
        return document_summaries

    def _generate_document_summary_with_llm(self, text: str) -> str:
        """Génère un résumé de document avec LLM.

        Parameters
        ----------
        text : str
            Texte du document à résumer.

        Returns:
        -------
        str
            Résumé du document (2-5 phrases).
        """
        # Récupération du prompt depuis la configuration
        prompt_template = (
            self.config.get("llm", {})
            .get("prompts", {})
            .get(
                "document_summary",
                # Prompt par défaut si non configuré
                """Génère un résumé concis et informatif du document suivant.

Le résumé doit :
- Capturer les idées principales et les points clés
- Être factuel et objectif
- Faire entre 2 et 5 phrases (100-200 mots maximum)
- Inclure le contexte et l'objectif du document

Document:
{text}

Résumé:""",
            )
        )

        # Substitution du placeholder {text}
        prompt = prompt_template.format(text=text)

        # Appel au LLM
        max_tokens = (
            self.config.get("summary_generation", {}).get("max_length_words", 200) * 2
        )  # Approximation: 1 mot ≈ 2 tokens
        content = self._call_llm_with_retry(prompt, max_tokens)

        if content is None:
            logger.warning(
                "LLM a retourné None pour résumé document. Fallback extractif."
            )
            return self._generate_extractive_summary(text, 3)

        return content.strip()

    def _generate_chunk_summary(self, text: str) -> str:
        """Génère un résumé au niveau chunk.

        Parameters
        ----------
        text : str
            Texte du chunk à résumer.

        Returns:
        -------
        str
            Résumé du chunk (1-2 phrases, 50 mots max).
        """
        # Si LLM activé, utiliser génération intelligente
        if self.llm_client is not None:
            try:
                return self._generate_chunk_summary_with_llm(text)
            except Exception as e:
                logger.warning(
                    f"Erreur génération résumé chunk LLM: {e}. Fallback extractif."
                )
                # Fallback extractif
                return self._generate_extractive_summary(text, 1)

        # Pas de LLM, utiliser fallback extractif
        return self._generate_extractive_summary(text, 1)

    def _generate_chunk_summary_with_llm(self, chunk_text: str) -> str:
        """Génère un résumé de chunk avec LLM.

        Parameters
        ----------
        chunk_text : str
            Texte du chunk à résumer.

        Returns:
        -------
        str
            Résumé du chunk (1-2 phrases).
        """
        # Récupération du prompt depuis la configuration
        prompt_template = (
            self.config.get("llm", {})
            .get("prompts", {})
            .get(
                "chunk_summary",
                # Prompt par défaut si non configuré
                """Génère un résumé très concis de ce fragment de document.

Le résumé doit :
- Tenir en 1-2 phrases maximum (50 mots)
- Capturer l'idée principale du fragment
- Être utile pour la recherche sémantique

Fragment:
{chunk_text}

Résumé:""",
            )
        )

        # Substitution du placeholder
        prompt = prompt_template.format(chunk_text=chunk_text[:1000])

        # Appel au LLM
        max_tokens = (
            self.config.get("summary_generation", {}).get(
                "chunk_summary_length_words", 50
            )
            * 2
        )  # Approximation: 1 mot ≈ 2 tokens
        content = self._call_llm_with_retry(prompt, max_tokens)

        if content is None:
            logger.warning("LLM a retourné None pour résumé chunk. Fallback extractif.")
            return self._generate_extractive_summary(chunk_text, 1)

        return content.strip()

    def _generate_extractive_summary(self, text: str, num_sentences: int) -> str:
        """Génère un résumé extractif simple (premières phrases).

        Parameters
        ----------
        text : str
            Texte à résumer.
        num_sentences : int
            Nombre de phrases à extraire.

        Returns:
        -------
        str
            Résumé extractif (premières phrases du texte).
        """
        # Découper en phrases (basique)
        sentences = text.replace("\n", " ").split(". ")
        selected_sentences = sentences[:num_sentences]
        summary = ". ".join(selected_sentences)

        # Assurer qu'il y a un point final
        if summary and not summary.endswith("."):
            summary += "."

        return summary

    def _extract_tags(self, text: str) -> list[str]:
        """Extrait des tags thématiques du texte.

        Parameters
        ----------
        text : str
            Texte à analyser.

        Returns:
        -------
        list[str]
            Liste de tags extraits.
        """
        tags_config = self.config.get("tags_extraction", {})
        all_tags: list[str] = []

        # 1. Utiliser LLM si activé
        if tags_config.get("use_llm", True) and self.llm_client is not None:
            try:
                llm_tags = self._extract_tags_with_llm(text)
                all_tags.extend(llm_tags)
                logger.debug(f"Tags LLM extraits: {llm_tags}")
            except Exception as e:
                logger.warning(f"Erreur extraction tags LLM: {e}")

        # 2. Utiliser mots-clés (TF-IDF basique) si activé
        if tags_config.get("use_keywords", True):
            keyword_tags = self._extract_tags_by_keywords(text)
            all_tags.extend(keyword_tags)
            logger.debug(f"Tags mots-clés extraits: {keyword_tags}")

        # 3. Utiliser tags prédéfinis si détectés dans le texte
        predefined_tags = self._extract_predefined_tags(text)
        all_tags.extend(predefined_tags)
        logger.debug(f"Tags prédéfinis détectés: {predefined_tags}")

        # Normalisation et filtrage
        if tags_config.get("normalize_tags", True):
            all_tags = [self._normalize_tag(tag) for tag in all_tags]

        # Suppression des doublons
        if tags_config.get("remove_duplicates", True):
            all_tags = list(dict.fromkeys(all_tags))  # Préserve l'ordre

        # Filtrage par longueur
        min_length = tags_config.get("min_tag_length", 3)
        max_length = tags_config.get("max_tag_length", 50)
        all_tags = [tag for tag in all_tags if min_length <= len(tag) <= max_length]

        # Limiter le nombre de tags
        max_tags = tags_config.get("max_tags", 10)
        min_tags = tags_config.get("min_tags", 3)

        final_tags = all_tags[:max_tags]

        # Si pas assez de tags, compléter avec des tags par défaut
        if len(final_tags) < min_tags:
            logger.warning(
                f"Seulement {len(final_tags)} tags extraits (minimum: {min_tags}). "
                "Ajout de tags par défaut."
            )
            default_tags = ["document", "conformité", "analyse"]
            final_tags.extend(default_tags[: min_tags - len(final_tags)])

        return final_tags

    def _extract_tags_with_llm(self, text: str) -> list[str]:
        """Extrait des tags avec LLM.

        Parameters
        ----------
        text : str
            Texte à analyser.

        Returns:
        -------
        list[str]
            Liste de tags extraits par le LLM.
        """
        # Récupération du prompt depuis la configuration
        prompt_template = (
            self.config.get("llm", {})
            .get("prompts", {})
            .get(
                "tags_extraction",
                # Prompt par défaut si non configuré
                """Extrait des tags pertinents et structurés du document suivant.

Les tags doivent couvrir :
- Thématiques principales (ex: sécurité, RGPD, audit, conformité)
- Technologies mentionnées
- Domaines d'application

Règles :
- Maximum 10 tags
- Tags en français
- Tags courts (1-3 mots)
- Éviter les mots trop génériques

Document:
{text}

Réponds au format JSON avec une liste de tags:
{{"tags": ["tag1", "tag2", "tag3", ...]}}""",
            )
        )

        # Substitution du placeholder
        prompt = prompt_template.format(text=text[:1000])

        # Appel au LLM
        max_tokens = self.config.get("llm", {}).get("max_tokens", 500)
        content = self._call_llm_with_retry(prompt, max_tokens)

        if content is None:
            return []

        # Parser la réponse JSON
        try:
            # Extraire le JSON de la réponse (peut contenir du texte avant/après)
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                parsed = json.loads(json_str)
                tags = parsed.get("tags", [])
                return tags if isinstance(tags, list) else []
            else:
                logger.warning(f"Pas de JSON trouvé dans réponse LLM: {content[:100]}")
                return []
        except json.JSONDecodeError as e:
            logger.warning(
                f"Erreur parsing JSON tags LLM: {e}. Réponse: {content[:100]}"
            )
            return []

    def _extract_tags_by_keywords(self, text: str) -> list[str]:
        """Extrait des tags basés sur des mots-clés fréquents (TF-IDF basique).

        Parameters
        ----------
        text : str
            Texte à analyser.

        Returns:
        -------
        list[str]
            Liste de tags basés sur mots-clés.
        """
        # Implémentation basique: mots fréquents de plus de 4 caractères
        # Dans une vraie implémentation, utiliser TF-IDF avec sklearn
        text_lower = text.lower()

        # Mots à exclure (stopwords basiques)
        stopwords = {
            "le",
            "la",
            "les",
            "un",
            "une",
            "des",
            "de",
            "du",
            "et",
            "ou",
            "dans",
            "pour",
            "par",
            "avec",
            "sans",
            "sur",
            "sous",
            "est",
            "sont",
            "sera",
            "ont",
            "peut",
            "doit",
            "faire",
            "être",
            "avoir",
            "cette",
            "ces",
            "son",
            "sa",
            "ses",
            "leur",
            "leurs",
            "tout",
            "toute",
            "tous",
            "toutes",
            "plus",
        }

        # Extraire les mots
        words = text_lower.split()
        word_freq: dict[str, int] = {}

        for word in words:
            # Nettoyer le mot (enlever ponctuation basique)
            word_clean = word.strip(".,;:!?()[]{}\"'-")
            if (
                len(word_clean) >= 4
                and word_clean not in stopwords
                and word_clean.isalpha()
            ):
                word_freq[word_clean] = word_freq.get(word_clean, 0) + 1

        # Trier par fréquence et prendre les 5 plus fréquents
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        tags = [word for word, _freq in sorted_words[:5]]

        return tags

    def _extract_predefined_tags(self, text: str) -> list[str]:
        """Extrait des tags prédéfinis depuis la configuration.

        Parameters
        ----------
        text : str
            Texte à analyser.

        Returns:
        -------
        list[str]
            Liste de tags prédéfinis détectés dans le texte.
        """
        text_lower = text.lower()
        detected_tags: list[str] = []

        predefined = self.config.get("tags_extraction", {}).get("predefined_tags", {})

        for _category, tags_list in predefined.items():
            for tag in tags_list:
                if tag.lower() in text_lower:
                    detected_tags.append(tag)

        return detected_tags

    def _normalize_tag(self, tag: str) -> str:
        """Normalise un tag (minuscules, suppression accents).

        Parameters
        ----------
        tag : str
            Tag à normaliser.

        Returns:
        -------
        str
            Tag normalisé.
        """
        # Conversion en minuscules
        normalized = tag.lower().strip()

        # Suppression des accents basique (pour une vraie impl, utiliser unidecode)
        accent_map = {
            "à": "a",
            "â": "a",
            "ä": "a",
            "á": "a",
            "è": "e",
            "é": "e",
            "ê": "e",
            "ë": "e",
            "î": "i",
            "ï": "i",
            "í": "i",
            "ô": "o",
            "ö": "o",
            "ó": "o",
            "ù": "u",
            "û": "u",
            "ü": "u",
            "ú": "u",
            "ç": "c",
        }

        for accented, base in accent_map.items():
            normalized = normalized.replace(accented, base)

        return normalized
