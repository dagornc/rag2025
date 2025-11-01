"""Étape 3 : Découpage de documents en chunks."""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from rag_framework.exceptions import StepExecutionError, ValidationError
from rag_framework.steps.base_step import BaseStep
from rag_framework.types import StepData
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class ChunkingStep(BaseStep):
    """Étape 3 : Découpage de documents en chunks."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise l'étape de chunking.

        Parameters
        ----------
        config : dict[str, Any]
            Configuration de l'étape.
        """
        super().__init__(config)

        # Configuration de la sauvegarde des chunks
        self.output_config = config.get("output", {"save_chunks": False})

        # Configuration LLM pour stratégie llm_guided
        self.llm_config = config.get("llm", {"enabled": False})

        # Initialisation du LLM si la stratégie est llm_guided
        self.llm_client = None
        if (
            config.get("strategy") == "llm_guided"
            and self.llm_config.get("enabled", False)
        ):
            self._initialize_llm()

        # Initialisation embeddings pour stratégie semantic
        self.embeddings_model = None
        if config.get("strategy") == "semantic":
            self._initialize_embeddings()

    def _initialize_llm(self) -> None:
        """Initialise le client LLM pour stratégie llm_guided."""
        try:
            from rag_framework.config import get_llm_client, load_config

            global_config = load_config()
            provider = self.llm_config.get("provider")
            model = self.llm_config.get("model")

            if not provider or not model:
                logger.warning(
                    "LLM provider ou model non configuré pour llm_guided, "
                    "fallback vers recursive"
                )
                return

            self.llm_client = get_llm_client(
                provider_name=provider,
                model=model,
                temperature=self.llm_config.get("temperature", 0.0),
                global_config=global_config,
            )
            logger.info(f"LLM initialisé pour chunking guidé: {provider}/{model}")

        except Exception as e:
            logger.error(
                f"Erreur initialisation LLM pour chunking: {e}", exc_info=True
            )
            self.llm_client = None

    def _initialize_embeddings(self) -> None:
        """Initialise le modèle d'embeddings pour stratégie semantic."""
        try:
            config = self.config.get("semantic", {})
            provider = config.get("provider", "openai")
            model = config.get("model", "text-embedding-3-large")

            # Import dynamique selon le provider
            if provider == "sentence-transformers":
                from sentence_transformers import SentenceTransformer

                self.embeddings_model = SentenceTransformer(model)
                logger.info(f"Sentence Transformers chargé: {model}")

            elif provider in ["openai", "mistral_ai"]:
                from rag_framework.config import get_llm_client, load_config

                global_config = load_config()
                self.embeddings_model = get_llm_client(
                    provider_name=provider,
                    model=model,
                    temperature=0.0,
                    global_config=global_config,
                )
                logger.info(f"Embeddings API initialisé: {provider}/{model}")

            else:
                logger.warning(
                    f"Provider embeddings non supporté: {provider}, "
                    f"fallback vers recursive"
                )

        except Exception as e:
            logger.error(
                f"Erreur initialisation embeddings: {e}", exc_info=True
            )
            self.embeddings_model = None

    def validate_config(self) -> None:
        """Valide la configuration de l'étape."""
        if "strategy" not in self.config:
            raise ValidationError(
                "Clé 'strategy' manquante dans la configuration",
                details={"step": "ChunkingStep"},
            )

        strategy = self.config["strategy"]
        if strategy not in ["recursive", "semantic", "fixed", "llm_guided"]:
            raise ValidationError(
                f"Stratégie inconnue: {strategy}",
                details={"step": "ChunkingStep", "strategy": strategy},
            )

    def execute(self, data: StepData) -> StepData:
        """Découpe les documents en chunks selon la stratégie configurée.

        Args:
            data: Données contenant 'extracted_documents'.

        Returns:
            Données avec 'chunks' ajouté.

        Raises:
            StepExecutionError: En cas d'erreur durant le chunking.
        """
        try:
            documents = data.get("extracted_documents", [])

            if not documents:
                logger.warning("Aucun document à découper")
                data["chunks"] = []
                return data

            strategy = self.config["strategy"]
            all_chunks = []

            for doc in documents:
                text = doc["text"]

                if strategy == "recursive":
                    chunks = self._chunk_recursive(text)
                elif strategy == "fixed":
                    chunks = self._chunk_fixed(text)
                elif strategy == "semantic":
                    chunks = self._chunk_semantic(text)
                elif strategy == "llm_guided":
                    chunks = self._chunk_llm_guided(text)
                else:
                    # Fallback vers recursive
                    logger.warning(
                        f"Stratégie {strategy} non gérée, fallback recursive"
                    )
                    chunks = self._chunk_recursive(text)

                # Ajouter métadonnées à chaque chunk
                for idx, chunk_text in enumerate(chunks):
                    all_chunks.append(
                        {
                            "text": chunk_text,
                            "source_file": doc.get("file_path") or doc.get("source_file", "unknown"),
                            "chunk_index": idx,
                            "total_chunks": len(chunks),
                            "chunking_strategy": strategy,
                        }
                    )

            # Validation des chunks (min/max size)
            validation_config = self.config.get("validation", {})
            min_size = validation_config.get("min_chunk_size", 50)
            max_size = validation_config.get("max_chunk_size", 5000)
            reject_empty = validation_config.get("reject_empty_chunks", True)

            valid_chunks = []
            rejected_count = 0

            for chunk in all_chunks:
                chunk_text = chunk["text"]
                chunk_len = len(chunk_text)

                # Vérifier si le chunk est vide
                if reject_empty and len(chunk_text.strip()) == 0:
                    rejected_count += 1
                    continue

                # Vérifier taille min/max
                if chunk_len < min_size or chunk_len > max_size:
                    rejected_count += 1
                    logger.debug(
                        f"Chunk rejeté (len={chunk_len}, "
                        f"min={min_size}, max={max_size})"
                    )
                    continue

                valid_chunks.append(chunk)

            # Log des chunks rejetés
            if rejected_count > 0:
                logger.warning(
                    f"Chunking: {rejected_count} chunks rejetés (hors limites)"
                )

            all_chunks = valid_chunks

            data["chunks"] = all_chunks
            logger.info(
                f"Chunking ({strategy}): {len(all_chunks)} chunks créés "
                f"depuis {len(documents)} documents"
            )

            # Sauvegarde des chunks en JSON
            if self.output_config.get("save_chunks", False):
                self._save_chunks_json(all_chunks, documents)

            return data

        except Exception as e:
            raise StepExecutionError(
                step_name="ChunkingStep",
                message=f"Erreur lors du chunking: {e!s}",
                details={"error": str(e)},
            ) from e

    def _chunk_recursive(self, text: str) -> list[str]:
        """Découpe récursif avec séparateurs hiérarchiques (LangChain).

        Utilise RecursiveCharacterTextSplitter de LangChain pour découper
        intelligemment en respectant la hiérarchie des séparateurs.

        Args:
            text: Texte à découper.

        Returns:
            Liste de chunks.
        """
        config = self.config.get("recursive", {})
        chunk_size = config.get("chunk_size", 1000)
        chunk_overlap = config.get("chunk_overlap", 200)
        separators = config.get(
            "separators", ["\n\n\n", "\n\n", "\n", " ", ""]
        )

        try:
            # Import LangChain RecursiveCharacterTextSplitter
            # Note: Depuis LangChain 1.0+, les text splitters sont dans langchain-text-splitters
            try:
                from langchain_text_splitters import RecursiveCharacterTextSplitter
            except ImportError:
                # Fallback pour anciennes versions de LangChain
                from langchain.text_splitter import RecursiveCharacterTextSplitter

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=separators,
                length_function=len,
                keep_separator=config.get("keep_separator", True),
            )

            chunks = text_splitter.split_text(text)
            logger.debug(
                f"Recursive chunking (LangChain): {len(chunks)} chunks "
                f"(size={chunk_size}, overlap={chunk_overlap})"
            )
            return chunks

        except ImportError:
            # Fallback vers implémentation simple si LangChain non disponible
            logger.info(
                "LangChain non disponible, utilisation implémentation simple "
                "(qualité identique, pas d'impact)"
            )
            return self._chunk_recursive_simple(text, chunk_size, chunk_overlap)

    def _chunk_recursive_simple(
        self, text: str, chunk_size: int, chunk_overlap: int
    ) -> list[str]:
        """Implémentation simple du chunking recursive (fallback).

        Args:
            text: Texte à découper.
            chunk_size: Taille cible des chunks.
            chunk_overlap: Chevauchement entre chunks.

        Returns:
            Liste de chunks.
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - chunk_overlap

        # Filtrer chunks trop petits
        min_size = self.config.get("recursive", {}).get("min_chunk_size", 50)
        return [c for c in chunks if len(c) >= min_size]

    def _chunk_fixed(self, text: str) -> list[str]:
        """Découpe à taille fixe avec overlap.

        Args:
            text: Texte à découper.

        Returns:
            Liste de chunks.
        """
        config = self.config.get("fixed", {})
        chunk_size = config.get("chunk_size", 1000)
        overlap = config.get("overlap", 200)

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap

        logger.debug(
            f"Fixed chunking: {len(chunks)} chunks "
            f"(size={chunk_size}, overlap={overlap})"
        )
        return chunks

    def _chunk_semantic(self, text: str) -> list[str]:
        """Découpage basé sur la similarité sémantique.

        Découpe le texte en phrases puis regroupe les phrases similaires
        pour former des chunks cohérents sémantiquement.

        Args:
            text: Texte à découper.

        Returns:
            Liste de chunks.
        """
        config = self.config.get("semantic", {})
        min_chunk_size = config.get("min_chunk_size", 500)
        max_chunk_size = config.get("max_chunk_size", 2000)
        similarity_threshold = config.get("similarity_threshold", 0.75)

        # Vérifier si le modèle d'embeddings est disponible
        if not self.embeddings_model:
            logger.warning(
                "Modèle d'embeddings non disponible pour semantic chunking, "
                "fallback vers recursive"
            )
            return self._chunk_recursive(text)

        try:
            # Découper le texte en phrases
            sentences = self._split_into_sentences(text)

            if len(sentences) == 0:
                return [text]

            # Calculer les embeddings de chaque phrase
            embeddings = self._compute_embeddings(sentences)

            # Regrouper les phrases par similarité
            chunks = self._group_by_similarity(
                sentences,
                embeddings,
                similarity_threshold,
                min_chunk_size,
                max_chunk_size,
            )

            logger.debug(
                f"Semantic chunking: {len(chunks)} chunks "
                f"(threshold={similarity_threshold})"
            )
            return chunks

        except Exception as e:
            logger.error(
                f"Erreur semantic chunking: {e}, fallback recursive",
                exc_info=True,
            )
            return self._chunk_recursive(text)

    def _chunk_llm_guided(self, text: str) -> list[str]:
        """Découpage guidé par LLM.

        Utilise un LLM pour analyser le texte et déterminer les meilleurs
        points de découpage en fonction du contexte sémantique.

        Args:
            text: Texte à découper.

        Returns:
            Liste de chunks.
        """
        # Vérifier si le LLM est disponible
        if not self.llm_client:
            logger.warning(
                "Client LLM non disponible pour llm_guided chunking, "
                "fallback vers recursive"
            )
            return self._chunk_recursive(text)

        try:
            # Si le texte est trop long, le découper d'abord grossièrement
            max_llm_input = 8000  # Limite pour analyse LLM
            if len(text) > max_llm_input:
                # Découpage préliminaire grossier
                preliminary_chunks = self._chunk_fixed(text)
                total_preliminary = len(preliminary_chunks)

                logger.info(
                    f"Texte trop long ({len(text)} chars) pour analyse LLM complète. "
                    f"Découpage en {total_preliminary} chunks préliminaires pour traitement."
                )

                # Appliquer LLM à chaque chunk préliminaire avec progression
                final_chunks = []
                for idx, prelim_chunk in enumerate(preliminary_chunks, 1):
                    logger.info(
                        f"📊 Analyse LLM du chunk {idx}/{total_preliminary} "
                        f"({len(prelim_chunk)} chars)..."
                    )
                    sub_chunks = self._analyze_chunk_with_llm(prelim_chunk)
                    final_chunks.extend(sub_chunks)
                    logger.info(
                        f"✓ Chunk {idx}/{total_preliminary} analysé → "
                        f"{len(sub_chunks)} sous-chunks créés"
                    )

                logger.info(
                    f"✅ Analyse LLM terminée : {total_preliminary} chunks → "
                    f"{len(final_chunks)} chunks finaux"
                )
                return final_chunks
            else:
                return self._analyze_chunk_with_llm(text)

        except Exception as e:
            logger.error(
                f"Erreur llm_guided chunking: {e}, fallback recursive",
                exc_info=True,
            )
            return self._chunk_recursive(text)

    def _call_llm_with_retry(self, prompt: str) -> Optional[str]:
        """Appelle le LLM avec gestion du rate limiting et retry.

        Parameters
        ----------
        prompt : str
            Prompt à envoyer au LLM.

        Returns
        -------
        Optional[str]
            Réponse du LLM, ou None en cas d'échec après tous les retries.
        """
        assert self.llm_client is not None

        # Configuration du rate limiting
        rate_config = self.llm_config.get("rate_limiting", {})
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
                    max_tokens=self.llm_config.get("max_tokens", 1000),
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
                            f"⏳ Rate limit atteint (tentative {attempt + 1}/{max_retries + 1}). "
                            f"Nouvelle tentative dans {delay}s..."
                        )
                        time.sleep(delay)
                        logger.info(f"🔄 Retry tentative {attempt + 2}/{max_retries + 1}...")
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

    def _analyze_chunk_with_llm(self, text: str) -> list[str]:
        """Analyse un texte avec le LLM pour déterminer les découpes.

        Args:
            text: Texte à analyser.

        Returns:
            Liste de chunks.
        """
        # Récupérer le prompt configuré
        prompts = self.llm_config.get("prompts", {})
        prompt_template = prompts.get("chunk_boundary_analysis", "")

        if not prompt_template:
            logger.warning("Prompt chunk_boundary_analysis manquant")
            return self._chunk_recursive(text)

        # Remplacer {text} par le texte réel
        prompt = prompt_template.replace("{text}", text[:4000])  # Limiter

        try:
            # Appeler le LLM avec retry et rate limiting
            content = self._call_llm_with_retry(prompt)

            if content is None:
                logger.warning("LLM a retourné None, fallback recursive")
                return self._chunk_recursive(text)

            # Logger la longueur de la réponse
            logger.debug(f"Réponse LLM reçue: {len(content)} caractères")

            # Parser la réponse JSON pour extraire les boundaries
            boundaries = self._parse_llm_boundaries(content)

            if not boundaries:
                logger.warning("Pas de boundaries trouvées, fallback recursive")
                logger.debug(f"Réponse LLM complète:\n{content}")
                return self._chunk_recursive(text)

            # Découper le texte selon les boundaries
            chunks = []
            prev_pos = 0
            for pos in sorted(boundaries):
                if 0 < pos < len(text):
                    chunks.append(text[prev_pos:pos])
                    prev_pos = pos

            # Ajouter le dernier chunk
            if prev_pos < len(text):
                chunks.append(text[prev_pos:])

            logger.debug(f"LLM guided chunking: {len(chunks)} chunks")
            return [c for c in chunks if len(c) > 0]

        except Exception as e:
            logger.error(f"Erreur analyse LLM: {e}", exc_info=True)
            return self._chunk_recursive(text)

    def _parse_llm_boundaries(self, response: str) -> list[int]:
        """Parse la réponse du LLM pour extraire les positions de découpage.

        Args:
            response: Réponse du LLM (format JSON attendu).

        Returns:
            Liste de positions (indices de caractères).
        """
        try:
            import json

            # Logger la réponse brute pour debug (tronquée si trop longue)
            logger.debug(f"Réponse LLM brute (200 premiers chars): {response[:200]}")

            # Prétraitement : Extraire le JSON des code blocks markdown si présent
            # Format : ```json\n{...}\n``` ou ```\n{...}\n```
            markdown_match = re.search(r'```(?:json)?\s*\n?({.*?})\s*\n?```', response, re.DOTALL)
            if markdown_match:
                response = markdown_match.group(1)
                logger.debug("JSON extrait depuis code block markdown")

            # Stratégie 1: Essayer de parser directement si c'est du JSON pur
            response_stripped = response.strip()
            if response_stripped.startswith("{") and response_stripped.endswith("}"):
                try:
                    data = json.loads(response_stripped)
                    boundaries = data.get("boundaries", [])

                    # Valider et convertir (utiliser la même logique que les autres stratégies)
                    validated = []
                    for b in boundaries:
                        try:
                            if isinstance(b, (int, float)):
                                validated.append(int(b))
                            elif isinstance(b, str):
                                b_stripped = b.strip()
                                if b_stripped:
                                    num = float(b_stripped)
                                    validated.append(int(num))
                        except (ValueError, TypeError):
                            continue  # Ignorer les valeurs invalides

                    if validated or boundaries == []:
                        logger.debug(f"JSON pur trouvé: {len(validated)} boundaries")
                        return validated
                except json.JSONDecodeError:
                    pass  # Continuer avec les autres stratégies

            # Stratégie 2: Extraire le JSON avec regex (peut contenir du texte avant/après)
            json_match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
            if not json_match:
                # Stratégie 3: Chercher un JSON plus complexe (avec nested braces)
                json_match = re.search(r'\{.*?"boundaries".*?\[.*?\].*?\}', response, re.DOTALL)

            if not json_match:
                logger.warning(f"Pas de JSON trouvé dans réponse LLM: {response[:100]}...")
                return []

            json_str = json_match.group()

            # Nettoyer le JSON (supprimer les commentaires et caractères invalides)
            # Supprimer les commentaires de style // et /* */
            json_str = re.sub(r"//.*?$", "", json_str, flags=re.MULTILINE)
            json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)

            # Supprimer les trailing commas (valide en JavaScript mais pas en JSON)
            json_str = re.sub(r",(\s*[}\]])", r"\1", json_str)

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"Erreur parsing JSON: {e}")
                logger.debug(f"JSON problématique: {json_str}")
                return []

            boundaries = data.get("boundaries", [])

            if not isinstance(boundaries, list):
                logger.warning(f"boundaries n'est pas une liste: {type(boundaries)}")
                return []

            # Valider et convertir en entiers
            validated = []
            for b in boundaries:
                try:
                    # Accepter int, float ou string représentant un nombre
                    if isinstance(b, (int, float)):
                        validated.append(int(b))
                    elif isinstance(b, str):
                        # Essayer de convertir la string en nombre
                        b_stripped = b.strip()
                        if b_stripped:
                            # Accepter les nombres entiers et décimaux
                            num = float(b_stripped)
                            validated.append(int(num))
                except (ValueError, TypeError):
                    logger.warning(f"Boundary invalide ignorée: {b}")
                    continue

            logger.debug(f"Boundaries extraites: {len(validated)} positions valides")
            return validated

        except Exception as e:
            logger.error(f"Erreur parsing réponse LLM: {e}")
            logger.debug(f"Réponse complète: {response}")
            return []

    def _split_into_sentences(self, text: str) -> list[str]:
        """Découpe le texte en phrases.

        Args:
            text: Texte à découper.

        Returns:
            Liste de phrases.
        """
        # Regex simple pour découper en phrases (. ! ? suivi d'espace/newline)
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _compute_embeddings(self, sentences: list[str]) -> list[list[float]]:
        """Calcule les embeddings pour chaque phrase.

        Args:
            sentences: Liste de phrases.

        Returns:
            Liste d'embeddings (vecteurs).
        """
        if isinstance(self.embeddings_model, object):
            # Sentence Transformers
            try:
                embeddings = self.embeddings_model.encode(
                    sentences, convert_to_numpy=True
                )
                return embeddings.tolist()
            except Exception:
                pass

        # API-based (OpenAI, Mistral, etc.)
        try:
            embeddings = []
            for sentence in sentences:
                embedding = self.embeddings_model.embed(sentence)
                embeddings.append(embedding)
            return embeddings
        except Exception as e:
            logger.error(f"Erreur calcul embeddings: {e}", exc_info=True)
            return []

    def _group_by_similarity(
        self,
        sentences: list[str],
        embeddings: list[list[float]],
        threshold: float,
        min_size: int,
        max_size: int,
    ) -> list[str]:
        """Regroupe les phrases par similarité cosine.

        Args:
            sentences: Liste de phrases.
            embeddings: Liste d'embeddings.
            threshold: Seuil de similarité (0-1).
            min_size: Taille min d'un chunk (caractères).
            max_size: Taille max d'un chunk (caractères).

        Returns:
            Liste de chunks.
        """
        import numpy as np

        chunks = []
        current_chunk = []
        current_size = 0

        for i, sentence in enumerate(sentences):
            # Ajouter la phrase au chunk courant
            current_chunk.append(sentence)
            current_size += len(sentence)

            # Vérifier si on doit créer un nouveau chunk
            create_new_chunk = False

            # Si taille max atteinte
            if current_size >= max_size:
                create_new_chunk = True

            # Si pas la dernière phrase, calculer similarité avec la suivante
            elif i < len(sentences) - 1:
                emb1 = np.array(embeddings[i])
                emb2 = np.array(embeddings[i + 1])

                # Similarité cosine
                similarity = np.dot(emb1, emb2) / (
                    np.linalg.norm(emb1) * np.linalg.norm(emb2)
                )

                # Si similarité < threshold et taille min atteinte
                if similarity < threshold and current_size >= min_size:
                    create_new_chunk = True

            # Créer le chunk si nécessaire
            if create_new_chunk:
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= min_size:
                    chunks.append(chunk_text)
                current_chunk = []
                current_size = 0

        # Ajouter le dernier chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= min_size:
                chunks.append(chunk_text)

        return chunks

    def _save_chunks_json(
        self, all_chunks: list[dict[str, Any]], documents: list[dict[str, Any]]
    ) -> None:
        """Sauvegarde les chunks en JSON.

        Parameters
        ----------
        all_chunks : list[dict[str, Any]]
            Liste de tous les chunks créés avec leurs métadonnées.
        documents : list[dict[str, Any]]
            Liste des documents sources.

        Examples
        --------
        >>> step = ChunkingStep(config)
        >>> chunks = [{"text": "...", "source_file": "...", ...}, ...]
        >>> documents = [{"file_path": "...", "text": "...", ...}]
        >>> step._save_chunks_json(chunks, documents)
        """
        try:
            # Répertoire de destination
            chunks_dir = Path(
                self.output_config.get("chunks_dir", "./data/output/chunks")
            )
            chunks_dir.mkdir(parents=True, exist_ok=True)

            # Si group_by_document, sauvegarder un fichier JSON par document source
            if self.output_config.get("group_by_document", True):
                # Regrouper les chunks par fichier source
                chunks_by_file: dict[str, list[dict[str, Any]]] = {}
                for chunk in all_chunks:
                    source_file = chunk.get("source_file", "unknown")
                    if source_file not in chunks_by_file:
                        chunks_by_file[source_file] = []
                    chunks_by_file[source_file].append(chunk)

                # Sauvegarder un fichier JSON par document source
                for source_file, chunks in chunks_by_file.items():
                    source_path = Path(source_file)
                    stem = source_path.stem

                    # Nom du fichier JSON
                    if self.output_config.get("add_timestamp", True):
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        json_filename = f"{stem}_{timestamp}_chunks.json"
                    else:
                        json_filename = f"{stem}_chunks.json"

                    json_path = chunks_dir / json_filename

                    # Écriture du fichier JSON
                    indent = 2 if self.output_config.get("pretty_print", True) else None
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(chunks, f, ensure_ascii=False, indent=indent)

                    logger.info(
                        f"💾 Chunks sauvegardés: {json_filename} ({len(chunks)} chunks)"
                    )
                    logger.debug(f"  Chemin complet: {json_path}")

            else:
                # Sauvegarder tous les chunks dans un seul fichier JSON
                if self.output_config.get("add_timestamp", True):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    json_filename = f"chunks_{timestamp}.json"
                else:
                    json_filename = "chunks.json"

                json_path = chunks_dir / json_filename

                # Écriture du fichier JSON
                indent = 2 if self.output_config.get("pretty_print", True) else None
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(all_chunks, f, ensure_ascii=False, indent=indent)

                logger.info(
                    f"💾 Chunks sauvegardés: {json_filename} ({len(all_chunks)} chunks)"
                )
                logger.debug(f"  Chemin complet: {json_path}")

        except Exception as e:
            logger.error(f"Erreur sauvegarde chunks JSON: {e}", exc_info=True)
            # Ne pas interrompre le pipeline en cas d'erreur de sauvegarde
