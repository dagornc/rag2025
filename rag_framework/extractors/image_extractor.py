"""Extracteur pour fichiers images (nécessite VLM)."""

import base64
from pathlib import Path
from typing import Any, ClassVar, Optional

from rag_framework.config import get_llm_client, load_config
from rag_framework.extractors.base import BaseExtractor, ExtractionResult
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class ImageExtractor(BaseExtractor):
    """Extracteur pour fichiers images utilisant VLM.

    Supporte les formats d'images courants : .png, .jpg, .jpeg, .bmp, .gif
    Nécessite un Vision Language Model (VLM) configuré.

    Avantages:
    - Fonctionne sur tous les formats d'images
    - Peut extraire texte de captures d'écran, photos de documents
    - Comprend le contexte visuel

    Limitations:
    - Nécessite un VLM configuré (OpenAI, Anthropic, Ollama)
    - Coûteux pour les services cloud
    - Plus lent qu'OCR traditionnel

    Parameters
    ----------
    config : dict[str, Any]
        Configuration de l'extracteur.
        Clés supportées:
        - provider : str (nom du provider VLM depuis global.yaml)
        - model : str (nom du modèle vision)
        - temperature : float (défaut: 0.0)
        - max_tokens : int (défaut: 2000)
        - prompt : str (prompt personnalisé)
    """

    # Extensions d'images supportées
    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".gif",
    }

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise l'extracteur d'images.

        Parameters
        ----------
        config : dict[str, Any]
            Configuration de l'extracteur.
        """
        super().__init__(config)

        # Chargement de la config globale pour accès aux VLM providers
        self.global_config = load_config()

        # Initialisation du client VLM si configuré
        self.vlm_client: Optional[Any] = None
        if config.get("provider") and config.get("model"):
            try:
                self.vlm_client = get_llm_client(
                    provider_name=config["provider"],
                    model=config["model"],
                    temperature=config.get("temperature", 0.0),
                    global_config=self.global_config,
                )
                provider = config["provider"]
                model = config["model"]
                logger.info(f"Image Extractor initialisé: {provider}/{model}")
            except Exception as e:
                logger.warning(f"Erreur initialisation VLM client: {e}")
                self.vlm_client = None

    def can_extract(self, file_path: Path) -> bool:
        """Vérifie si VLM peut traiter cette image.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier.

        Returns:
        -------
        bool
            True si VLM est configuré et le fichier est une image supportée.

        Examples:
        --------
        >>> extractor = ImageExtractor(config={"provider": "openai", ...})
        >>> extractor.can_extract(Path("screenshot.png"))
        True
        >>> extractor.can_extract(Path("document.pdf"))
        False
        """
        if not self.vlm_client:
            return False

        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def extract(self, file_path: Path) -> ExtractionResult:
        """Extrait le texte d'une image avec VLM.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier image.

        Returns:
        -------
        ExtractionResult
            Résultat de l'extraction.

        Examples:
        --------
        >>> extractor = ImageExtractor(config={...})
        >>> result = extractor.extract(Path("screenshot.png"))
        >>> if result.success:
        ...     print(f"Texte extrait : {result.text[:100]}")
        """
        if not self.vlm_client:
            error_msg = "VLM client non initialisé"
            return ExtractionResult(
                text="",
                success=False,
                extractor_name=self.name,
                metadata={"file_name": file_path.name},
                error=error_msg,
                confidence_score=0.0,
            )

        try:
            logger.info(f"Extraction VLM de l'image: {file_path.name}")

            # Lecture et encodage de l'image en base64
            with open(file_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")

            # Déterminer le type MIME
            mime_type = self._get_mime_type(file_path)

            # Prompt pour extraction de texte
            prompt = self.config.get(
                "prompt",
                "Extract all text visible in this image. "
                "Preserve the structure and formatting. "
                "Include all visible text, labels, and captions. "
                "If there is no text, respond with 'NO_TEXT_FOUND'.",
            )

            # Appel au VLM
            assert self.vlm_client is not None

            response = self.vlm_client.chat.completions.create(
                model=self.vlm_client._model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}"
                                },
                            },
                        ],
                    }
                ],
                temperature=self.vlm_client._temperature,
                max_tokens=self.config.get("max_tokens", 2000),
            )

            # Extraction du texte de la réponse
            if response.choices and response.choices[0].message.content:
                extracted_text: str = str(response.choices[0].message.content).strip()

                # Vérifier si aucun texte trouvé
                if extracted_text.upper() == "NO_TEXT_FOUND":
                    extracted_text = ""

            else:
                extracted_text = ""

            # Métadonnées
            metadata = {
                "file_name": file_path.name,
                "file_size": file_path.stat().st_size,
                "format": file_path.suffix[1:],
                "mime_type": mime_type,
                "vlm_provider": self.config.get("provider"),
                "vlm_model": self.config.get("model"),
            }

            # Score de confiance basé sur longueur du texte extrait
            if len(extracted_text) > 100:
                confidence = 0.85
            elif len(extracted_text) > 20:
                confidence = 0.7
            elif len(extracted_text) > 0:
                confidence = 0.5
            else:
                confidence = 0.3  # Image sans texte

            logger.info(
                f"Image: Extrait {len(extracted_text)} caractères "
                f"de {file_path.name} (confidence={confidence:.2f})"
            )

            return ExtractionResult(
                text=extracted_text,
                success=True,
                extractor_name=self.name,
                metadata=metadata,
                confidence_score=confidence,
            )

        except Exception as e:
            error_msg = f"Erreur extraction VLM image: {e}"
            logger.error(error_msg)
            return ExtractionResult(
                text="",
                success=False,
                extractor_name=self.name,
                metadata={"file_name": file_path.name},
                error=error_msg,
                confidence_score=0.0,
            )

    def _get_mime_type(self, file_path: Path) -> str:
        """Détermine le type MIME de l'image.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier image.

        Returns:
        -------
        str
            Type MIME (ex: "image/png").
        """
        extension = file_path.suffix.lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".bmp": "image/bmp",
            ".gif": "image/gif",
        }
        return mime_types.get(extension, "image/png")
